from noticia import generador


def test_llamar_ia_delega_en_motor(monkeypatch):
    llamado = {}

    def fake(system, user):
        llamado["args"] = (system, user)
        return "ok"

    monkeypatch.setattr(generador, "generar_texto", fake)
    assert generador.llamar_ia("SYS", "USER") == "ok"
    assert llamado["args"] == ("SYS", "USER")


def test_limpiar_markdown_elimina_encabezados_reglas_y_negritas():
    """Claude a veces envuelve el bloque en markdown; el TTS lo leería en voz alta."""
    crudo = "# NoticIA — Bloque Ciencia\n\n---\n\n**Álex:** Hola\nSanti: Qué tal *tío*"
    assert generador._limpiar_markdown(crudo) == "Álex: Hola\nSanti: Qué tal tío"


def test_limpiar_markdown_conserva_los_saltos_entre_intervenciones():
    crudo = "Álex: Uno\n\nSanti: Dos"
    assert generador._limpiar_markdown(crudo) == "Álex: Uno\n\nSanti: Dos"


def test_construir_guion_mantiene_estructura_y_limpia_markdown(monkeypatch):
    monkeypatch.setattr(generador, "llamar_ia", lambda s, u: "Álex: hola **fuerte**")
    datos = {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]}

    guion = generador.construir_guion(datos)

    assert "intro" in guion and "outro" in guion
    assert "espana" in guion
    assert guion["espana"] and "**" not in guion["espana"][0]
