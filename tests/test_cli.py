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
