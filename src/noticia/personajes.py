"""Reparto de cada episodio: presentadores fijos y una invitada que rota."""

import random
from dataclasses import dataclass
from datetime import date
from typing import Literal

from noticia.config import settings
from noticia.voz.base import Locutor, nombre_mostrado

PRESENTADORES: tuple[Locutor, ...] = ("alex", "santi")


def nombre_personaje(locutor: Locutor) -> str:
    return nombre_mostrado(locutor)


@dataclass(frozen=True)
class Reparto:
    """Quién habla en un episodio. `locutores` conserva el orden de emisión."""

    locutores: tuple[Locutor, ...]
    sustituido: Locutor | None = None  # presentador al que reemplaza la invitada

    @classmethod
    def habitual(cls) -> "Reparto":
        return cls(PRESENTADORES)

    @property
    def hay_invitada(self) -> bool:
        return "invitada" in self.locutores

    @property
    def nombres(self) -> list[str]:
        return [nombre_personaje(locutor) for locutor in self.locutores]

    @property
    def presentadores_texto(self) -> str:
        """Los nombres unidos con " y ", para ID3, portada y avisos."""
        return " y ".join(self.nombres)

    @property
    def prefijos_texto(self) -> str:
        """Los prefijos de línea del guion, p.ej. "Álex:" o "Santi:"."""
        return " o ".join(f'"{nombre}:"' for nombre in self.nombres)

    def a_dict(self) -> dict:
        return {"locutores": list(self.locutores), "sustituido": self.sustituido}


def _sustituido(fecha: date, cada_n: int, modo: str) -> Locutor:
    if modo in PRESENTADORES:
        return modo
    if modo == "aleatorio":
        # Semilla por fecha: misma fecha -> mismo resultado, en cualquier proceso.
        return random.Random(f"noticia-invitada-{fecha.isoformat()}").choice(PRESENTADORES)
    # "alterna": cada aparición de la invitada cambia de presentador.
    return PRESENTADORES[(fecha.toordinal() // cada_n) % len(PRESENTADORES)]


def reparto_para_fecha(
    fecha: date,
    cada_n: int | None = None,
    modo: Literal["alterna", "aleatorio", "alex", "santi"] | None = None,
) -> Reparto:
    """Reparto del episodio de `fecha`: determinista, sin depender del historial.

    La invitada aparece cuando `fecha.toordinal() % cada_n == 0` (cada N días de
    calendario; 0 = nunca) y sustituye a uno de los presentadores solo ese día.
    """
    n = settings.invitada_cada_n_episodios if cada_n is None else cada_n
    if n <= 0 or fecha.toordinal() % n != 0:
        return Reparto.habitual()
    sustituido = _sustituido(fecha, n, modo or settings.invitada_sustituye)
    locutores = tuple("invitada" if p == sustituido else p for p in PRESENTADORES)
    return Reparto(locutores, sustituido)


def locutores_requeridos() -> tuple[Locutor, ...]:
    """Ranuras de voz que un motor debe poder cubrir con la configuración actual."""
    if settings.invitada_cada_n_episodios > 0:
        return (*PRESENTADORES, "invitada")
    return PRESENTADORES
