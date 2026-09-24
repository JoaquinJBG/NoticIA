"""Genera muestras de audio de cada motor de voz, para comparar de oído."""

import asyncio
import logging
from collections.abc import Sequence
from pathlib import Path

from noticia.voz.base import LOCUTORES
from noticia.voz.selector import MOTORES, crear_motor

logger = logging.getLogger("noticia.voz.muestras")

FRASE_MUESTRA = (
    "Buenos días, esto es NoticIA. Hoy hablamos de la plaza, del cielo y de la zarzuela."
)


async def generar_muestras(
    carpeta: Path, nombres: Sequence[str] = ("edge", "kokoro", "chatterbox")
) -> list[Path]:
    """Sintetiza `FRASE_MUESTRA` con cada motor disponible y cada locutor.

    Los motores desconocidos o no disponibles se saltan con un aviso. Devuelve
    las rutas generadas.
    """
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    generadas: list[Path] = []
    for nombre in nombres:
        if nombre not in MOTORES:
            logger.warning("Motor de voz desconocido, se omite: %s", nombre)
            continue

        motor = crear_motor(nombre)
        ok, motivo = motor.disponible()
        if not ok:
            logger.warning("Motor %s no disponible, se omite: %s", nombre, motivo)
            continue

        try:
            await motor.cargar()
        except Exception as exc:
            logger.warning("Motor %s no se pudo cargar, se omite: %s", nombre, exc)
            continue

        for locutor in LOCUTORES:
            ruta = carpeta / f"{nombre}_{locutor}.{motor.extension}"
            try:
                await motor.sintetizar(FRASE_MUESTRA, locutor, ruta)
            except Exception as exc:
                logger.warning("Fallo generando la muestra %s: %s", ruta, exc)
                continue
            generadas.append(ruta)

        await motor.cerrar()

    return generadas


def main() -> int:
    """Punto de entrada de `python -m noticia.voz.muestras`."""
    from noticia.config import settings

    carpeta = Path(settings.carpeta_output) / "muestras"
    try:
        generadas = asyncio.run(generar_muestras(carpeta))
    except Exception as exc:
        logger.error("No se pudieron generar las muestras de voz: %s", exc)
        return 1

    if not generadas:
        logger.error("No se generó ninguna muestra: revisa qué motores están disponibles.")
        return 1

    for ruta in generadas:
        logger.info("Muestra generada: %s", ruta)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
