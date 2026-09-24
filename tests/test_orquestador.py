"""Tests del orquestador: idempotencia, lock, reanudación y resumen."""

import asyncio
import json
import logging
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from noticia import orquestador
from noticia.config import Settings
from noticia.editor import ResultadoMontaje
from noticia.locutor import ResultadoLocucion
from noticia.masterizado import MedicionLoudness

FECHA = date(2026, 9, 24)


class _MotorFalso:
    def __init__(self, nombre: str = "edge") -> None:
        self.nombre = nombre
        self.extension = "mp3"
        self.concurrencia_maxima = 1
        self.cerrado = False

    def disponible(self):
        return True, ""

    async def cargar(self):
        return None

    async def sintetizar(self, texto, locutor, ruta):
        return ruta

    async def cerrar(self):
        self.cerrado = True


def _loudness() -> MedicionLoudness:
    return MedicionLoudness(
        lufs_integrados=-16.1, true_peak_dbtp=-1.2, lra=7.0, umbral=-30.0, offset=0.4
    )


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Redirige toda la E/S de disco del orquestador a `tmp_path`."""
    carpeta_output = tmp_path / "output"
    carpeta_temp = tmp_path / "temp"
    carpeta_episodios = carpeta_output / "episodios"
    carpeta_publicacion = carpeta_output / "publicacion"

    monkeypatch.setattr(orquestador.settings, "carpeta_output", str(carpeta_output))
    monkeypatch.setattr(orquestador.settings, "carpeta_temp", str(carpeta_temp))
    monkeypatch.setattr(orquestador.settings, "carpeta_publicacion", carpeta_publicacion)
    monkeypatch.setattr(Settings, "carpeta_episodios", property(lambda self: carpeta_episodios))

    monkeypatch.setattr(orquestador, "comprobar_sintonias", lambda *a, **k: [])

    llamadas = {
        "obtener_pool": 0,
        "construir_guion": 0,
        "publicar_episodio": [],
        "locutar_episodio": [],
    }

    def _fake_obtener_pool(*a, **k):
        llamadas["obtener_pool"] += 1
        return {"espana": [{"titular": "T1", "fuente": "F", "url": "http://x", "resumen": ""}]}

    def _fake_seleccionar_noticias(pool, *a, **k):
        return pool

    def _fake_construir_guion(noticias, fecha=None):
        llamadas["construir_guion"] += 1
        return {
            "intro": ["Álex: hola"],
            "espana": ["Álex: bla\nMaría: sí"],
            "outro": ["Álex: chao"],
        }

    async def _fake_locutar_episodio(bloques, motores, carpeta, **kwargs):
        llamadas["locutor_episodio_bloques"] = set(bloques)
        rutas = {}
        for bloque in bloques:
            ruta = Path(carpeta) / f"{bloque}.mp3"
            ruta.write_bytes(b"audio falso")
            rutas[bloque] = [ruta]
        return ResultadoLocucion(
            fragmentos_por_bloque=rutas,
            motores_usados=Counter({motores[0].nombre: len(bloques)}),
            fallidos=[],
            descartadas=0,
            total_turnos=len(bloques),
        )

    def _fake_ensamblar(fragmentos_por_bloque, archivo_salida, metadatos=None):
        archivo_salida = Path(archivo_salida)
        archivo_salida.parent.mkdir(parents=True, exist_ok=True)
        archivo_salida.write_bytes(b"mp3 falso")
        capitulos = [(bloque, float(i)) for i, bloque in enumerate(fragmentos_por_bloque)]
        return ResultadoMontaje(
            ruta=archivo_salida,
            duracion_s=123.4,
            capitulos=capitulos,
            sintonias_faltantes=[],
            loudness=_loudness(),
        )

    def _fake_resolver_motores(motor_voz=None, info_gpu=None):
        return [_MotorFalso("edge")]

    async def _fake_preparar_cadena(motores):
        return motores

    def _fake_episodio_publicado(fecha, carpeta=None):
        return False

    def _fake_publicar_episodio(ep, carpeta=None, ahora=None):
        llamadas["publicar_episodio"].append(ep)
        ruta_feed = carpeta_publicacion / "feed.xml"
        ruta_feed.parent.mkdir(parents=True, exist_ok=True)
        ruta_feed.write_text("<rss></rss>", encoding="utf-8")
        return ruta_feed

    monkeypatch.setattr(orquestador, "obtener_pool", _fake_obtener_pool)
    monkeypatch.setattr(orquestador, "seleccionar_noticias", _fake_seleccionar_noticias)
    monkeypatch.setattr(orquestador, "construir_guion", _fake_construir_guion)
    monkeypatch.setattr(orquestador, "locutar_episodio", _fake_locutar_episodio)
    monkeypatch.setattr(orquestador, "ensamblar_podcast_dinamico", _fake_ensamblar)
    monkeypatch.setattr(orquestador, "resolver_motores", _fake_resolver_motores)
    monkeypatch.setattr(orquestador, "preparar_cadena", _fake_preparar_cadena)
    monkeypatch.setattr(orquestador, "episodio_publicado", _fake_episodio_publicado)
    monkeypatch.setattr(orquestador, "publicar_episodio", _fake_publicar_episodio)

    return llamadas


def test_primer_ejecutar_produce_y_segundo_ya_existia(entorno):
    resumen1 = asyncio.run(orquestador.ejecutar(FECHA, publicar=False))
    assert resumen1.estado == "producido"
    assert resumen1.codigo == orquestador.Codigo.OK
    assert entorno["construir_guion"] == 1

    resumen2 = asyncio.run(orquestador.ejecutar(FECHA, publicar=False))
    assert resumen2.estado == "ya_existia"
    assert entorno["construir_guion"] == 1  # no se ha vuelto a llamar
    assert entorno["obtener_pool"] == 1


def test_forzar_rehace_audio_sin_llamar_a_construir_guion(entorno):
    asyncio.run(orquestador.ejecutar(FECHA, publicar=False))
    assert entorno["construir_guion"] == 1

    resumen = asyncio.run(orquestador.ejecutar(FECHA, publicar=False, forzar=True))

    assert entorno["construir_guion"] == 1  # el guion no se ha regenerado
    assert resumen.codigo == orquestador.Codigo.OK


def test_regenerar_guion_llama_de_nuevo_al_generador(entorno):
    asyncio.run(orquestador.ejecutar(FECHA, publicar=False))
    assert entorno["construir_guion"] == 1

    asyncio.run(orquestador.ejecutar(FECHA, publicar=False, forzar=True, regenerar_guion=True))

    assert entorno["construir_guion"] == 2


def _guion_solo_reserva() -> dict[str, list[str]]:
    """Comportamiento real de `construir_guion` sin ninguna noticia: intro y outro
    siempre traen texto de reserva (ver `generador.generar_intro`/`generar_outro`),
    y ningún bloque de `CATEGORIAS_NOTICIAS` se añade al guion."""
    return {
        "intro": ["Álex: ¡Bienvenidos! \nMaría: ¡Hola a todos, encantada de estar aquí!"],
        "outro": ["Álex: Gracias por escucharnos. \nMaría: ¡Hasta pronto!"],
    }


def test_guion_tiene_noticias_ignora_intro_y_outro():
    assert orquestador.guion_tiene_noticias(_guion_solo_reserva()) is False


def test_guion_tiene_noticias_true_si_hay_bloque_de_noticias_con_texto():
    guion = {**_guion_solo_reserva(), "espana": ["Álex: bla"]}
    assert orquestador.guion_tiene_noticias(guion) is True


def test_generar_guion_con_intro_outro_de_reserva_y_sin_noticias_lanza_guion_vacio(
    entorno, monkeypatch
):
    """Regresión: antes, `generar_guion` consideraba "con contenido" cualquier guion
    con texto en CUALQUIER bloque, incluidos intro/outro -- que siempre lo tienen
    (texto de reserva). Eso hacía que GuionVacio nunca saltara de verdad."""
    monkeypatch.setattr(orquestador.settings, "reintentos_guion", 0)
    monkeypatch.setattr(orquestador.settings, "espera_reintento_guion_s", 0)
    monkeypatch.setattr(
        orquestador, "construir_guion", lambda noticias, fecha=None: _guion_solo_reserva()
    )

    with pytest.raises(orquestador.GuionVacio):
        orquestador.generar_guion(FECHA)


def test_guion_vacio_tras_reintentos_no_crea_ni_mp3_ni_guion(entorno, monkeypatch):
    monkeypatch.setattr(orquestador.settings, "reintentos_guion", 0)
    monkeypatch.setattr(orquestador.settings, "espera_reintento_guion_s", 0)
    monkeypatch.setattr(
        orquestador, "construir_guion", lambda noticias, fecha=None: _guion_solo_reserva()
    )

    with pytest.raises(orquestador.GuionVacio):
        asyncio.run(orquestador.ejecutar(FECHA, publicar=False))

    carpeta = orquestador.carpeta_episodio(FECHA)
    assert not (carpeta / "guion.md").exists()
    assert not (carpeta / "noticias.json").exists()
    assert not (carpeta / f"NoticIA_{FECHA.isoformat()}.mp3").exists()


def test_guion_md_sin_mp3_se_reanuda_sin_llamar_a_claude(entorno):
    carpeta = orquestador.carpeta_episodio(FECHA)
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "guion.md").write_text(
        orquestador.formatear_guion(
            {"intro": ["Álex: hola"], "espana": ["Álex: bla"], "outro": ["Álex: chao"]}
        ),
        encoding="utf-8",
    )
    (carpeta / "noticias.json").write_text(
        json.dumps({"espana": [{"titular": "T", "fuente": "F", "url": "u", "otras_fuentes": []}]}),
        encoding="utf-8",
    )

    resumen = asyncio.run(orquestador.ejecutar(FECHA, publicar=False))

    assert resumen.estado == "reanudado"
    assert entorno["construir_guion"] == 0
    assert entorno["obtener_pool"] == 0


def test_publicar_reanuda_publicacion_sin_rehacer_audio(entorno):
    asyncio.run(orquestador.ejecutar(FECHA, publicar=False))
    assert entorno["publicar_episodio"] == []

    resumen = asyncio.run(orquestador.ejecutar(FECHA, publicar=True))

    assert resumen.estado == "reanudado"
    assert len(entorno["publicar_episodio"]) == 1
    assert entorno["construir_guion"] == 1


def test_ejecutar_publicar_ya_publicado_no_hace_nada(entorno, monkeypatch):
    monkeypatch.setattr(orquestador, "episodio_publicado", lambda fecha, carpeta=None: True)
    asyncio.run(orquestador.ejecutar(FECHA, publicar=False))

    resumen = asyncio.run(orquestador.ejecutar(FECHA, publicar=True))

    assert resumen.estado == "ya_existia"
    assert entorno["publicar_episodio"] == []


def test_log_por_episodio_se_crea(entorno):
    asyncio.run(orquestador.ejecutar(FECHA, publicar=False))
    carpeta = orquestador.carpeta_episodio(FECHA)
    assert (carpeta / "produccion.log").exists()


def test_resumen_aparece_en_el_log(entorno, caplog):
    with caplog.at_level(logging.INFO, logger="noticia.orquestador"):
        asyncio.run(orquestador.ejecutar(FECHA, publicar=False))
    assert any("RESUMEN" in registro.message for registro in caplog.records)


def test_resumen_se_escribe_en_el_produccion_log_del_episodio(entorno, caplog):
    """Regresión: el resumen se registraba DESPUÉS de quitar el handler del
    episodio, así que nunca llegaba a produccion.log."""
    with caplog.at_level(logging.INFO):
        asyncio.run(orquestador.ejecutar(FECHA, publicar=False))
    carpeta = orquestador.carpeta_episodio(FECHA)
    contenido = (carpeta / "produccion.log").read_text(encoding="utf-8")
    assert "RESUMEN" in contenido


def test_fallo_al_producir_se_registra_en_el_produccion_log_del_episodio(
    entorno, monkeypatch, caplog
):
    """Regresión: el motivo del fallo (logger.exception) debe quedar en el
    produccion.log del episodio, no perderse tras quitar el handler."""
    monkeypatch.setattr(orquestador.settings, "reintentos_guion", 0)
    monkeypatch.setattr(orquestador.settings, "espera_reintento_guion_s", 0)
    monkeypatch.setattr(
        orquestador, "construir_guion", lambda noticias, fecha=None: _guion_solo_reserva()
    )

    with caplog.at_level(logging.INFO), pytest.raises(orquestador.GuionVacio):
        asyncio.run(orquestador.ejecutar(FECHA, publicar=False))

    carpeta = orquestador.carpeta_episodio(FECHA)
    contenido = (carpeta / "produccion.log").read_text(encoding="utf-8")
    assert "Fallo produciendo el episodio" in contenido
    assert "GuionVacio" in contenido


# --------------------------------------------------------------- bloqueo_exclusivo


def test_bloqueo_exclusivo_segundo_intento_lanza_bloqueo_ocupado(tmp_path):
    ruta = tmp_path / ".noticia.lock"
    with orquestador.bloqueo_exclusivo(ruta):
        with pytest.raises(orquestador.BloqueoOcupado):
            with orquestador.bloqueo_exclusivo(ruta):
                pass


def test_bloqueo_exclusivo_se_libera_al_salir(tmp_path):
    ruta = tmp_path / ".noticia.lock"
    with orquestador.bloqueo_exclusivo(ruta):
        pass
    with orquestador.bloqueo_exclusivo(ruta):
        pass


# --------------------------------------------------------------- formatear/trocear


def test_formatear_y_trocear_guion_son_inversos():
    guion = {"intro": ["Álex: hola"], "espana": ["Álex: bla", "María: sí"], "outro": [""]}
    texto = orquestador.formatear_guion(guion)
    assert "## outro" not in texto
    bloques = orquestador.trocear_guion(texto)
    assert bloques["intro"] == "Álex: hola"
    assert bloques["espana"] == "Álex: bla\nMaría: sí"
