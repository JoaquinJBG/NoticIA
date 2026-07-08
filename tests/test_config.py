import noticia.config as config


def test_settings_valores_por_defecto():
    assert config.settings.voz_alex == "es-ES-AlvaroNeural"
    assert config.settings.voz_santi == "es-ES-XimenaNeural"
    assert config.settings.carpeta_output == "output"
    assert config.settings.carpeta_temp == "temp"


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
