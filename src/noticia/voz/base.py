"""Tipos y contrato común para los motores de locución."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

Locutor = Literal["alex", "maria"]

LOCUTORES: tuple[Locutor, ...] = ("alex", "maria")

NOMBRE_MOSTRADO: dict[str, str] = {"alex": "Álex", "maria": "María"}


@dataclass(frozen=True)
class Turno:
    bloque: str
    indice: int  # 0-based dentro del bloque
    locutor: Locutor
    texto: str


class ErrorMotorVoz(Exception):
    """Error genérico al sintetizar o gestionar un motor de voz."""


class MotorNoDisponible(ErrorMotorVoz):
    """El motor no se pudo cargar o no cumple sus requisitos."""


@runtime_checkable
class MotorVoz(Protocol):
    nombre: str  # "edge" | "kokoro" | "chatterbox"
    extension: str  # "mp3" | "wav"
    concurrencia_maxima: int

    def disponible(self) -> tuple[bool, str]:
        """Comprobación barata: módulos y ficheros presentes. Devuelve (ok, motivo)."""
        ...

    async def cargar(self) -> None:
        """Carga pesada e idempotente. Lanza MotorNoDisponible si falla."""
        ...

    async def sintetizar(self, texto: str, locutor: Locutor, ruta: Path) -> Path:
        """Sintetiza `texto` con la voz de `locutor` y lo escribe en `ruta`."""
        ...

    async def cerrar(self) -> None:
        """Libera los recursos cargados por `cargar`."""
        ...
