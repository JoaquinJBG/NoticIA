import asyncio
import logging
import os

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


def main():
    configurar_logging()
    asyncio.run(producir_episodio())


if __name__ == "__main__":
    main()
