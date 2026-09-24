import argparse
import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path

from noticia.bloques import ORDEN_BLOQUES
from noticia.config import settings
from noticia.editor import ErrorMontaje, ensamblar_podcast_dinamico
from noticia.fechas import hoy_madrid, parsear_fecha
from noticia.generador import construir_guion
from noticia.ingesta import obtener_noticias
from noticia.locutor import ErrorLocucion, locutar_episodio
from noticia.logging_setup import configurar_logging
from noticia.masterizado import ErrorMasterizado
from noticia.orquestador import (
    BloqueoOcupado,
    Codigo,
    GuionVacio,
    ejecutar,
    formatear_guion,
    trocear_guion,
)
from noticia.voz.selector import preparar_cadena, resolver_motores

logger = logging.getLogger("noticia.cli")


def generar_solo_guion(salida: str | None = None) -> str:
    """Corre ingesta + generación y vuelca el guion a fichero, sin audio."""
    logger.info("Modo solo-guion: ingesta + generación, sin locución ni mastering.")
    os.makedirs(settings.carpeta_output, exist_ok=True)
    fecha = hoy_madrid()
    noticias = obtener_noticias()
    guion = construir_guion(noticias, fecha)

    if not any(linea.strip() for lineas in guion.values() for linea in lineas):
        logger.error("Guion vacío: ¿sesión de Claude iniciada?")
        raise RuntimeError(
            "Guion vacío: ningún bloque tiene contenido. ¿Sesión de Claude iniciada?"
        )

    if salida is None:
        salida = os.path.join(settings.carpeta_output, f"guion_{fecha.isoformat()}.md")

    ruta_salida = Path(salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_text(formatear_guion(guion), encoding="utf-8")
    logger.info("Guion escrito en %s", salida)
    return salida


async def generar_solo_audio(
    ruta_guion: str, salida: str | None = None, motor_voz: str | None = None
) -> str:
    """Locuta y masteriza un guion ya escrito, sin regenerarlo."""
    logger.info("Modo solo-audio: locución + montaje desde %s", ruta_guion)
    texto = Path(ruta_guion).read_text(encoding="utf-8")
    bloques_texto = trocear_guion(texto)
    if not bloques_texto:
        raise RuntimeError(f"El guion {ruta_guion} no tiene bloques '## nombre'.")

    bloques_reconocidos = {
        bloque: bloques_texto[bloque] for bloque in ORDEN_BLOQUES if bloques_texto.get(bloque)
    }
    if not bloques_reconocidos:
        logger.error(
            "Ningún encabezado de %s coincide con un bloque conocido (%s).",
            ruta_guion,
            ", ".join(ORDEN_BLOQUES),
        )
        raise RuntimeError(
            f"El guion {ruta_guion} no tiene ningún bloque reconocido: los "
            f"encabezados '## nombre' deben coincidir con uno de "
            f"{', '.join(ORDEN_BLOQUES)}."
        )

    os.makedirs(settings.carpeta_temp, exist_ok=True)
    os.makedirs(settings.carpeta_output, exist_ok=True)

    motores = resolver_motores(motor_voz)
    motores = await preparar_cadena(motores)

    logger.info("Locutando bloques: %s", ", ".join(bloques_reconocidos))
    carpeta_temp = Path(tempfile.mkdtemp(dir=settings.carpeta_temp))
    try:
        resultado = await locutar_episodio(bloques_reconocidos, motores, carpeta_temp)
    finally:
        for motor in motores:
            await motor.cerrar()

    if salida is None:
        salida = os.path.join(settings.carpeta_output, "NoticIA_audio.mp3")

    ensamblar_podcast_dinamico(resultado.fragmentos_por_bloque, salida)
    logger.info("Audio escrito en %s", salida)
    return salida


def main(argv: list[str] | None = None) -> int:
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
        help="Ruta del fichero de guion o de audio, según el modo.",
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
    parser.add_argument(
        "--publicar",
        action="store_true",
        help="Publica el episodio (feed.xml local) después de producirlo.",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Rehace el audio aunque ya exista (reutiliza el guion salvo --regenerar-guion).",
    )
    parser.add_argument(
        "--regenerar-guion",
        action="store_true",
        help="Vuelve a generar el guion con Claude aunque ya exista uno para esa fecha.",
    )
    parser.add_argument(
        "--fecha",
        type=parsear_fecha,
        default=None,
        help="Fecha del episodio, en formato AAAA-MM-DD (por defecto: hoy en Madrid).",
    )
    parser.add_argument(
        "--motor-voz",
        choices=("auto", "edge", "kokoro", "chatterbox"),
        default=None,
        help="Motor de voz a usar (por defecto: el configurado en settings.motor_voz).",
    )
    args = parser.parse_args(argv)

    try:
        if args.solo_audio:
            if not args.guion:
                parser.error("--solo-audio requiere --guion RUTA")
            asyncio.run(generar_solo_audio(args.guion, args.salida, args.motor_voz))
        elif args.solo_guion:
            generar_solo_guion(args.salida)
        else:
            fecha = args.fecha or hoy_madrid()
            asyncio.run(
                ejecutar(
                    fecha,
                    publicar=args.publicar,
                    forzar=args.forzar,
                    regenerar_guion=args.regenerar_guion,
                    motor_voz=args.motor_voz,
                )
            )
    except BloqueoOcupado as exc:
        logger.error("NoticIA ya se está ejecutando: %s", exc)
        return int(Codigo.BLOQUEADO)
    except GuionVacio as exc:
        logger.error("Guion vacío: %s", exc)
        return int(Codigo.GUION_VACIO)
    except (ErrorLocucion, ErrorMontaje, ErrorMasterizado) as exc:
        logger.error("Fallo produciendo el audio: %s", exc)
        return int(Codigo.AUDIO)
    except Exception:
        logger.exception("Fallo inesperado")
        return int(Codigo.ERROR)

    return int(Codigo.OK)


if __name__ == "__main__":
    sys.exit(main())
