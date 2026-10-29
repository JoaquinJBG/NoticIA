"""Tipos y contrato común para los motores de locución."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

# Id de la "ranura" de voz: "alex", "santi" o "invitada". Es genérico a propósito:
# cada episodio decide qué ranuras suenan (ver noticia.personajes.Reparto).
Locutor = str

LOCUTORES: tuple[Locutor, ...] = ("alex", "santi", "invitada")

_NOMBRE_FIJO: dict[str, str] = {"alex": "Álex", "santi": "Santi"}


def nombre_mostrado(locutor: Locutor) -> str:
    """Nombre del personaje; el de la invitada es configurable (INVITADA_NOMBRE)."""
    if locutor == "invitada":
        from noticia.config import settings

        return settings.invitada_nombre
    return _NOMBRE_FIJO.get(locutor, locutor)


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


def ajuste(prefijo: str, locutor: Locutor):
    """Valor del ajuste `<prefijo>_<locutor>` de la configuración (p.ej. `voz_santi`)."""
    from noticia.config import settings

    try:
        return getattr(settings, f"{prefijo}_{locutor}")
    except AttributeError as exc:
        raise ErrorMotorVoz(f"locutor sin configurar: {locutor!r} ({prefijo})") from exc


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
