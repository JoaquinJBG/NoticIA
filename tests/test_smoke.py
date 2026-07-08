def test_todos_los_modulos_importan():
    import noticia.cli  # noqa: F401
    import noticia.config  # noqa: F401
    import noticia.editor  # noqa: F401
    import noticia.generador  # noqa: F401
    import noticia.ingesta  # noqa: F401
    import noticia.locutor  # noqa: F401
