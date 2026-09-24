"""Motor de voz Kokoro-82M (CPU), vía kokoro-onnx."""

import asyncio
import importlib.util
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from noticia.config import settings
from noticia.voz.base import ErrorMotorVoz, Locutor, MotorNoDisponible
from noticia.voz.modelos import modelos_kokoro_presentes, rutas_kokoro

logger = logging.getLogger("noticia.voz.motor_kokoro")


def voz_y_velocidad(locutor: Locutor) -> tuple[str, float]:
    """Devuelve (voz, velocidad) configuradas para `locutor`."""
    if locutor == "alex":
        return settings.kokoro_voz_alex, settings.kokoro_velocidad_alex
    return settings.kokoro_voz_maria, settings.kokoro_velocidad_maria


def _fabrica_kokoro(onnx: str, voices: str) -> Any:
    from kokoro_onnx import Kokoro

    return Kokoro(onnx, voices)


class MotorKokoro:
    nombre = "kokoro"
    extension = "wav"

    def __init__(self, fabrica: Callable[[str, str], Any] | None = None) -> None:
        self.concurrencia_maxima = settings.kokoro_concurrencia
        self._fabrica = fabrica or _fabrica_kokoro
        self._kokoro: Any = None
        self._lock = asyncio.Lock()

    def disponible(self) -> tuple[bool, str]:
        if importlib.util.find_spec("kokoro_onnx") is None:
            return False, "el paquete kokoro_onnx no está instalado"
        if importlib.util.find_spec("soundfile") is None:
            return False, "el paquete soundfile no está instalado"
        if not modelos_kokoro_presentes():
            return False, f"faltan los pesos de Kokoro en {settings.kokoro_dir}"
        return True, ""

    async def cargar(self) -> None:
        async with self._lock:
            if self._kokoro is not None:
                return
            onnx, voices = rutas_kokoro()
            try:
                self._kokoro = await asyncio.to_thread(self._fabrica, str(onnx), str(voices))
            except Exception as exc:
                logger.error("No se pudo cargar Kokoro: %s", exc)
                raise MotorNoDisponible(f"no se pudo cargar Kokoro: {exc}") from exc

    async def sintetizar(self, texto: str, locutor: Locutor, ruta: Path) -> Path:
        import soundfile as sf

        if self._kokoro is None:
            await self.cargar()

        voz, velocidad = voz_y_velocidad(locutor)
        try:
            muestras, sr = await asyncio.to_thread(
                self._kokoro.create, texto, voice=voz, speed=velocidad, lang="es"
            )
        except Exception as exc:
            logger.error("Kokoro falló al sintetizar para %s: %s", locutor, exc)
            raise ErrorMotorVoz(f"Kokoro falló al sintetizar: {exc}") from exc

        if len(muestras) == 0:
            raise ErrorMotorVoz(f"Kokoro generó un audio vacío para {locutor!r}")

        sf.write(str(ruta), muestras, sr, subtype="PCM_16")
        return ruta

    async def cerrar(self) -> None:
        self._kokoro = None
