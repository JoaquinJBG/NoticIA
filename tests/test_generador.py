from datetime import date

from noticia import generador, locutor


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
    datos = {"espana": [{"titular": "T", "resumen": "", "fuente": "f", "otras_fuentes": []}]}

    guion = generador.construir_guion(datos)

    assert "intro" in guion and "outro" in guion
    assert "espana" in guion
    assert guion["espana"] and "**" not in guion["espana"][0]


def test_fallbacks_de_intro_y_outro_son_locutables(monkeypatch):
    """Si Claude no responde, generar_intro/generar_outro caen a un texto fijo.

    Ese texto fijo tiene que hablar con los locutores que el parser de
    locutor.py reconoce de verdad (Álex/María), o la línea se descarta en
    silencio y el fallback se queda mudo.
    """
    monkeypatch.setattr(generador, "llamar_ia", lambda s, u: "")

    intro = generador.generar_intro({})
    outro = generador.generar_outro()

    for texto in (intro, outro):
        for linea in texto.split("\n"):
            if not linea.strip():
                continue
            parseada = locutor._parsear_linea(linea.strip())
            assert parseada is not None, f"línea no locutable en el fallback: {linea!r}"
            locutor_id, _ = parseada
            assert locutor_id in ("alex", "maria")


def test_construir_guion_incluye_la_fecha_en_los_prompts(monkeypatch):
    prompts_capturados = []

    def fake(sistema, usuario):
        prompts_capturados.append(usuario)
        return "Álex: hola"

    monkeypatch.setattr(generador, "llamar_ia", fake)
    datos = {"espana": [{"titular": "T", "resumen": "", "fuente": "f", "otras_fuentes": []}]}

    generador.construir_guion(datos, fecha=date(2026, 9, 24))

    assert prompts_capturados
    assert any("jueves 24 de septiembre" in p for p in prompts_capturados)


def test_construir_bloque_con_contexto_reintenta_si_la_ia_devuelve_vacio(monkeypatch):
    respuestas = iter(["", "Álex: hola"])
    monkeypatch.setattr(generador, "llamar_ia", lambda s, u: next(respuestas))
    monkeypatch.setattr(generador.settings, "reintentos_guion", 1)

    texto = generador.construir_bloque_con_contexto(
        "espana", [{"titular": "T", "resumen": "", "fuente": "f", "otras_fuentes": []}], "briefing"
    )

    assert texto == "Álex: hola"


def test_con_reintento_agota_los_reintentos_y_devuelve_lo_ultimo():
    llamadas = {"n": 0}

    def fn():
        llamadas["n"] += 1
        return ""

    resultado = generador._con_reintento(fn, reintentos=2)

    assert resultado == ""
    assert llamadas["n"] == 3  # intento inicial + 2 reintentos


def test_generar_outro_recibe_los_titulares(monkeypatch):
    prompts_capturados = []

    def fake(sistema, usuario):
        prompts_capturados.append(usuario)
        return "Álex: adiós"

    monkeypatch.setattr(generador, "llamar_ia", fake)

    generador.generar_outro(["Titular uno", "Titular dos"])

    assert prompts_capturados
    assert "Titular uno" in prompts_capturados[0]
    assert "Titular dos" in prompts_capturados[0]


def test_construir_guion_pasa_los_titulares_reales_al_outro(monkeypatch):
    prompts_capturados = []

    def fake(sistema, usuario):
        prompts_capturados.append(usuario)
        return "Álex: hola"

    monkeypatch.setattr(generador, "llamar_ia", fake)
    datos = {
        "espana": [
            {"titular": "Titular de España", "resumen": "", "fuente": "f", "otras_fuentes": []}
        ]
    }

    generador.construir_guion(datos)

    assert any("Titular de España" in p for p in prompts_capturados)


def test_construir_bloque_con_contexto_descarta_noticias_comerciales_o_irrelevantes(monkeypatch):
    """El guion real de hoy coló cupones de TurboTax en ia_y_actualidad: el
    prompt del bloque debe instruir explícitamente descartar promociones,
    cupones y contenido comercial sin interés para una audiencia española."""
    prompt_capturado = {}

    def fake(sistema, usuario):
        prompt_capturado["usuario"] = usuario
        return "Álex: hola"

    monkeypatch.setattr(generador, "llamar_ia", fake)

    generador.construir_bloque_con_contexto(
        "ia_y_actualidad",
        [{"titular": "T", "resumen": "", "fuente": "f", "otras_fuentes": []}],
        "briefing",
    )

    prompt = prompt_capturado["usuario"].lower()
    assert "cupon" in prompt or "cupón" in prompt
    assert "promocion" in prompt or "promoción" in prompt
    assert "comercial" in prompt
    assert "audiencia española" in prompt or "interés" in prompt
