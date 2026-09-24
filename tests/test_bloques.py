from noticia import bloques


def test_categorias_noticias():
    assert bloques.CATEGORIAS_NOTICIAS == (
        "espana",
        "geopolitica",
        "ia_y_actualidad",
        "ciencia",
        "friki",
        "futbol",
    )


def test_orden_bloques_incluye_intro_y_outro():
    assert bloques.ORDEN_BLOQUES == (
        "intro",
        "espana",
        "geopolitica",
        "ia_y_actualidad",
        "ciencia",
        "friki",
        "futbol",
        "outro",
    )


def test_nombre_bloque_cubre_todos_los_bloques():
    for bloque in bloques.ORDEN_BLOQUES:
        assert bloque in bloques.NOMBRE_BLOQUE
    assert bloques.NOMBRE_BLOQUE["espana"] == "España"
    assert bloques.NOMBRE_BLOQUE["ia_y_actualidad"] == "IA y actualidad"
    assert bloques.NOMBRE_BLOQUE["intro"] == "Introducción"
    assert bloques.NOMBRE_BLOQUE["outro"] == "Despedida"
