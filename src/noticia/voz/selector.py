"""Resuelve la cadena de motores de voz a usar según preferencia y GPU."""

import logging
from collections.abc import Callable

from noticia.voz.base import MotorNoDisponible, MotorVoz
from noticia.voz.gpu import InfoGPU, detectar_gpu
from noticia.voz.motor_chatterbox import MotorChatterbox
from noticia.voz.motor_edge import MotorEdge
from noticia.voz.motor_kokoro import MotorKokoro

logger = logging.getLogger("noticia.voz.selector")

MOTORES: dict[str, Callable[[], MotorVoz]] = {
    "edge": MotorEdge,
    "kokoro": MotorKokoro,
    "chatterbox": MotorChatterbox,
}


def crear_motor(nombre: str) -> MotorVoz:
    """Instancia el motor `nombre` a partir de `MOTORES`."""
    try:
        fabrica = MOTORES[nombre]
    except KeyError as exc:
        raise ValueError(f"Motor de voz desconocido: {nombre!r}") from exc
    return fabrica()


def orden_preferido(preferencia: str, info_gpu: InfoGPU) -> list[str]:
    """Orden de motores a intentar según la preferencia y si hay GPU disponible."""
    if preferencia == "auto":
        return ["chatterbox", "kokoro", "edge"] if info_gpu.disponible else ["kokoro", "edge"]
    if preferencia == "chatterbox":
        return ["chatterbox", "kokoro", "edge"]
    if preferencia == "kokoro":
        return ["kokoro", "edge"]
    if preferencia == "edge":
        return ["edge"]
    raise ValueError(f"Preferencia de motor de voz desconocida: {preferencia!r}")


def resolver_motores(
    preferencia: str | None = None, info_gpu: InfoGPU | None = None
) -> list[MotorVoz]:
    """Instancia y filtra los motores disponibles, en el orden preferido.

    `edge` está siempre al final de cualquier cadena, como último recurso; si
    ni siquiera él está disponible, lanza `MotorNoDisponible`.
    """
    from noticia.config import settings

    pref = preferencia if preferencia is not None else settings.motor_voz
    gpu = info_gpu if info_gpu is not None else detectar_gpu()

    cadena: list[MotorVoz] = []
    for nombre in orden_preferido(pref, gpu):
        motor = crear_motor(nombre)
        ok, motivo = motor.disponible()
        if ok:
            cadena.append(motor)
        else:
            logger.info("Motor de voz %s descartado: %s", nombre, motivo)

    if not cadena:
        raise MotorNoDisponible("Ningún motor de voz disponible, ni siquiera edge-tts")

    if len(cadena) > 1:
        fallback = " → ".join(motor.nombre for motor in cadena[1:])
        logger.info("Motor de voz: %s (fallback: %s)", cadena[0].nombre, fallback)
    else:
        logger.info("Motor de voz: %s", cadena[0].nombre)

    return cadena


async def preparar_cadena(motores: list[MotorVoz]) -> list[MotorVoz]:
    """Carga el primer motor de la cadena; si falla, lo descarta y prueba el siguiente."""
    restante = list(motores)
    while restante:
        primero = restante[0]
        try:
            await primero.cargar()
        except MotorNoDisponible as exc:
            logger.warning("Motor %s no se pudo cargar, se descarta: %s", primero.nombre, exc)
            restante = restante[1:]
            continue
        return restante
    return restante


__all__ = [
    "MOTORES",
    "crear_motor",
    "orden_preferido",
    "preparar_cadena",
    "resolver_motores",
]
