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
