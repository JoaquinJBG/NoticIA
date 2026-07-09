import argparse
import asyncio
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from noticia.config import settings
from noticia.editor import ensamblar_podcast_dinamico
from noticia.generador import construir_guion
from noticia.ingesta import obtener_noticias
from noticia.locutor import procesar_guion_a_audio
from noticia.logging_setup import configurar_logging

logger = logging.getLogger("noticia.cli")


async def producir_episodio():
    logger.info("--- INICIANDO PRODUCCIÓN DE NOTICIA: PROFESSIONAL EDITION ---")

    os.makedirs(settings.carpeta_output, exist_ok=True)
    os.makedirs(settings.carpeta_temp, exist_ok=True)

    logger.info("Capturando noticias de todas las fuentes...")
    noticias = obtener_noticias()

    logger.info("Generando guion inteligente por bloques (esto puede tardar unos minutos)...")
    guion_por_bloques = construir_guion(noticias)

    logger.info("Iniciando locución de voces realistas...")
    fragmentos_audio_por_bloque = {}
    for categoria, lineas in guion_por_bloques.items():
        if not lineas:
            continue
        logger.info("Procesando locución del bloque: %s...", categoria)
        texto_bloque = "\n".join(lineas)
        fragmentos_audio_por_bloque[categoria] = await procesar_guion_a_audio(texto_bloque)

    if fragmentos_audio_por_bloque:
        archivo_final = os.path.join(settings.carpeta_output, "NoticIA_PRO_Final.mp3")
        logger.info("Iniciando montaje dinámico y mastering final...")
        ensamblar_podcast_dinamico(fragmentos_audio_por_bloque, archivo_final)
        logger.info("--- PODCAST PROFESIONAL FINALIZADO: %s ---", archivo_final)
    else:
        logger.error("No se generaron audios para ensamblar.")


_ORDEN_BLOQUES = [
    "intro",
    "espana",
    "geopolitica",
    "ia_y_actualidad",
    "ciencia",
    "friki",
    "futbol",
    "outro",
]


def _formatear_guion(guion: dict) -> str:
    """Renderiza el guion a Markdown: un encabezado por bloque, en orden."""
    partes = []
    for bloque in _ORDEN_BLOQUES:
        lineas = guion.get(bloque)
        if not lineas or not any(linea.strip() for linea in lineas):
            continue
        partes.append(f"## {bloque}\n\n" + "\n".join(lineas))
    return "\n\n".join(partes) + "\n"


def generar_solo_guion(salida: str | None = None) -> str:
    """Corre ingesta + generación y vuelca el guion a fichero, sin audio."""
    logger.info("Modo solo-guion: ingesta + generación, sin locución ni mastering.")
    os.makedirs(settings.carpeta_output, exist_ok=True)
    noticias = obtener_noticias()
    guion = construir_guion(noticias)

    if not any(linea.strip() for lineas in guion.values() for linea in lineas):
        logger.error("Guion vacío: ¿sesión de Claude iniciada?")
        raise RuntimeError(
            "Guion vacío: ningún bloque tiene contenido. ¿Sesión de Claude iniciada?"
        )

    if salida is None:
        fecha = datetime.now(UTC).strftime("%Y-%m-%d")
        salida = os.path.join(settings.carpeta_output, f"guion_{fecha}.md")

    ruta_salida = Path(salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_text(_formatear_guion(guion), encoding="utf-8")
    logger.info("Guion escrito en %s", salida)
    return salida


_ENCABEZADO_BLOQUE = re.compile(r"^##\s+(\w+)\s*$")


def _trocear_guion(texto_md: str) -> dict[str, str]:
    """Inverso de _formatear_guion: '## bloque' + texto -> {bloque: texto}."""
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


async def generar_solo_audio(ruta_guion: str, salida: str | None = None) -> str:
    """Locuta y masteriza un guion ya escrito, sin regenerarlo."""
    logger.info("Modo solo-audio: locución + montaje desde %s", ruta_guion)
    texto = Path(ruta_guion).read_text(encoding="utf-8")
    bloques = _trocear_guion(texto)
    if not bloques:
        raise RuntimeError(f"El guion {ruta_guion} no tiene bloques '## nombre'.")

    os.makedirs(settings.carpeta_temp, exist_ok=True)
    os.makedirs(settings.carpeta_output, exist_ok=True)

    fragmentos_por_bloque = {}
    for categoria in _ORDEN_BLOQUES:
        contenido = bloques.get(categoria)
        if not contenido:
            continue
        logger.info("Procesando locución del bloque: %s...", categoria)
        fragmentos_por_bloque[categoria] = await procesar_guion_a_audio(contenido)

    if salida is None:
        salida = os.path.join(settings.carpeta_output, "NoticIA_audio.mp3")

    ensamblar_podcast_dinamico(fragmentos_por_bloque, salida)
    logger.info("Audio escrito en %s", salida)
    return salida


def main():
    configurar_logging()
    parser = argparse.ArgumentParser(
        prog="noticia", description="Podcast diario automatizado con IA"
    )
    parser.add_argument(
        "--solo-guion",
        action="store_true",
        help="Genera solo el guion (sin audio) y lo vuelca a un fichero.",
    )
    parser.add_argument(
        "--salida",
        help="Ruta del fichero de guion (solo con --solo-guion).",
    )
    parser.add_argument(
        "--solo-audio",
        action="store_true",
        help="Locuta y masteriza un guion ya escrito (requiere --guion).",
    )
    parser.add_argument(
        "--guion",
        help="Ruta del guion .md de entrada (solo con --solo-audio).",
    )
    args = parser.parse_args()

    if args.solo_audio:
        if not args.guion:
            parser.error("--solo-audio requiere --guion RUTA")
        asyncio.run(generar_solo_audio(args.guion, args.salida))
    elif args.solo_guion:
        generar_solo_guion(args.salida)
    else:
        asyncio.run(producir_episodio())


if __name__ == "__main__":
    main()
