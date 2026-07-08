from noticia import ingesta


def test_limpiar_html_quita_tags_y_entidades():
    crudo = "<p>Hola <b>mundo</b> &amp; adi&oacute;s</p>"
    assert ingesta.limpiar_html(crudo) == "Hola mundo & adiós"


def test_limpiar_html_vacio():
    assert ingesta.limpiar_html("") == ""
    assert ingesta.limpiar_html(None) == ""
