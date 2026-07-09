import logging
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


class _FakeFeed:
    def __init__(self, entries):
        self.entries = entries


def test_descargar_feed_parsea_entradas(monkeypatch):
    entradas = [
        {"title": "N1", "summary": "s1", "link": "u1", "published_parsed": _time.gmtime()},
        {"title": "N2", "summary": "s2", "link": "u2", "published_parsed": _time.gmtime()},
    ]
    monkeypatch.setattr(ingesta.feedparser, "parse", lambda url: _FakeFeed(entradas))
    arts = ingesta._descargar_feed("http://x", "x.com")
    assert [a["titular"] for a in arts] == ["N1", "N2"]
    assert arts[0]["fuente"] == "x.com"


def test_obtener_pool_filtra_recencia_y_estructura(monkeypatch):
    reciente = _time.gmtime(_time.time() - 3600)
    viejo = _time.gmtime(_time.time() - 10 * 24 * 3600)
    entradas = [
        {"title": "Nueva", "summary": "s", "link": "u-nueva", "published_parsed": reciente},
        {"title": "Vieja", "summary": "s", "link": "u-vieja", "published_parsed": viejo},
    ]
    monkeypatch.setattr(ingesta.feedparser, "parse", lambda url: _FakeFeed(entradas))
    # Catálogos mínimos para no depender de la lista real ni de la red
    monkeypatch.setattr(ingesta.fuentes, "FEEDS_CURADOS", {"espana": ["http://x"]})
    monkeypatch.setattr(ingesta.fuentes, "SECCIONES_GOOGLE_NEWS", {})

    pool = ingesta.obtener_pool(ventana_horas=48, timeout=1)
    assert set(pool.keys()) == {"espana"}
    titulares = [a["titular"] for a in pool["espana"]]
    assert "Nueva" in titulares
    assert "Vieja" not in titulares


def test_obtener_pool_avisa_si_una_categoria_queda_vacia(monkeypatch, caplog):
    """Un catálogo de feeds muerto no debe perder un bloque en silencio."""
    monkeypatch.setattr(ingesta.feedparser, "parse", lambda url: _FakeFeed([]))
    monkeypatch.setattr(ingesta.fuentes, "FEEDS_CURADOS", {"futbol": ["http://muerto"]})
    monkeypatch.setattr(ingesta.fuentes, "SECCIONES_GOOGLE_NEWS", {})

    with caplog.at_level(logging.WARNING, logger="noticia.ingesta"):
        pool = ingesta.obtener_pool(timeout=1)

    assert pool["futbol"] == []
    assert any("futbol" in reg.getMessage() for reg in caplog.records)


def test_obtener_noticias_puente_aplana_clusters(monkeypatch):
    # Pool simulado: espana (contraste) + futbol (simple)
    fake_pool = {
        "espana": [
            {"titular": "A", "resumen": "", "fuente": "f1", "url": "a", "fecha": None},
            {"titular": "B", "resumen": "", "fuente": "f2", "url": "b", "fecha": None},
        ],
        "futbol": [
            {"titular": "Gol", "resumen": "", "fuente": "marca", "url": "g", "fecha": None},
        ],
    }
    monkeypatch.setattr(ingesta, "obtener_pool", lambda **kw: fake_pool)

    noticias = ingesta.obtener_noticias()
    # Todas las categorías devuelven listas planas (compatibilidad con generador actual)
    assert isinstance(noticias["espana"], list)
    assert isinstance(noticias["futbol"], list)
    assert {a["titular"] for a in noticias["espana"]} == {"A", "B"}
