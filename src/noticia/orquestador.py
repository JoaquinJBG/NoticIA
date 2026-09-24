"""Orquesta la producción diaria de un episodio: guion, locución, montaje y publicación.

Es idempotente: una segunda ejecución del mismo día no repite trabajo ya hecho
(ni gasta cuota de Claude) salvo que se le pida explícitamente con
`forzar`/`regenerar_guion`. Un `fcntl.flock` evita que dos ejecuciones
concurrentes pisen la misma carpeta de episodio.
"""

import contextlib
import fcntl
import json
import logging
import re
import shutil
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum
from pathlib import Path

from noticia.bloques import CATEGORIAS_NOTICIAS, ORDEN_BLOQUES
from noticia.config import settings
from noticia.editor import comprobar_sintonias, ensamblar_podcast_dinamico
from noticia.generador import construir_guion
from noticia.ingesta import obtener_pool
from noticia.locutor import locutar_episodio
from noticia.logging_setup import anadir_log_fichero, quitar_handler
from noticia.publicador import (
    EpisodioPublicable,
    NoticiaCitada,
    episodio_publicado,
    escribir_atomico,
    publicar_episodio,
    titulo_episodio,
)
from noticia.seleccion import noticias_a_json, seleccionar_noticias
from noticia.voz.selector import preparar_cadena, resolver_motores

logger = logging.getLogger("noticia.orquestador")

_ENCABEZADO_BLOQUE = re.compile(r"^##\s+(\w+)\s*$")


class Codigo(IntEnum):
    OK = 0
    ERROR = 1
    USO = 2
    GUION_VACIO = 3
    AUDIO = 4
    BLOQUEADO = 75


class GuionVacio(Exception):
    """El guion generado no tiene contenido en ningún bloque de noticias."""


class BloqueoOcupado(Exception):
    """Ya hay otra ejecución de NoticIA en curso (mismo lock)."""


def formatear_guion(guion: dict[str, list[str]]) -> str:
    """Renderiza el guion a Markdown: un encabezado por bloque, en el orden de emisión."""
    partes = []
    for bloque in ORDEN_BLOQUES:
        lineas = guion.get(bloque)
        if not lineas or not any(linea.strip() for linea in lineas):
            continue
        partes.append(f"## {bloque}\n\n" + "\n".join(lineas))
    return "\n\n".join(partes) + "\n"


def guion_tiene_noticias(guion: dict[str, list[str]]) -> bool:
    """True si algún bloque de `CATEGORIAS_NOTICIAS` tiene texto.

    Intro y outro siempre traen texto de reserva (ver `generador.generar_intro`
    y `generador.generar_outro`), así que no cuentan como contenido real: un
    guion sin ninguna noticia no debe considerarse "con contenido".
    """
    return any(
        any(linea.strip() for linea in guion.get(categoria, []))
        for categoria in CATEGORIAS_NOTICIAS
    )


def trocear_guion(texto_md: str) -> dict[str, str]:
    """Inverso de `formatear_guion`: '## bloque' + texto -> {bloque: texto}."""
    bloques: dict[str, str] = {}
    actual = None
    lineas: list[str] = []
    for linea in texto_md.splitlines():
        encabezado = _ENCABEZADO_BLOQUE.match(linea)
        if encabezado:
            if actual is not None:
                bloques[actual] = "\n".join(lineas).strip()
            actual = encabezado.group(1)
            lineas = []
        elif actual is not None:
            lineas.append(linea)
    if actual is not None:
        bloques[actual] = "\n".join(lineas).strip()
    return bloques


