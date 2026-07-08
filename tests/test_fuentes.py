from noticia import fuentes


def test_url_google_news_seccion():
    url = fuentes.url_google_news("WORLD")
    assert "/headlines/section/topic/WORLD" in url
    assert "hl=es" in url and "gl=ES" in url and "ceid=ES:es" in url


def test_url_google_news_busqueda():
    url = fuentes.url_google_news("reforma laboral", es_busqueda=True)
    assert "/search?q=reforma+laboral" in url
    assert "hl=es" in url


def test_categorias_con_contraste():
    assert fuentes.CATEGORIAS_CON_CONTRASTE == frozenset(
        {"espana", "geopolitica", "ciencia", "ia_y_actualidad"}
    )


def test_catalogos_cubren_todas_las_categorias():
    # friki y futbol solo en curados; las 4 de contraste en ambos catálogos
    for cat in fuentes.CATEGORIAS_CON_CONTRASTE:
        assert cat in fuentes.FEEDS_CURADOS
        assert cat in fuentes.SECCIONES_GOOGLE_NEWS
    assert "friki" in fuentes.FEEDS_CURADOS
    assert "futbol" in fuentes.FEEDS_CURADOS
