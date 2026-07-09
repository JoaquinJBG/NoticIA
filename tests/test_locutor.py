import asyncio

from noticia import locutor


def test_parsear_linea_alex_y_maria():
    assert locutor._parsear_linea("Álex: hola") == ("alex", "hola")
    assert locutor._parsear_linea("María: qué tal") == ("maria", "qué tal")


def test_parsear_linea_sin_tildes():
    assert locutor._parsear_linea("Alex: hola") == ("alex", "hola")
    assert locutor._parsear_linea("Maria: hola") == ("maria", "hola")


def test_parsear_linea_mencion_de_otro_locutor_no_confunde():
    # El bug antiguo: buscaba "álex:" en CUALQUIER posición y se lo atribuía a Álex.
    linea = "María: y entonces Álex: dijo que no"
    assert locutor._parsear_linea(linea) == ("maria", "y entonces Álex: dijo que no")


def test_parsear_linea_dos_puntos_en_la_frase():
    # split(":", 1) corta por el dos puntos del prefijo, no por el de la hora.
    assert locutor._parsear_linea("Álex: quedamos a las 15:30") == (
        "alex",
        "quedamos a las 15:30",
    )


def test_parsear_linea_no_dialogo_devuelve_none():
    assert locutor._parsear_linea("IMPORTANTE: no inventes hechos") is None
    assert locutor._parsear_linea("una línea cualquiera") is None
    assert locutor._parsear_linea("Santi: ya no existe") is None
    assert locutor._parsear_linea("Álex:") is None  # sin texto
    assert locutor._parsear_linea("") is None


class _FakeCommunicate:
    llamadas = []

    def __init__(self, texto, voz, rate="+0%"):
        _FakeCommunicate.llamadas.append({"texto": texto, "voz": voz, "rate": rate})

    async def save(self, ruta):
        with open(ruta, "wb") as fh:
            fh.write(b"fake-mp3")


def test_procesar_guion_usa_voz_y_rate_por_locutor(monkeypatch, tmp_path):
    _FakeCommunicate.llamadas = []
    monkeypatch.setattr(locutor.edge_tts, "Communicate", _FakeCommunicate)
    monkeypatch.setattr(locutor.settings, "carpeta_temp", str(tmp_path))

    guion = "Álex: buenos días\nMaría: hola a todos\nlínea sin locutor"
    piezas = asyncio.run(locutor.procesar_guion_a_audio(guion))

    assert len(piezas) == 2  # la línea sin locutor se salta
    primera, segunda = _FakeCommunicate.llamadas
    assert primera == {
        "texto": "buenos días",
        "voz": "es-ES-AlvaroNeural",
        "rate": "-4%",
    }
    assert segunda == {
        "texto": "hola a todos",
        "voz": "es-ES-ElviraNeural",
        "rate": "+6%",
    }
