from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from noticia.voz.base import (
    LOCUTORES,
    NOMBRE_MOSTRADO,
    ErrorMotorVoz,
    MotorNoDisponible,
    Turno,
)


def test_locutores_y_nombre_mostrado():
    assert LOCUTORES == ("alex", "maria")
    assert NOMBRE_MOSTRADO["alex"] == "Álex"
    assert NOMBRE_MOSTRADO["maria"] == "María"


def test_turno_es_inmutable():
    turno = Turno(bloque="espana", indice=0, locutor="alex", texto="Hola")
    assert turno.bloque == "espana"
    assert turno.indice == 0
    assert turno.locutor == "alex"
    assert turno.texto == "Hola"
    with pytest.raises(FrozenInstanceError):
        turno.texto = "Adiós"


def test_error_motor_no_disponible_es_error_motor_voz():
    assert issubclass(MotorNoDisponible, ErrorMotorVoz)


def test_motor_voz_es_runtime_checkable():
    from noticia.voz.base import MotorVoz

    class MotorFalso:
        nombre = "falso"
        extension = "wav"
        concurrencia_maxima = 1

        def disponible(self) -> tuple[bool, str]:
            return True, ""

        async def cargar(self) -> None:
            return None

        async def sintetizar(self, texto: str, locutor: str, ruta: Path) -> Path:
            return ruta

        async def cerrar(self) -> None:
            return None

    assert isinstance(MotorFalso(), MotorVoz)
