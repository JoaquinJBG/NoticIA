from noticia.voz.texto import limpiar_texto_locucion, trocear_frases


def test_limpiar_texto_locucion_quita_acotaciones():
    texto = "Hola (risas) qué tal [pausa] todo bien"
    resultado = limpiar_texto_locucion(texto)
    assert "(risas)" not in resultado
    assert "[pausa]" not in resultado
    assert "Hola" in resultado
    assert "todo bien" in resultado


def test_limpiar_texto_locucion_quita_urls():
    texto = "Mira esto: https://example.com/noticia?x=1 muy interesante"
    resultado = limpiar_texto_locucion(texto)
    assert "https://" not in resultado
    assert "example.com" not in resultado


def test_limpiar_texto_locucion_quita_emojis():
    texto = "Menuda noticia 😀🚀 de verdad"
    resultado = limpiar_texto_locucion(texto)
    assert "😀" not in resultado
    assert "🚀" not in resultado
    assert "Menuda noticia" in resultado
    assert "de verdad" in resultado


def test_limpiar_texto_locucion_quita_markdown():
    texto = "Esto es *muy* importante, casi **crucial** y `código` # titular _cursiva_"
    resultado = limpiar_texto_locucion(texto)
    for caracter in "*_#`":
        assert caracter not in resultado


def test_limpiar_texto_locucion_colapsa_espacios():
    texto = "Hola   (risas)     mundo"
    resultado = limpiar_texto_locucion(texto)
    assert "  " not in resultado


def test_trocear_frases_texto_corto_devuelve_una_lista_con_el_texto():
    texto = "Hola, ¿qué tal estás?"
    assert trocear_frases(texto) == [texto]


def test_trocear_frases_respeta_el_maximo_con_texto_largo():
    frase = "Esto es una frase de prueba con contenido variado. "
    texto = (frase * 30).strip()
    trozos = trocear_frases(texto, max_caracteres=280)
    assert len(trozos) > 1
    for trozo in trozos:
        assert len(trozo) <= 280
        assert trozo != ""


def test_trocear_frases_una_frase_larga_sin_puntuacion_se_parte():
    texto = "palabra " * 100  # ~600 caracteres, sin puntos
    texto = texto.strip()
    trozos = trocear_frases(texto, max_caracteres=280)
    assert len(trozos) > 1
    for trozo in trozos:
        assert len(trozo) <= 280
        assert trozo != ""


def test_trocear_frases_conserva_todas_las_palabras():
    texto = (
        "Primera frase con algo de contenido. Segunda frase, algo más larga, "
        "con una coma en medio. Tercera frase final que cierra el bloque de prueba "
        "con más palabras todavía para forzar el troceo del texto completo."
    )
    trozos = trocear_frases(texto, max_caracteres=60)
    palabras_originales = texto.split()
    palabras_trozos = " ".join(trozos).split()
    assert palabras_trozos == palabras_originales
