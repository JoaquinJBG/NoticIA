from noticia import agrupador


def test_normalizar_quita_acentos_stopwords_y_puntuacion():
    assert (
        agrupador._normalizar("El Gobierno de España aprueba la Reforma!")
        == "gobierno espana aprueba reforma"
    )


def test_normalizar_vacio():
    assert agrupador._normalizar("") == ""
