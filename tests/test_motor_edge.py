"""Tests del motor de voz edge-tts."""

import asyncio
import sys
import types

import pytest

from noticia.voz.base import ErrorMotorVoz
from noticia.voz.motor_edge import MotorEdge, voz_y_rate


class _CommunicateFalso:
    llamadas: list[tuple[str, str, str]] = []
    vacio = False

    def __init__(self, texto: str, voz: str, rate: str) -> None:
        self.texto = texto
        self.voz = voz
        self.rate = rate

    async def save(self, ruta: str) -> None:
        type(self).llamadas.append((self.texto, self.voz, self.rate))
        if type(self).vacio:
            open(ruta, "w").close()
        else:
            with open(ruta, "w") as fh:
                fh.write("audio falso")


@pytest.fixture
def edge_tts_falso(monkeypatch):
    _CommunicateFalso.llamadas = []
    _CommunicateFalso.vacio = False
    modulo = types.ModuleType("edge_tts")
    modulo.Communicate = _CommunicateFalso
    monkeypatch.setitem(sys.modules, "edge_tts", modulo)
    return _CommunicateFalso


def test_voz_y_rate_alex():
    assert voz_y_rate("alex") == ("es-ES-AlvaroNeural", "-4%")


def test_voz_y_rate_maria():
    assert voz_y_rate("maria") == ("es-ES-XimenaNeural", "+0%")


def test_sintetizar_alex_usa_su_voz_y_rate(tmp_path, edge_tts_falso):
    motor = MotorEdge()
    ruta = tmp_path / "salida.mp3"

    resultado = asyncio.run(motor.sintetizar("Hola", "alex", ruta))

    assert resultado == ruta
    assert edge_tts_falso.llamadas == [("Hola", "es-ES-AlvaroNeural", "-4%")]


def test_sintetizar_maria_usa_su_voz_y_rate(tmp_path, edge_tts_falso):
    motor = MotorEdge()
    ruta = tmp_path / "salida.mp3"

    asyncio.run(motor.sintetizar("Hola", "maria", ruta))

    assert edge_tts_falso.llamadas == [("Hola", "es-ES-XimenaNeural", "+0%")]


def test_fichero_vacio_lanza_error(tmp_path, edge_tts_falso):
    edge_tts_falso.vacio = True
    motor = MotorEdge()
    ruta = tmp_path / "salida.mp3"

    with pytest.raises(ErrorMotorVoz):
        asyncio.run(motor.sintetizar("Hola", "alex", ruta))


def test_disponible_sin_edge_tts(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda nombre: None)
    motor = MotorEdge()

    ok, motivo = motor.disponible()

    assert ok is False
    assert motivo


def test_cargar_y_cerrar_no_hacen_nada():
    motor = MotorEdge()
    asyncio.run(motor.cargar())
    asyncio.run(motor.cerrar())


def test_atributos_del_motor():
    motor = MotorEdge()
    assert motor.nombre == "edge"
    assert motor.extension == "mp3"
    assert motor.concurrencia_maxima > 0
