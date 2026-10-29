"""Tests del reparto de cada episodio (presentadores + invitada rotativa)."""

from datetime import date, timedelta

import pytest

from noticia import config
from noticia.personajes import Reparto, locutores_requeridos, reparto_para_fecha


def _dia_con_invitada(n: int) -> date:
    d = date(2026, 10, 1)
    while d.toordinal() % n != 0:
        d += timedelta(days=1)
    return d


def test_habitual_son_alex_y_santi():
    reparto = Reparto.habitual()
    assert reparto.locutores == ("alex", "santi")
    assert not reparto.hay_invitada
    assert reparto.presentadores_texto == "Álex y Santi"
    assert reparto.prefijos_texto == '"Álex:" o "Santi:"'


def test_cada_n_cero_nunca_hay_invitada():
    for dia in range(60):
        assert not reparto_para_fecha(date(2026, 1, 1) + timedelta(days=dia), cada_n=0).hay_invitada


def test_la_invitada_aparece_una_vez_cada_n_dias():
    inicio = date(2026, 1, 1)
    con_invitada = [
        inicio + timedelta(days=d)
        for d in range(90)
        if reparto_para_fecha(inicio + timedelta(days=d), cada_n=3).hay_invitada
    ]
    assert len(con_invitada) == 30
    assert all((b - a).days == 3 for a, b in zip(con_invitada, con_invitada[1:], strict=False))


def test_el_resto_de_dias_son_los_presentadores_habituales():
    dia = _dia_con_invitada(3) + timedelta(days=1)
    assert reparto_para_fecha(dia, cada_n=3) == Reparto.habitual()


def test_el_reparto_es_determinista_para_una_misma_fecha():
    dia = _dia_con_invitada(3)
    for modo in ("alterna", "aleatorio", "alex", "santi"):
        assert reparto_para_fecha(dia, 3, modo) == reparto_para_fecha(dia, 3, modo)


def test_modos_fijos_sustituyen_siempre_al_mismo():
    dia = _dia_con_invitada(3)
    assert reparto_para_fecha(dia, 3, "alex").locutores == ("invitada", "santi")
    assert reparto_para_fecha(dia, 3, "santi").locutores == ("alex", "invitada")
    assert reparto_para_fecha(dia, 3, "santi").sustituido == "santi"


def test_modo_alterna_cambia_de_presentador_en_cada_aparicion():
    primero = _dia_con_invitada(3)
    sustituidos = [
        reparto_para_fecha(primero + timedelta(days=3 * i), 3, "alterna").sustituido
        for i in range(6)
    ]
    assert sustituidos == ["alex", "santi"] * 3 or sustituidos == ["santi", "alex"] * 3


def test_modo_aleatorio_usa_los_dos_presentadores():
    primero = _dia_con_invitada(3)
    sustituidos = {
        reparto_para_fecha(primero + timedelta(days=3 * i), 3, "aleatorio").sustituido
        for i in range(40)
    }
    assert sustituidos == {"alex", "santi"}


def test_reparto_con_invitada_nombra_a_la_invitada(monkeypatch):
    monkeypatch.setattr(config.settings, "invitada_nombre", "Marta")
    reparto = reparto_para_fecha(_dia_con_invitada(3), 3, "santi")
    assert reparto.presentadores_texto == "Álex y Marta"
    assert reparto.a_dict() == {"locutores": ["alex", "invitada"], "sustituido": "santi"}


def test_reparto_usa_la_config_por_defecto(monkeypatch):
    monkeypatch.setattr(config.settings, "invitada_cada_n_episodios", 2)
    monkeypatch.setattr(config.settings, "invitada_sustituye", "alex")
    dia = _dia_con_invitada(2)
    assert reparto_para_fecha(dia).locutores == ("invitada", "santi")


@pytest.mark.parametrize(
    ("n", "esperado"), [(0, ("alex", "santi")), (3, ("alex", "santi", "invitada"))]
)
def test_locutores_requeridos_segun_haya_invitada(monkeypatch, n, esperado):
    monkeypatch.setattr(config.settings, "invitada_cada_n_episodios", n)
    assert locutores_requeridos() == esperado
