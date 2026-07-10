import asyncio

import pytest

from noticia import cli


def test_solo_guion_escribe_fichero_y_no_toca_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "obtener_noticias",
        lambda: {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]},
    )
    monkeypatch.setattr(
        cli,
        "construir_guion",
        lambda noticias: {
            "intro": ["Álex: hola"],
            "espana": ["Álex: bla bla"],
            "outro": ["Santi: chao"],
        },
    )
    salida = tmp_path / "guion.md"

    ruta = cli.generar_solo_guion(str(salida))

    assert ruta == str(salida)
    contenido = salida.read_text(encoding="utf-8")
    assert "## intro" in contenido
    assert "## espana" in contenido
    assert "Álex: bla bla" in contenido


def test_formatear_guion_respeta_orden_y_omite_vacios():
    guion = {"outro": ["fin"], "intro": ["ini"], "espana": []}
    texto = cli._formatear_guion(guion)
    # intro antes que outro; espana vacío se omite
    assert texto.index("## intro") < texto.index("## outro")
    assert "## espana" not in texto


def test_formatear_guion_omite_bloque_con_lineas_en_blanco():
    guion = {"intro": ["ini"], "espana": [""], "outro": ["fin"]}
    texto = cli._formatear_guion(guion)
    assert "## espana" not in texto
    assert "## intro" in texto
    assert "## outro" in texto


def test_solo_guion_con_guion_vacio_lanza_y_no_escribe_fichero(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "obtener_noticias",
        lambda: {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]},
    )
    monkeypatch.setattr(
        cli,
        "construir_guion",
        lambda noticias: {"intro": [""], "espana": [""], "outro": [""]},
    )
    salida = tmp_path / "guion.md"

    with pytest.raises(RuntimeError):
        cli.generar_solo_guion(str(salida))

    assert not salida.exists()


def test_solo_guion_crea_directorio_padre_de_salida(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "obtener_noticias",
        lambda: {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]},
    )
    monkeypatch.setattr(
        cli,
        "construir_guion",
        lambda noticias: {"intro": ["Álex: hola"], "espana": ["Álex: bla"]},
    )
    salida = tmp_path / "sub" / "anidado" / "guion.md"

    ruta = cli.generar_solo_guion(str(salida))

    assert ruta == str(salida)
    assert salida.read_text(encoding="utf-8")


def test_trocear_guion_separa_por_bloques():
    md = "## intro\n\nÁlex: hola\n\n## espana\n\nMaría: qué tal\nÁlex: bien\n"
    bloques = cli._trocear_guion(md)
    assert set(bloques) == {"intro", "espana"}
    assert bloques["intro"] == "Álex: hola"
    assert bloques["espana"] == "María: qué tal\nÁlex: bien"


def test_trocear_guion_texto_sin_bloques_devuelve_vacio():
    assert cli._trocear_guion("Álex: sin encabezados") == {}


def test_solo_audio_no_genera_guion(monkeypatch, tmp_path):
    llamadas = {"locucion": [], "ensamblado": []}

    def _no_llamar(*_a, **_k):  # el modo solo-audio NO debe tocar la generación
        raise AssertionError("construir_guion no debe invocarse en --solo-audio")

    monkeypatch.setattr(cli, "construir_guion", _no_llamar)
    monkeypatch.setattr(cli, "obtener_noticias", _no_llamar)

    async def fake_locucion(texto):
        llamadas["locucion"].append(texto)
        return ["frag.mp3"]

    monkeypatch.setattr(cli, "procesar_guion_a_audio", fake_locucion)
    monkeypatch.setattr(
        cli,
        "ensamblar_podcast_dinamico",
        lambda fragmentos, salida: llamadas["ensamblado"].append((fragmentos, salida)),
    )
    monkeypatch.setattr(cli.settings, "carpeta_temp", str(tmp_path))
    monkeypatch.setattr(cli.settings, "carpeta_output", str(tmp_path))

    guion = tmp_path / "g.md"
    guion.write_text("## intro\n\nÁlex: hola\n", encoding="utf-8")
    salida = tmp_path / "out.mp3"

    ruta = asyncio.run(cli.generar_solo_audio(str(guion), str(salida)))

    assert ruta == str(salida)
    assert llamadas["locucion"] == ["Álex: hola"]
    assert llamadas["ensamblado"] == [({"intro": ["frag.mp3"]}, str(salida))]


def test_solo_audio_guion_sin_bloques_falla(monkeypatch, tmp_path):
    guion = tmp_path / "g.md"
    guion.write_text("Álex: sin encabezados\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        asyncio.run(cli.generar_solo_audio(str(guion), str(tmp_path / "o.mp3")))


def test_solo_audio_bloques_desconocidos_falla_y_no_escribe(monkeypatch, tmp_path):
    llamadas = {"locucion": [], "ensamblado": []}

    async def fake_locucion(texto):
        llamadas["locucion"].append(texto)
        return ["frag.mp3"]

    monkeypatch.setattr(cli, "procesar_guion_a_audio", fake_locucion)
    monkeypatch.setattr(
        cli,
        "ensamblar_podcast_dinamico",
        lambda fragmentos, salida: llamadas["ensamblado"].append((fragmentos, salida)),
    )
    monkeypatch.setattr(cli.settings, "carpeta_temp", str(tmp_path))
    monkeypatch.setattr(cli.settings, "carpeta_output", str(tmp_path))

    guion = tmp_path / "g.md"
    guion.write_text("## bloque_inventado\n\nÁlex: hola\n", encoding="utf-8")
    salida = tmp_path / "out.mp3"

    with pytest.raises(RuntimeError):
        asyncio.run(cli.generar_solo_audio(str(guion), str(salida)))

    assert llamadas["ensamblado"] == []
    assert not salida.exists()
