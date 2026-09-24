"""Tests del motor de voz Kokoro."""

import asyncio

import pytest

pytest.importorskip("numpy")
pytest.importorskip("soundfile")

import numpy as np

from noticia.voz.base import ErrorMotorVoz, MotorNoDisponible
from noticia.voz.motor_kokoro import MotorKokoro, voz_y_velocidad


class _KokoroFalso:
    llamadas: list[dict] = []
    vacio = False

    def create(self, texto, voice, speed, lang):
        type(self).llamadas.append({"texto": texto, "voice": voice, "speed": speed, "lang": lang})
        if type(self).vacio:
            return np.zeros(0, dtype=np.float32), 24000
        return np.zeros(2400, dtype=np.float32), 24000


def _fabrica_ok(onnx, voices):
    return _KokoroFalso()


def _fabrica_que_falla(onnx, voices):
    raise RuntimeError("no se pudo cargar el modelo")


@pytest.fixture(autouse=True)
def _resetear_kokoro_falso():
    _KokoroFalso.llamadas = []
    _KokoroFalso.vacio = False
    yield


def test_voz_y_velocidad_alex():
    assert voz_y_velocidad("alex") == ("em_alex", 0.96)


def test_voz_y_velocidad_maria():
    assert voz_y_velocidad("maria") == ("ef_dora", 1.05)


def test_sintetizar_llama_con_lang_es_y_voz_correcta(tmp_path):
    motor = MotorKokoro(fabrica=_fabrica_ok)
    asyncio.run(motor.cargar())
    ruta = tmp_path / "salida.wav"

    resultado = asyncio.run(motor.sintetizar("Hola, buenas", "alex", ruta))

    assert resultado == ruta
    assert ruta.exists()
    llamada = _KokoroFalso.llamadas[0]
    assert llamada["lang"] == "es"
    assert llamada["voice"] == "em_alex"
    assert llamada["speed"] == 0.96


def test_sintetizar_maria_usa_su_voz_y_velocidad(tmp_path):
    motor = MotorKokoro(fabrica=_fabrica_ok)
    asyncio.run(motor.cargar())
    ruta = tmp_path / "salida.wav"

    asyncio.run(motor.sintetizar("Hola", "maria", ruta))

    llamada = _KokoroFalso.llamadas[0]
    assert llamada["voice"] == "ef_dora"
    assert llamada["speed"] == 1.05


def test_sintetizar_escribe_wav_legible_a_24khz(tmp_path):
    import soundfile as sf

    motor = MotorKokoro(fabrica=_fabrica_ok)
    asyncio.run(motor.cargar())
    ruta = tmp_path / "salida.wav"

    asyncio.run(motor.sintetizar("Hola", "alex", ruta))

    datos, sr = sf.read(str(ruta))
    assert sr == 24000
    assert len(datos) == 2400


def test_sintetizar_con_audio_vacio_lanza_error(tmp_path):
    _KokoroFalso.vacio = True
    motor = MotorKokoro(fabrica=_fabrica_ok)
    asyncio.run(motor.cargar())
    ruta = tmp_path / "salida.wav"

    with pytest.raises(ErrorMotorVoz):
        asyncio.run(motor.sintetizar("Hola", "alex", ruta))


def test_disponible_falso_sin_modelos(tmp_path, monkeypatch):
    monkeypatch.setattr("noticia.config.settings.kokoro_dir", tmp_path)
    motor = MotorKokoro(fabrica=_fabrica_ok)

    ok, motivo = motor.disponible()

    assert ok is False
    assert motivo


def test_cargar_con_fabrica_que_falla_lanza_motor_no_disponible():
    motor = MotorKokoro(fabrica=_fabrica_que_falla)

    with pytest.raises(MotorNoDisponible):
        asyncio.run(motor.cargar())


def test_atributos_del_motor():
    motor = MotorKokoro(fabrica=_fabrica_ok)
    assert motor.nombre == "kokoro"
    assert motor.extension == "wav"
    assert motor.concurrencia_maxima > 0
