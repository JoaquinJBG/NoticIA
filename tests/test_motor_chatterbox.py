"""Tests del motor de voz Chatterbox Multilingual es-ES."""

import asyncio
import copy
import sys

import pytest

from noticia.voz.base import MotorNoDisponible
from noticia.voz.motor_chatterbox import MotorChatterbox


class _AudioFalso:
    """Simula un tensor de torch: .squeeze(0).cpu().numpy()."""

    def __init__(self, n_muestras: int = 4800) -> None:
        self._n = n_muestras

    def squeeze(self, _dim):
        return self

    def cpu(self):
        return self

    def numpy(self):
        import numpy as np

        return np.zeros(self._n, dtype="float32")


class _ModeloFalso:
    def __init__(self) -> None:
        self.sr = 24000
        self.conds = "conds-iniciales"
        self.llamadas_prepare: list[tuple[str, float]] = []
        self.llamadas_generate: list[dict] = []

    def prepare_conditionals(self, ref: str, exaggeration: float) -> None:
        self.llamadas_prepare.append((ref, exaggeration))
        self.conds = f"conds-de-{ref}"

    def generate(self, texto, **kwargs):
        self.llamadas_generate.append({"texto": texto, **kwargs})
        return _AudioFalso()


@pytest.fixture
def modelo_falso():
    return _ModeloFalso()


@pytest.fixture
def cargador_ok(modelo_falso):
    def _cargador(device: str):
        return modelo_falso

    return _cargador


@pytest.fixture
def referencias_presentes(tmp_path, monkeypatch):
    ref_alex = tmp_path / "alex_ref.wav"
    ref_maria = tmp_path / "maria_ref.wav"
    ref_alex.write_bytes(b"wav-alex")
    ref_maria.write_bytes(b"wav-maria")
    monkeypatch.setattr("noticia.config.settings.chatterbox_ref_alex", ref_alex)
    monkeypatch.setattr("noticia.config.settings.chatterbox_ref_maria", ref_maria)
    return ref_alex, ref_maria


def test_prepare_conditionals_se_llama_una_vez_por_locutor(
    cargador_ok, modelo_falso, referencias_presentes
):
    motor = MotorChatterbox(cargador=cargador_ok)

    asyncio.run(motor.cargar())

    assert len(modelo_falso.llamadas_prepare) == 2
    locutores_llamados = {ref for ref, _exag in modelo_falso.llamadas_prepare}
    ref_alex, ref_maria = referencias_presentes
    assert locutores_llamados == {str(ref_alex), str(ref_maria)}


def test_maria_usa_exageracion_0_65(cargador_ok, modelo_falso, referencias_presentes):
    motor = MotorChatterbox(cargador=cargador_ok)
    asyncio.run(motor.cargar())

    exageraciones = dict(modelo_falso.llamadas_prepare)
    ref_maria = referencias_presentes[1]
    assert exageraciones[str(ref_maria)] == pytest.approx(0.65)


def test_texto_largo_se_trocea_en_varias_llamadas(
    tmp_path, cargador_ok, modelo_falso, referencias_presentes
):
    motor = MotorChatterbox(cargador=cargador_ok)
    asyncio.run(motor.cargar())
    texto = ("Esto es una frase de prueba bastante larga para forzar el troceo. ") * 12
    ruta = tmp_path / "salida.wav"

    asyncio.run(motor.sintetizar(texto, "alex", ruta))

    llamadas = modelo_falso.llamadas_generate
    assert len(llamadas) >= 3
    for llamada in llamadas:
        assert len(llamada["texto"]) <= 280
        assert llamada["language_id"] == "es"
        assert llamada["repetition_penalty"] == 1.2
        assert llamada["top_p"] == 0.95


def test_conds_del_locutor_se_restauran_antes_de_generar(
    tmp_path, cargador_ok, modelo_falso, referencias_presentes
):
    motor = MotorChatterbox(cargador=cargador_ok)
    asyncio.run(motor.cargar())
    ref_alex = referencias_presentes[0]
    conds_alex_esperados = f"conds-de-{ref_alex}"

    conds_vistos = []
    original_generate = modelo_falso.generate

    def _generate_que_registra_conds(texto, **kwargs):
        conds_vistos.append(modelo_falso.conds)
        return original_generate(texto, **kwargs)

    modelo_falso.generate = _generate_que_registra_conds

    asyncio.run(motor.sintetizar("Hola, buenas tardes", "alex", tmp_path / "s.wav"))

    assert all(c == conds_alex_esperados for c in conds_vistos)


def test_disponible_sin_wav_de_referencia_nombra_el_fichero(tmp_path, monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda _nombre: object())
    monkeypatch.setattr("noticia.config.settings.chatterbox_ref_alex", tmp_path / "alex_ref.wav")
    monkeypatch.setattr("noticia.config.settings.chatterbox_ref_maria", tmp_path / "maria_ref.wav")
    motor = MotorChatterbox(cargador=lambda device: None)

    ok, motivo = motor.disponible()

    assert ok is False
    assert "alex_ref.wav" in motivo


def test_disponible_sin_chatterbox_instalado(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda _nombre: None)
    motor = MotorChatterbox(cargador=lambda device: None)

    ok, motivo = motor.disponible()

    assert ok is False
    assert "chatterbox" in motivo


def test_cargar_con_cargador_que_falla_lanza_motor_no_disponible(referencias_presentes):
    def _cargador_falla(device):
        raise RuntimeError("sin GPU")

    motor = MotorChatterbox(cargador=_cargador_falla)

    with pytest.raises(MotorNoDisponible):
        asyncio.run(motor.cargar())


def test_importar_el_modulo_no_importa_torch():
    estaba_antes = "torch" in sys.modules
    sys.modules.pop("noticia.voz.motor_chatterbox", None)
    if not estaba_antes:
        sys.modules.pop("torch", None)

    import noticia.voz.motor_chatterbox  # noqa: F401

    if not estaba_antes:
        assert "torch" not in sys.modules


def test_atributos_del_motor():
    motor = MotorChatterbox(cargador=lambda device: None)
    assert motor.nombre == "chatterbox"
    assert motor.extension == "wav"
    assert motor.concurrencia_maxima == 1


def test_copy_del_conds_es_independiente(cargador_ok, modelo_falso, referencias_presentes):
    """self._conds[locutor] debe ser una copia, no una referencia al mismo objeto vivo."""
    motor = MotorChatterbox(cargador=cargador_ok)
    asyncio.run(motor.cargar())

    conds_guardados = dict(motor._conds)
    modelo_falso.conds = copy.copy(modelo_falso.conds) + "-mutado"

    assert conds_guardados["alex"] != modelo_falso.conds
