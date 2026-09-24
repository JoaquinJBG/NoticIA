import pytest
from pydantic import ValidationError

import noticia.config as config


def test_settings_valores_por_defecto():
    assert config.settings.voz_alex == "es-ES-AlvaroNeural"
    assert config.settings.voz_maria == "es-ES-ElviraNeural"
    assert config.settings.carpeta_output == "output"
    assert config.settings.carpeta_temp == "temp"


def test_prosodia_y_pausa_por_defecto():
    assert config.settings.rate_alex == "-4%"
    assert config.settings.rate_maria == "+6%"
    assert config.settings.pausa_entre_turnos_ms == 350


def test_sintonias_cubre_categorias_y_apunta_a_mp3():
    s = config.settings.sintonias
    assert {
        "espana",
        "geopolitica",
        "ia_y_actualidad",
        "ciencia",
        "friki",
        "futbol",
        "intro",
        "outro",
    } <= set(s)
    assert all(v.endswith(".mp3") for v in s.values())


def test_get_prompt_sistema_lee_las_reglas():
    txt = config.get_prompt_sistema()
    assert isinstance(txt, str) and len(txt) > 0


def test_motor_voz_y_objetivo_lufs_por_defecto():
    assert config.settings.motor_voz == "auto"
    assert config.settings.objetivo_lufs == -16.0


def test_motor_voz_desde_entorno(monkeypatch):
    monkeypatch.setenv("MOTOR_VOZ", "kokoro")
    s = config.Settings()
    assert s.motor_voz == "kokoro"


def test_motor_voz_invalido_lanza_validation_error(monkeypatch):
    monkeypatch.setenv("MOTOR_VOZ", "inventado")
    with pytest.raises(ValidationError):
        config.Settings()


def test_carpeta_episodios():
    assert config.settings.carpeta_episodios == config.ROOT / "output" / "episodios"
