"""Locución del guion: parseo de turnos y síntesis en paralelo ordenada."""

import asyncio
import logging
import re
import tempfile
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from noticia.config import settings
from noticia.voz.base import Locutor, MotorNoDisponible, MotorVoz, Turno
from noticia.voz.texto import limpiar_texto_locucion

logger = logging.getLogger("noticia.locutor")

_LOCUTORES = ("alex", "maria")

# Líneas que hablan "los dos a la vez" (p.ej. el eslogan final): se asignan a
# Álex en vez de descartarse como locutor desconocido.
_PREFIJOS_AMBOS = frozenset({"alex y maria", "maria y alex", "ambos", "los dos"})

_RE_PARENTESIS = re.compile(r"\([^)]*\)")
# Una palabra sola (sin espacios) seguida de dos puntos: "Santi:", "IMPORTANTE:".
# Indica un intento de atribución (a un locutor desconocido o un encabezado),
# no una línea de continuación del turno anterior.
_RE_FORMA_PALABRA = re.compile(r"^\w+\s*:")


def _normalizar(texto: str) -> str:
    """minúsculas y sin tildes, para comparar el prefijo del locutor."""
    texto = texto.strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _limpiar_prefijo(prefijo: str) -> str:
    """Quita acotaciones entre paréntesis y asteriscos de negrita del prefijo."""
    prefijo = _RE_PARENTESIS.sub("", prefijo)
    return prefijo.replace("*", "")


def _parsear_linea(linea: str) -> tuple[str, str] | None:
    """ "Álex: hola" -> ("alex", "hola"). None si la línea no es diálogo.

    El prefijo es lo que hay ANTES del primer dos puntos, y debe ser un locutor
    conocido (una vez quitadas acotaciones entre paréntesis y asteriscos). Así
    una mención a otro locutor dentro de la frase no confunde la atribución, y
    un dos puntos dentro del texto no rompe el corte.
    """
    if ":" not in linea:
        return None
    prefijo, resto = linea.split(":", 1)
    locutor = _normalizar(_limpiar_prefijo(prefijo))
    if locutor in _PREFIJOS_AMBOS:
        locutor = "alex"
    elif locutor not in _LOCUTORES:
        return None
    texto = resto.strip()
    if not texto:
        return None
    return locutor, texto


class ErrorLocucion(Exception):
    """Se superó la fracción máxima de turnos fallidos al locutar el episodio."""


@dataclass
class ResultadoLocucion:
    fragmentos_por_bloque: dict[str, list[Path]]
    motores_usados: Counter[str] = field(default_factory=Counter)
    fallidos: list[Turno] = field(default_factory=list)
    descartadas: int = 0
    total_turnos: int = 0


def parsear_turnos(texto_bloque: str, bloque: str) -> tuple[list[Turno], int]:
    """Convierte el texto de un bloque de guion en una lista ordenada de Turno.

    Una línea sin prefijo de locutor reconocido que sigue, sin línea en blanco
    de por medio, a un turno ya abierto, y que no tiene forma "Palabra:", se
    entiende como continuación de ese turno. El resto de líneas no reconocidas
    se descartan (con un warning) y se cuentan.
    """
    turnos: list[Turno] = []
    descartadas = 0
    hay_linea_en_blanco_antes = True

    for linea_cruda in texto_bloque.split("\n"):
        linea = linea_cruda.strip()
        if not linea:
            hay_linea_en_blanco_antes = True
            continue

        parseada = _parsear_linea(linea)
        if parseada is not None:
            locutor, texto = parseada
            texto_limpio = limpiar_texto_locucion(texto)
            if texto_limpio:
                turnos.append(
                    Turno(bloque=bloque, indice=len(turnos), locutor=locutor, texto=texto_limpio)
                )
            else:
                logger.warning(
                    "Turno vacío tras limpiar el texto en el bloque %s: %s", bloque, linea[:60]
                )
                descartadas += 1
            hay_linea_en_blanco_antes = False
            continue

        es_continuacion = (
            turnos and not hay_linea_en_blanco_antes and not _RE_FORMA_PALABRA.match(linea)
        )
        if es_continuacion:
            anterior = turnos[-1]
            texto_unido = limpiar_texto_locucion(f"{anterior.texto} {linea}")
            turnos[-1] = Turno(
                bloque=anterior.bloque,
                indice=anterior.indice,
                locutor=anterior.locutor,
                texto=texto_unido,
            )
        else:
            logger.warning("Descartando línea sin locutor en el bloque %s: %s", bloque, linea[:60])
            descartadas += 1
        hay_linea_en_blanco_antes = False

    return turnos, descartadas


