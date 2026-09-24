"""Motor de voz basado en edge-tts (voces neuronales de Microsoft)."""

import importlib.util
import logging
from pathlib import Path

from noticia.config import settings
from noticia.voz.base import ErrorMotorVoz, Locutor

logger = logging.getLogger("noticia.voz.motor_edge")


def voz_y_rate(locutor: Locutor) -> tuple[str, str]:
    """Devuelve (voz, rate) configurados para `locutor`."""
    if locutor == "alex":
        return settings.voz_alex, settings.rate_alex
    return settings.voz_maria, settings.rate_maria


class MotorEdge:
    nombre = "edge"
    extension = "mp3"

    def __init__(self) -> None:
        self.concurrencia_maxima = settings.concurrencia_locucion

    def disponible(self) -> tuple[bool, str]:
        if importlib.util.find_spec("edge_tts") is None:
            return False, "el paquete edge_tts no está instalado"
        return True, ""

    async def cargar(self) -> None:
        """edge-tts no necesita carga previa: es una llamada de red por turno."""

    async def sintetizar(self, texto: str, locutor: Locutor, ruta: Path) -> Path:
        import edge_tts

        voz, rate = voz_y_rate(locutor)
        try:
            await edge_tts.Communicate(texto, voz, rate=rate).save(str(ruta))
        except Exception as exc:
            logger.error("edge-tts falló al sintetizar para %s: %s", locutor, exc)
            raise ErrorMotorVoz(f"edge-tts falló al sintetizar: {exc}") from exc

        if not ruta.exists() or ruta.stat().st_size == 0:
            raise ErrorMotorVoz(f"edge-tts generó un fichero vacío en {ruta}")
        return ruta

    async def cerrar(self) -> None:
        """No hay recursos que liberar."""
