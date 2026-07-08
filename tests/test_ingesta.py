import time as _time

from noticia import ingesta


def test_limpiar_html_quita_tags_y_entidades():
    crudo = "<p>Hola <b>mundo</b> &amp; adi&oacute;s</p>"
    assert ingesta.limpiar_html(crudo) == "Hola mundo & adiós"


def test_limpiar_html_vacio():
    assert ingesta.limpiar_html("") == ""
    assert ingesta.limpiar_html(None) == ""


def test_es_reciente_dentro_de_ventana():
    ahora = _time.time()
    hace_10h = _time.gmtime(ahora - 10 * 3600)
    assert ingesta.es_reciente(hace_10h, ventana_horas=48, ahora=ahora) is True


def test_es_reciente_fuera_de_ventana():
    ahora = _time.time()
    hace_5dias = _time.gmtime(ahora - 5 * 24 * 3600)
    assert ingesta.es_reciente(hace_5dias, ventana_horas=48, ahora=ahora) is False


def test_es_reciente_sin_fecha_se_conserva():
    assert ingesta.es_reciente(None) is True


def test_parsear_entrada_basica():
    entry = {
        "title": "Titular de prueba",
        "summary": "<p>Resumen &amp; co</p>",
        "link": "https://medio.com/n1",
        "published_parsed": _time.gmtime(),
    }
    art = ingesta._parsear_entrada(entry, "medio.com")
    assert art["titular"] == "Titular de prueba"
    assert art["resumen"] == "Resumen & co"
    assert art["fuente"] == "medio.com"
    assert art["url"] == "https://medio.com/n1"


def test_parsear_entrada_google_news_usa_fuente_real():
    entry = {
        "title": "Sube el paro - El País",
        "summary": "texto",
        "link": "https://news.google.com/x",
        "source": {"title": "El País"},
    }
    art = ingesta._parsear_entrada(entry, "news.google.com")
    assert art["fuente"] == "El País"
    assert art["titular"] == "Sube el paro"  # se quita el sufijo " - El País"


def test_parsear_entrada_sin_titulo_devuelve_none():
    assert ingesta._parsear_entrada({"summary": "x"}, "medio.com") is None


def test_dedup_por_url_y_titular():
    arts = [
        {"titular": "A", "url": "u1"},
        {"titular": "A-dup", "url": "u1"},  # misma url -> fuera
        {"titular": "B", "url": ""},
        {"titular": "B", "url": ""},  # mismo titular sin url -> fuera
        {"titular": "C", "url": "u3"},
    ]
    out = ingesta._dedup(arts)
    assert [a["titular"] for a in out] == ["A", "B", "C"]
