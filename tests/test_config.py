import pytest
from pydantic import ValidationError

import noticia.config as config


@pytest.fixture
def por_defecto(monkeypatch):
    """Settings sin .env ni variables de entorno: solo los valores del código."""
    for clave in (
        "VOZ_ALEX",
        "VOZ_MARIA",
        "RATE_ALEX",
        "RATE_MARIA",
        "PAUSA_ENTRE_TURNOS_MS",
        "CARPETA_OUTPUT",
        "CARPETA_TEMP",
    ):
        monkeypatch.delenv(clave, raising=False)
    return config.Settings(_env_file=None)


def test_settings_valores_por_defecto(por_defecto):
    assert por_defecto.voz_alex == "es-ES-AlvaroNeural"
    assert por_defecto.voz_maria == "es-ES-XimenaNeural"
    assert por_defecto.carpeta_output == "output"
    assert por_defecto.carpeta_temp == "temp"


def test_prosodia_y_pausa_por_defecto(por_defecto):
    assert por_defecto.rate_alex == "-4%"
    assert por_defecto.rate_maria == "+0%"
    assert por_defecto.pausa_entre_turnos_ms == 350


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


def test_motor_voz_y_objetivo_lufs_por_defecto(monkeypatch):
    # Sin .env ni entorno: el .env local de cada máquina puede fijar MOTOR_VOZ.
    monkeypatch.delenv("MOTOR_VOZ", raising=False)
    monkeypatch.delenv("OBJETIVO_LUFS", raising=False)
    s = config.Settings(_env_file=None)
    assert s.motor_voz == "auto"
    assert s.objetivo_lufs == -16.0


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


def test_ruta_output_relativa_se_resuelve_desde_root(monkeypatch):
    monkeypatch.setattr(config.settings, "carpeta_output", "salida")
    assert config.settings.ruta_output == config.ROOT / "salida"


def test_ruta_output_absoluta_se_mantiene(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "carpeta_output", str(tmp_path))
    assert config.settings.ruta_output == tmp_path


def test_ruta_temp_relativa_se_resuelve_desde_root(monkeypatch):
    monkeypatch.setattr(config.settings, "carpeta_temp", "tmp")
    assert config.settings.ruta_temp == config.ROOT / "tmp"


def test_ruta_temp_absoluta_se_mantiene(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "carpeta_temp", str(tmp_path))
    assert config.settings.ruta_temp == tmp_path


def test_pronunciacion_extra_por_defecto_vacio():
    assert config.settings.pronunciacion_extra == {}


def test_carpeta_publicacion_y_episodios_derivan_de_carpeta_output(tmp_path, monkeypatch):
    monkeypatch.delenv("CARPETA_PUBLICACION", raising=False)
    s = config.Settings(_env_file=None, carpeta_output=str(tmp_path / "salida"))
    assert s.carpeta_publicacion == tmp_path / "salida" / "publicacion"
    assert s.carpeta_episodios == tmp_path / "salida" / "episodios"


def test_carpeta_publicacion_explicita_se_respeta(tmp_path, monkeypatch):
    monkeypatch.delenv("CARPETA_PUBLICACION", raising=False)
    s = config.Settings(_env_file=None, carpeta_output=str(tmp_path), carpeta_publicacion="pub")
    assert s.carpeta_publicacion == config.ROOT / "pub"


def test_carpeta_publicacion_desde_entorno_resuelve_desde_root(monkeypatch):
    monkeypatch.setenv("CARPETA_PUBLICACION", "pub_env")
    s = config.Settings(_env_file=None)
    assert s.carpeta_publicacion == config.ROOT / "pub_env"


def test_rutas_de_voz_relativas_se_resuelven_desde_root(monkeypatch):
    for clave in ("KOKORO_DIR", "CHATTERBOX_REF_ALEX", "CHATTERBOX_REF_MARIA"):
        monkeypatch.delenv(clave, raising=False)
    s = config.Settings(
        _env_file=None,
        kokoro_dir="modelos/otro",
        chatterbox_ref_alex="voces/a.wav",
        chatterbox_ref_maria="voces/m.wav",
    )
    assert s.kokoro_dir == config.ROOT / "modelos" / "otro"
    assert s.chatterbox_ref_alex == config.ROOT / "voces" / "a.wav"
    assert s.chatterbox_ref_maria == config.ROOT / "voces" / "m.wav"


def test_get_prompt_sistema_sin_instrucciones_lanza_error(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_dir_reglas", lambda: tmp_path)
    with pytest.raises(FileNotFoundError, match="instrucciones.md"):
        config.get_prompt_sistema()


def test_get_contexto_sin_fichero_devuelve_vacio(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_dir_reglas", lambda: tmp_path)
    assert config.get_contexto() == ""
