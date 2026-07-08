import argparse
import asyncio
import logging
import os
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
    args = parser.parse_args()

    if args.solo_guion:
        generar_solo_guion(args.salida)
    else:
        asyncio.run(producir_episodio())


if __name__ == "__main__":
    main()