@dataclass
class ResumenEjecucion:
    fecha: date
    estado: str  # "producido" | "reanudado" | "ya_existia"
    codigo: Codigo
    motor_voz: str = ""
    motores_usados: dict[str, int] = field(default_factory=dict)
    turnos_fallidos: int = 0
    lineas_descartadas: int = 0
    duracion_s: float = 0.0
    lufs: float | None = None
    true_peak: float | None = None
    ruta_mp3: Path | None = None
    ruta_feed: Path | None = None
    sintonias_faltantes: list[str] = field(default_factory=list)
    segundos_totales: float = 0.0

    def registrar(self) -> None:
        logger.info(
            "=== RESUMEN ===\n"
            "Fecha: %s\n"
            "Estado: %s (código %s)\n"
            "Motor de voz: %s · motores usados: %s\n"
            "Turnos fallidos: %s · líneas descartadas: %s\n"
            "Duración: %.1fs · LUFS: %s · true peak: %s dBTP\n"
            "MP3: %s\n"
            "Feed: %s\n"
            "Sintonías faltantes: %s\n"
            "Tiempo total: %.1fs",
            self.fecha.isoformat(),
            self.estado,
            int(self.codigo),
            self.motor_voz or "-",
            dict(self.motores_usados),
            self.turnos_fallidos,
            self.lineas_descartadas,
            self.duracion_s,
            self.lufs,
            self.true_peak,
            self.ruta_mp3,
            self.ruta_feed,
            ", ".join(self.sintonias_faltantes) or "ninguna",
            self.segundos_totales,
        )


