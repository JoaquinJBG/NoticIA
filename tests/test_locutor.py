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