async def locutar_episodio(
    bloques: Mapping[str, str],
    motores: Sequence[MotorVoz],
    carpeta: Path,
    concurrencia: int | None = None,
    reintentos: int | None = None,
    espera_base_s: float = 0.5,
) -> ResultadoLocucion:
    """Locuta todos los bloques del episodio en paralelo, en orden reproducible.

    Aplana los turnos de todos los bloques y los sintetiza con un límite de
    concurrencia, probando los motores en orden (con reintentos) hasta que
    alguno funcione. Si la fracción de turnos fallidos supera
    `settings.max_fraccion_fallos_locucion`, lanza ErrorLocucion; si no, el
    episodio sigue con esos turnos marcados como fallidos.
    """
    if not motores:
        raise ValueError("locutar_episodio necesita al menos un motor de voz")

    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    todos_los_turnos: list[Turno] = []
    descartadas_total = 0
    for bloque, texto in bloques.items():
        turnos, descartadas = parsear_turnos(texto, bloque)
        todos_los_turnos.extend(turnos)
        descartadas_total += descartadas

    reintentos_efectivos = settings.reintentos_locucion if reintentos is None else reintentos
    limite_concurrencia = max(
        1,
        min(
            concurrencia if concurrencia is not None else settings.concurrencia_locucion,
            motores[0].concurrencia_maxima,
        ),
    )
    semaforo = asyncio.Semaphore(limite_concurrencia)

    motores_usados: Counter[str] = Counter()
    fallidos: list[Turno] = []
    resultados: dict[tuple[str, int], Path] = {}

    async def _procesar_turno(turno: Turno) -> None:
        async with semaforo:
            for motor in motores:
                try:
                    await motor.cargar()
                except MotorNoDisponible as exc:
                    logger.warning(
                        "Motor %s no disponible para el turno %s/%s: %s",
                        motor.nombre,
                        turno.bloque,
                        turno.indice,
                        exc,
                    )
                    continue

                ruta = carpeta / f"{turno.bloque}_{turno.indice:04d}.{motor.extension}"
                for intento in range(reintentos_efectivos + 1):
                    try:
                        await motor.sintetizar(turno.texto, turno.locutor, ruta)
                    except Exception as exc:
                        logger.warning(
                            "Fallo sintetizando el turno %s/%s con %s (intento %s): %s",
                            turno.bloque,
                            turno.indice,
                            motor.nombre,
                            intento,
                            exc,
                        )
                        if intento < reintentos_efectivos:
                            await asyncio.sleep(espera_base_s * 2**intento)
                        continue
                    else:
                        resultados[(turno.bloque, turno.indice)] = ruta
                        motores_usados[motor.nombre] += 1
                        return

            logger.error(
                "Todos los motores fallaron para el turno %s/%s", turno.bloque, turno.indice
            )
            fallidos.append(turno)

    await asyncio.gather(*(_procesar_turno(turno) for turno in todos_los_turnos))

    total = len(todos_los_turnos)
    if total and (len(fallidos) / total) > settings.max_fraccion_fallos_locucion:
        raise ErrorLocucion(f"Demasiados turnos fallidos al locutar: {len(fallidos)}/{total}")

    fragmentos_por_bloque: dict[str, list[Path]] = {bloque: [] for bloque in bloques}
    ordenados: dict[str, list[tuple[int, Path]]] = {bloque: [] for bloque in bloques}
    for turno in todos_los_turnos:
        ruta = resultados.get((turno.bloque, turno.indice))
        if ruta is not None:
            ordenados[turno.bloque].append((turno.indice, ruta))
    for bloque, pares in ordenados.items():
        pares.sort(key=lambda par: par[0])
        fragmentos_por_bloque[bloque] = [ruta for _, ruta in pares]

    return ResultadoLocucion(
        fragmentos_por_bloque=fragmentos_por_bloque,
        motores_usados=motores_usados,
        fallidos=fallidos,
        descartadas=descartadas_total,
        total_turnos=total,
    )


async def procesar_guion_a_audio(
    guion_texto: str,
    bloque: str = "bloque",
    motores: Sequence[MotorVoz] | None = None,
) -> list[str]:
    """Locuta un único bloque de guion. Compatibilidad para cli.py hasta T11."""
    if motores is None:
        from noticia.voz.motor_edge import MotorEdge

        motores = [MotorEdge()]

    settings.ruta_temp.mkdir(parents=True, exist_ok=True)
    carpeta = Path(tempfile.mkdtemp(dir=settings.ruta_temp))

    resultado = await locutar_episodio({bloque: guion_texto}, motores, carpeta)
    return [str(ruta) for ruta in resultado.fragmentos_por_bloque.get(bloque, [])]


__all__ = [
    "ErrorLocucion",
    "Locutor",
    "ResultadoLocucion",
    "Turno",
    "locutar_episodio",
    "parsear_turnos",
    "procesar_guion_a_audio",
]