@contextlib.contextmanager
def bloqueo_exclusivo(ruta: Path) -> Iterator[None]:
    """Toma un lock exclusivo y no bloqueante sobre `ruta`.

    Lanza `BloqueoOcupado` si otro proceso (u otra llamada) ya lo tiene.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fh = ruta.open("w")
    try:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise BloqueoOcupado(f"NoticIA ya se está ejecutando (lock: {ruta})") from exc
        yield
    finally:
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError as exc:
            logger.debug("No se pudo liberar el lock %s: %s", ruta, exc)
        fh.close()


def carpeta_episodio(fecha: date) -> Path:
    return settings.carpeta_episodios / fecha.isoformat()


def generar_guion(fecha: date) -> tuple[dict[str, list[str]], dict[str, list[dict]]]:
    """Genera el guion del episodio: ingesta, selección y llamada al generador de texto.

    Si todos los bloques de noticias del guion salen vacíos, reintenta hasta
    `settings.reintentos_guion` veces (esperando `settings.espera_reintento_guion_s`
    entre intentos) antes de lanzar `GuionVacio`.
    """
    intentos = settings.reintentos_guion + 1
    guion: dict[str, list[str]] = {}
    noticias: dict[str, list[dict]] = {}
    for intento in range(intentos):
        pool = obtener_pool()
        noticias = seleccionar_noticias(pool)
        guion = construir_guion(noticias, fecha)
        if guion_tiene_noticias(guion):
            return guion, noticias
        ultimo = intento == intentos - 1
        logger.warning(
            "Guion vacío en el intento %s/%s%s",
            intento + 1,
            intentos,
            "." if ultimo else ", reintentando...",
        )
        if not ultimo:
            time.sleep(settings.espera_reintento_guion_s)

    raise GuionVacio("El guion generado no tiene contenido en ningún bloque de noticias")


def _construir_resumen_reutilizado(
    fecha: date, datos: dict, estado: str, ruta_feed: Path | None, inicio: float
) -> ResumenEjecucion:
    return ResumenEjecucion(
        fecha=fecha,
        estado=estado,
        codigo=Codigo.OK,
        motor_voz=datos.get("motor_voz", ""),
        motores_usados=datos.get("motores_usados", {}),
        turnos_fallidos=datos.get("turnos_fallidos", 0),
        duracion_s=datos.get("duracion_s", 0.0),
        lufs=datos.get("lufs"),
        true_peak=datos.get("true_peak"),
        ruta_mp3=Path(datos["ruta_mp3"]) if datos.get("ruta_mp3") else None,
        ruta_feed=ruta_feed,
        sintonias_faltantes=datos.get("sintonias_faltantes", []),
        segundos_totales=time.monotonic() - inicio,
    )


def _publicar(fecha: date, carpeta: Path, ruta_mp3: Path, datos_episodio: dict) -> Path:
    noticias_citadas = [
        NoticiaCitada(
            bloque=bloque,
            titular=n.get("titular", ""),
            fuente=n.get("fuente", ""),
            url=n.get("url", ""),
        )
        for bloque, lista in datos_episodio.get("noticias", {}).items()
        for n in lista
    ]
    capitulos = [(bloque, inicio) for bloque, inicio in datos_episodio.get("capitulos", [])]
    ep = EpisodioPublicable(
        fecha=fecha,
        mp3=ruta_mp3,
        noticias=noticias_citadas,
        capitulos=capitulos,
        guion=carpeta / "guion.md",
        motor_voz=datos_episodio.get("motor_voz", ""),
    )
    ruta_feed = publicar_episodio(ep)
    if "edge" in (datos_episodio.get("motores_usados") or {}):
        logger.warning(
            "edge-tts se ha usado para algún fragmento y no está amparado para uso "
            "comercial: revisa la licencia antes de distribuir este episodio."
        )
    return ruta_feed


async def ejecutar(
    fecha: date,
    publicar: bool,
    forzar: bool = False,
    regenerar_guion: bool = False,
    motor_voz: str | None = None,
) -> ResumenEjecucion:
    """Produce (o reanuda) el episodio de `fecha` y, si se pide, lo publica."""
    inicio = time.monotonic()
    ruta_lock = settings.ruta_output / ".noticia.lock"

    with bloqueo_exclusivo(ruta_lock):
        carpeta = carpeta_episodio(fecha)
        carpeta.mkdir(parents=True, exist_ok=True)
        handler = anadir_log_fichero(carpeta / "produccion.log")
        try:
            resumen = await _ejecutar_bloqueado(
                fecha, publicar, forzar, regenerar_guion, motor_voz, carpeta, inicio
            )
        except Exception:
            logger.exception("Fallo produciendo el episodio de %s", fecha.isoformat())
            raise
        else:
            resumen.registrar()
        finally:
            quitar_handler(handler)

    return resumen


async def _ejecutar_bloqueado(
    fecha: date,
    publicar: bool,
    forzar: bool,
    regenerar_guion: bool,
    motor_voz: str | None,
    carpeta: Path,
    inicio: float,
) -> ResumenEjecucion:
    ruta_mp3 = carpeta / f"NoticIA_{fecha.isoformat()}.mp3"
    ruta_episodio_json = carpeta / "episodio.json"
    audio_ya_hecho = ruta_mp3.exists() and ruta_episodio_json.exists()

    if not forzar:
        if publicar and episodio_publicado(fecha):
            datos = (
                json.loads(ruta_episodio_json.read_text(encoding="utf-8")) if audio_ya_hecho else {}
            )
            ruta_feed = settings.carpeta_publicacion / "feed.xml"
            return _construir_resumen_reutilizado(fecha, datos, "ya_existia", ruta_feed, inicio)

        if publicar and audio_ya_hecho:
            datos = json.loads(ruta_episodio_json.read_text(encoding="utf-8"))
            ruta_feed = _publicar(fecha, carpeta, ruta_mp3, datos)
            return _construir_resumen_reutilizado(fecha, datos, "reanudado", ruta_feed, inicio)

        if not publicar and audio_ya_hecho:
            datos = json.loads(ruta_episodio_json.read_text(encoding="utf-8"))
            return _construir_resumen_reutilizado(fecha, datos, "ya_existia", None, inicio)

    sintonias_faltantes_previo = comprobar_sintonias()

    ruta_guion_md = carpeta / "guion.md"
    ruta_noticias_json = carpeta / "noticias.json"

    if ruta_guion_md.exists() and ruta_noticias_json.exists() and not regenerar_guion:
        bloques_texto = trocear_guion(ruta_guion_md.read_text(encoding="utf-8"))
        noticias_json = json.loads(ruta_noticias_json.read_text(encoding="utf-8"))
        estado = "reanudado"
    else:
        guion, noticias = generar_guion(fecha)
        noticias_json = noticias_a_json(noticias)
        bloques_texto = {
            bloque: "\n".join(lineas)
            for bloque, lineas in guion.items()
            if any(linea.strip() for linea in lineas)
        }
        escribir_atomico(ruta_guion_md, formatear_guion(guion))
        escribir_atomico(
            ruta_noticias_json, json.dumps(noticias_json, ensure_ascii=False, indent=2)
        )
        estado = "producido"

    bloques_ordenados = {
        bloque: bloques_texto[bloque] for bloque in ORDEN_BLOQUES if bloque in bloques_texto
    }

    motores = resolver_motores(motor_voz)
    motores = await preparar_cadena(motores)
    motor_voz_usado = motores[0].nombre if motores else ""

    carpeta_temp_episodio = settings.ruta_temp / fecha.isoformat()
    if carpeta_temp_episodio.exists():
        shutil.rmtree(carpeta_temp_episodio)
    carpeta_temp_episodio.mkdir(parents=True, exist_ok=True)

    try:
        resultado_locucion = await locutar_episodio(
            bloques_ordenados, motores, carpeta_temp_episodio
        )

        metadatos = {
            "title": titulo_episodio(fecha),
            "artist": "Álex y María",
            "album": settings.podcast_titulo,
            "date": fecha.isoformat(),
        }
        resultado_montaje = ensamblar_podcast_dinamico(
            resultado_locucion.fragmentos_por_bloque, ruta_mp3, metadatos=metadatos
        )
    finally:
        for motor in motores:
            await motor.cerrar()
        shutil.rmtree(carpeta_temp_episodio, ignore_errors=True)

    datos_episodio = {
        "fecha": fecha.isoformat(),
        "titulo": titulo_episodio(fecha),
        "motor_voz": motor_voz_usado,
        "motores_usados": dict(resultado_locucion.motores_usados),
        "duracion_s": resultado_montaje.duracion_s,
        "lufs": resultado_montaje.loudness.lufs_integrados,
        "true_peak": resultado_montaje.loudness.true_peak_dbtp,
        "capitulos": [[bloque, ini] for bloque, ini in resultado_montaje.capitulos],
        "noticias": noticias_json,
        "sintonias_faltantes": resultado_montaje.sintonias_faltantes or sintonias_faltantes_previo,
        "turnos_fallidos": len(resultado_locucion.fallidos),
        "ruta_mp3": str(ruta_mp3),
    }
    escribir_atomico(ruta_episodio_json, json.dumps(datos_episodio, ensure_ascii=False, indent=2))

    ruta_feed = None
    if publicar:
        ruta_feed = _publicar(fecha, carpeta, ruta_mp3, datos_episodio)

    return ResumenEjecucion(
        fecha=fecha,
        estado=estado,
        codigo=Codigo.OK,
        motor_voz=motor_voz_usado,
        motores_usados=dict(resultado_locucion.motores_usados),
        turnos_fallidos=len(resultado_locucion.fallidos),
        lineas_descartadas=resultado_locucion.descartadas,
        duracion_s=resultado_montaje.duracion_s,
        lufs=resultado_montaje.loudness.lufs_integrados,
        true_peak=resultado_montaje.loudness.true_peak_dbtp,
        ruta_mp3=ruta_mp3,
        ruta_feed=ruta_feed,
        sintonias_faltantes=datos_episodio["sintonias_faltantes"],
        segundos_totales=time.monotonic() - inicio,
    )


__all__ = [
    "BloqueoOcupado",
    "Codigo",
    "GuionVacio",
    "ResumenEjecucion",
    "bloqueo_exclusivo",
    "carpeta_episodio",
    "ejecutar",
    "formatear_guion",
    "generar_guion",
    "guion_tiene_noticias",
    "trocear_guion",
]
