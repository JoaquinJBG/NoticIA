import gzip
import logging
from datetime import date
from pathlib import Path

import pytest

from noticia import resultados_futbol as rf

DATOS = Path(__file__).parent / "datos"
FECHA = date(2026, 3, 10)


def _bytes(nombre):
    return (DATOS / nombre).read_bytes()


@pytest.fixture
def descargas(monkeypatch):
    """Parchea el transporte con los fixtures y devuelve las URL pedidas."""
    pedidas = []

    def _descargar(url, timeout):
        pedidas.append(url)
        if url.endswith("/es.1.json"):
            return _bytes("openfootball_es1.json")
        if url.endswith("/es.2.json"):
            return _bytes("openfootball_es2.json")
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(rf, "_descargar", _descargar)
    return pedidas


def _marcadores(partidos):
    return {(p.local, p.visitante): (p.goles_local, p.goles_visitante) for p in partidos}


def test_team1_es_local_y_team2_visitante(descargas):
    partidos = rf.obtener_resultados(FECHA)

    norte = next(p for p in partidos if p.local == "Club Norte")
    assert (norte.visitante, norte.goles_local, norte.goles_visitante) == ("Club Sur", 2, 1)
    assert norte.competicion == "LaLiga"
    assert norte.goles == ()


def test_solo_partidos_con_resultado_final(descargas):
    marcadores = _marcadores(rf.obtener_resultados(FECHA))

    assert ("Club Centro", "Club Costa") not in marcadores
    assert marcadores[("Club Este", "Club Oeste")] == (0, 0)
    assert marcadores[("Club Sur", "Club Este")] == (3, 3)


def test_deduplica_el_mismo_partido(descargas):
    partidos = rf.obtener_resultados(FECHA)

    assert sum(1 for p in partidos if (p.local, p.visitante) == ("Club Norte", "Club Sur")) == 1


def test_solo_pide_la_liga_y_la_segunda_de_la_temporada(descargas):
    rf.obtener_resultados(FECHA)

    base = f"{rf.URL_BASE}/2025-26"
    assert descargas == [f"{base}/es.1.json", f"{base}/es.2.json"]


def test_respeta_la_ventana_de_dias(descargas):
    partidos = rf.obtener_resultados(FECHA, dias=1)

    assert {p.inicio.date() for p in partidos} == {date(2026, 3, 9)}
    assert ("Club Oeste", "Club Norte") not in _marcadores(rf.obtener_resultados(FECHA))


def test_ignora_un_partido_mal_formado_y_conserva_el_resto(descargas, caplog):
    with caplog.at_level(logging.WARNING, logger="noticia.resultados_futbol"):
        partidos = rf.obtener_resultados(FECHA)

    assert len(partidos) == 5
    assert "partido ignorado" in caplog.text


class _RespuestaFalsa:
    def __init__(self, cuerpo):
        self._cuerpo = cuerpo

    def read(self):
        return self._cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.mark.parametrize("comprimir", [True, False])
def test_descargar_descomprime_gzip(monkeypatch, comprimir):
    original = _bytes("openfootball_es1.json")
    cuerpo = gzip.compress(original) if comprimir else original
    visto = {}

    def _urlopen(peticion, timeout=None):
        visto["timeout"] = timeout
        visto["accept"] = peticion.get_header("Accept-encoding")
        return _RespuestaFalsa(cuerpo)

    monkeypatch.setattr(rf.urllib.request, "urlopen", _urlopen)

    assert rf._descargar("https://x/es.1.json", 7) == original
    assert visto == {"timeout": 7, "accept": "gzip"}


def test_una_competicion_que_falla_no_rompe_la_otra(monkeypatch):
    def _descargar(url, timeout):
        if url.endswith("/es.2.json"):
            raise OSError("HTTP Error 404")
        return _bytes("openfootball_es1.json")

    monkeypatch.setattr(rf, "_descargar", _descargar)

    partidos = rf.obtener_resultados(FECHA)

    assert partidos
    assert {p.competicion for p in partidos} == {"LaLiga"}


@pytest.mark.parametrize(
    "fallo",
    [OSError("sin red"), RuntimeError("boom"), ValueError("raro")],
)
def test_si_fallan_todas_devuelve_lista_vacia(monkeypatch, fallo):
    def _descargar(url, timeout):
        raise fallo

    monkeypatch.setattr(rf, "_descargar", _descargar)

    assert rf.obtener_resultados(FECHA) == []


@pytest.mark.parametrize("cuerpo", [b"no es json", b"{}", b'{"matches": 3}', b"[]"])
def test_respuesta_invalida_devuelve_lista_vacia(monkeypatch, cuerpo):
    monkeypatch.setattr(rf, "_descargar", lambda url, timeout: cuerpo)

    assert rf.obtener_resultados(FECHA) == []


def test_matches_no_iterable_en_una_competicion_conserva_la_otra(monkeypatch):
    def _descargar(url, timeout):
        if url.endswith("/es.1.json"):
            return b'{"matches": 3}'
        return _bytes("openfootball_es2.json")

    monkeypatch.setattr(rf, "_descargar", _descargar)

    assert {p.competicion for p in rf.obtener_resultados(FECHA)} == {"Segunda"}


def test_obtener_resultados_nunca_lanza_aunque_falle_el_resto(monkeypatch):
    def _fallo(*args, **kwargs):
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(rf, "_partidos_de_competicion", _fallo)

    assert rf.obtener_resultados(FECHA) == []


def test_formatear_ordena_por_competicion_y_recorta(descargas):
    partidos = rf.obtener_resultados(FECHA)

    lineas = rf.formatear_resultados_prompt(partidos, maximo=3).splitlines()

    assert lineas == [
        "LaLiga (lun 9): Club Sur 3-3 Club Este",
        "LaLiga (dom 8): Club Norte 2-1 Club Sur",
        "LaLiga (sáb 7): Club Este 0-0 Club Oeste",
    ]


def test_formatear_pone_la_segunda_tras_la_liga(descargas):
    lineas = rf.formatear_resultados_prompt(rf.obtener_resultados(FECHA)).splitlines()

    assert [linea.split(" (")[0] for linea in lineas] == ["LaLiga"] * 3 + ["Segunda"] * 2


def test_formatear_sin_partidos_devuelve_cadena_vacia():
    assert rf.formatear_resultados_prompt([]) == ""


@pytest.mark.parametrize(
    ("fecha", "temporada"),
    [
        (date(2026, 10, 22), "2026-27"),
        (date(2026, 3, 10), "2025-26"),
        (date(2026, 7, 1), "2026-27"),
        (date(2026, 6, 30), "2025-26"),
        (date(2099, 9, 1), "2099-00"),
    ],
)
def test_temporada_cambia_en_julio(fecha, temporada):
    assert rf._temporada(fecha) == temporada


def test_resultados_a_json(descargas):
    datos = rf.resultados_a_json(rf.obtener_resultados(FECHA))

    norte = next(d for d in datos if d["local"] == "Club Norte")
    assert norte["goles_local"] == 2
    assert norte["inicio"].startswith("2026-03-08T21:00")
    assert norte["goles"] == []
