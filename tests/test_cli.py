import asyncio
from datetime import date

import pytest

from noticia import cli
from noticia.orquestador import BloqueoOcupado, Codigo, GuionVacio


def test_solo_guion_escribe_fichero_y_no_toca_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "obtener_noticias",
        lambda: {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]},
    )
    monkeypatch.setattr(
        cli,
        "construir_guion",
        lambda noticias, fecha=None: {
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


def test_solo_guion_con_guion_vacio_lanza_y_no_escribe_fichero(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli,
        "obtener_noticias",
        lambda: {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]},
    )
    monkeypatch.setattr(
        cli,
        "construir_guion",
        lambda noticias, fecha=None: {"intro": [""], "espana": [""], "outro": [""]},
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
        lambda noticias, fecha=None: {"intro": ["Álex: hola"], "espana": ["Álex: bla"]},
    )
    salida = tmp_path / "sub" / "anidado" / "guion.md"

    ruta = cli.generar_solo_guion(str(salida))

    assert ruta == str(salida)
    assert salida.read_text(encoding="utf-8")


def test_solo_guion_usa_fecha_de_hoy_en_madrid(monkeypatch, tmp_path):
    fechas_recibidas = []
    monkeypatch.setattr(cli, "obtener_noticias", lambda: {})
    monkeypatch.setattr(cli, "hoy_madrid", lambda: date(2026, 9, 24))

    def _construir_guion(noticias, fecha=None):
        fechas_recibidas.append(fecha)
        return {"intro": ["Álex: hola"]}

    monkeypatch.setattr(cli, "construir_guion", _construir_guion)
    monkeypatch.setattr(cli.settings, "carpeta_output", str(tmp_path))

    ruta = cli.generar_solo_guion()

    assert fechas_recibidas == [date(2026, 9, 24)]
    assert ruta == str(tmp_path / "guion_2026-09-24.md")


def test_solo_audio_no_genera_guion(monkeypatch, tmp_path):
    llamadas = {"locucion": [], "ensamblado": []}

    def _no_llamar(*_a, **_k):  # el modo solo-audio NO debe tocar la generación
        raise AssertionError("construir_guion no debe invocarse en --solo-audio")

    monkeypatch.setattr(cli, "construir_guion", _no_llamar)
    monkeypatch.setattr(cli, "obtener_noticias", _no_llamar)

    class _MotorFalso:
        nombre = "edge"
        extension = "mp3"
        concurrencia_maxima = 1

        async def cargar(self):
            return None

        async def cerrar(self):
            return None

    monkeypatch.setattr(cli, "resolver_motores", lambda motor_voz: [_MotorFalso()])

    async def fake_preparar_cadena(motores):
        return motores

    monkeypatch.setattr(cli, "preparar_cadena", fake_preparar_cadena)

    async def fake_locucion(bloques, motores, carpeta, **kwargs):
        llamadas["locucion"].append(dict(bloques))
        return type(
            "ResultadoLocucionFalso",
            (),
            {"fragmentos_por_bloque": {b: ["frag.mp3"] for b in bloques}},
        )()

    monkeypatch.setattr(cli, "locutar_episodio", fake_locucion)
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
    assert llamadas["locucion"] == [{"intro": "Álex: hola"}]
    assert llamadas["ensamblado"] == [({"intro": ["frag.mp3"]}, str(salida))]


def test_solo_audio_guion_sin_bloques_falla(tmp_path):
    guion = tmp_path / "g.md"
    guion.write_text("Álex: sin encabezados\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        asyncio.run(cli.generar_solo_audio(str(guion), str(tmp_path / "o.mp3")))


def test_solo_audio_bloques_desconocidos_falla_y_no_escribe(monkeypatch, tmp_path):
    llamadas = {"ensamblado": []}
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


# --------------------------------------------------------------- main()


def test_main_publicar_devuelve_ok(monkeypatch):
    async def _fake_ejecutar(fecha, publicar, forzar, regenerar_guion, motor_voz):
        assert publicar is True
        return object()

    monkeypatch.setattr(cli, "ejecutar", _fake_ejecutar)

    assert cli.main(["--publicar"]) == int(Codigo.OK)


def test_main_guion_vacio_devuelve_3(monkeypatch):
    async def _fake_ejecutar(*a, **k):
        raise GuionVacio("sin noticias")

    monkeypatch.setattr(cli, "ejecutar", _fake_ejecutar)

    assert cli.main([]) == int(Codigo.GUION_VACIO)


def test_main_bloqueo_ocupado_devuelve_75(monkeypatch):
    async def _fake_ejecutar(*a, **k):
        raise BloqueoOcupado("ya en marcha")

    monkeypatch.setattr(cli, "ejecutar", _fake_ejecutar)

    assert cli.main([]) == int(Codigo.BLOQUEADO)


def test_main_excepcion_generica_devuelve_1(monkeypatch):
    async def _fake_ejecutar(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "ejecutar", _fake_ejecutar)

    assert cli.main([]) == int(Codigo.ERROR)


def test_main_fecha_invalida_sale_con_codigo_2():
    with pytest.raises(SystemExit) as info:
        cli.main(["--fecha", "mal"])
    assert info.value.code == 2


def test_main_solo_audio_sin_guion_sale_con_codigo_2():
    with pytest.raises(SystemExit) as info:
        cli.main(["--solo-audio"])
    assert info.value.code == 2


def test_main_sin_flags_llama_a_ejecutar_sin_publicar(monkeypatch):
    llamadas = []

    async def _fake_ejecutar(fecha, publicar, forzar, regenerar_guion, motor_voz):
        llamadas.append((fecha, publicar, forzar, regenerar_guion, motor_voz))
        return object()

    monkeypatch.setattr(cli, "ejecutar", _fake_ejecutar)

    assert cli.main([]) == int(Codigo.OK)
    assert llamadas[0][1] is False
    assert llamadas[0][2] is False
    assert llamadas[0][3] is False
    assert llamadas[0][4] is None


def test_main_pasa_forzar_regenerar_guion_y_motor_voz(monkeypatch):
    llamadas = []

    async def _fake_ejecutar(fecha, publicar, forzar, regenerar_guion, motor_voz):
        llamadas.append((fecha, publicar, forzar, regenerar_guion, motor_voz))
        return object()

    monkeypatch.setattr(cli, "ejecutar", _fake_ejecutar)

    cli.main(["--publicar", "--forzar", "--regenerar-guion", "--motor-voz", "kokoro"])

    fecha, publicar, forzar, regenerar_guion, motor_voz = llamadas[0]
    assert publicar is True
    assert forzar is True
    assert regenerar_guion is True
    assert motor_voz == "kokoro"


def test_main_fecha_explicita_se_pasa_a_ejecutar(monkeypatch):
    llamadas = []

    async def _fake_ejecutar(fecha, publicar, forzar, regenerar_guion, motor_voz):
        llamadas.append(fecha)
        return object()

    monkeypatch.setattr(cli, "ejecutar", _fake_ejecutar)

    cli.main(["--fecha", "2026-01-15"])

    assert llamadas == [date(2026, 1, 15)]
