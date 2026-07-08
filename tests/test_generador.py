from noticia import generador


def test_llamar_ia_delega_en_motor(monkeypatch):
    llamado = {}

    def fake(system, user):
        llamado["args"] = (system, user)
        return "ok"

    monkeypatch.setattr(generador, "generar_texto", fake)
    assert generador.llamar_ia("SYS", "USER") == "ok"
    assert llamado["args"] == ("SYS", "USER")


def test_construir_guion_mantiene_estructura_y_limpia_markdown(monkeypatch):
    monkeypatch.setattr(generador, "llamar_ia", lambda s, u: "Álex: hola **fuerte**")
    datos = {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]}

    guion = generador.construir_guion(datos)

    assert "intro" in guion and "outro" in guion
    assert "espana" in guion
    assert guion["espana"] and "**" not in guion["espana"][0]
