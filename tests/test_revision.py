"""Tests del control de neutralidad (WP-13, D-02 y D-03)."""

import json
from pathlib import Path

from noticia.revision import (
    ADJETIVO_VALORATIVO,
    ATRIBUCION_SIN_FUENTE,
    PROMOCION,
    VEREDICTO,
    revisar_guion,
)

DATOS = Path(__file__).parent / "datos" / "guiones"


def _marcas(nombre: str) -> list[tuple[str, str]]:
    guion = (DATOS / nombre).read_text(encoding="utf-8")
    return [(h.tipo, h.fragmento) for h in revisar_guion(guion, {}).hallazgos]


def _hay(marcas, tipo, texto):
    return any(t == tipo and texto in f for t, f in marcas)


def test_prd01_veredicto_judicial_en_guion_validacion():
    assert _hay(_marcas("guion_validacion.md"), VEREDICTO, "apunta más a la segunda lectura")


def test_prd01_medios_sin_citar_en_guion_validacion():
    assert _hay(_marcas("guion_validacion.md"), ATRIBUCION_SIN_FUENTE, "ciertos medios reciclan")


def test_prd01_afinidad_de_medios_en_guion_0924():
    assert _hay(_marcas("guion_2026-09-24.md"), ATRIBUCION_SIN_FUENTE, "más cercanos al PP")


def test_prd01_intencion_de_un_gobierno_en_guion_0924():
    assert _hay(_marcas("guion_2026-09-24.md"), VEREDICTO, "legitimarse puertas adentro")


def test_ux07_varios_analisis_sin_nombrar_en_guion_0924():
    assert _hay(_marcas("guion_2026-09-24.md"), ATRIBUCION_SIN_FUENTE, "varios análisis")


def test_no_marca_el_cierre_ninguna_es_toda_la_verdad():
    marcas = _marcas("guion_2026-09-24.md")
    assert not any("ninguna es toda la verdad" in f for _, f in marcas)


def test_atribucion_con_segun_no_se_marca():
    guion = {"espana": "Álex: Según El País, varios análisis apuntan a un retraso."}
    assert revisar_guion(guion, {}).limpio


def test_adjetivo_valorativo_sobre_actor_politico():
    guion = {"espana": "Álex: El Gobierno es incompetente y el PP también."}
    tipos = [h.tipo for h in revisar_guion(guion, {}).hallazgos]
    assert tipos == [ADJETIVO_VALORATIVO]


def test_adjetivo_dentro_de_cita_atribuida_se_permite():
    guion = {"espana": 'Álex: Vox llama al Gobierno "corrupto", y el Gobierno lo niega.'}
    assert revisar_guion(guion, {}).limpio


def test_promocion_en_cualquier_bloque():
    guion = {"outro": "María: No os perdáis los descuentos del Black Friday."}
    assert [h.tipo for h in revisar_guion(guion, {}).hallazgos] == [PROMOCION]


def test_guion_neutral_queda_limpio():
    guion = {
        "espana": "Álex: El PP sostiene que el decreto invade competencias.\n"
        "María: El Gobierno responde que se ajusta a la ley."
    }
    assert revisar_guion(guion, {}).limpio


def test_hallazgo_indica_bloque_y_linea_dentro_del_bloque():
    guion = {"ciencia": "Álex: Hola.\nMaría: Ciertos medios exageran."}
    (h,) = revisar_guion(guion, {}).hallazgos
    assert (h.bloque, h.linea) == ("ciencia", 2)


def test_recuento_de_fuentes_por_bloque():
    noticias = {
        "espana": [
            {"titular": "a", "fuente": "El País", "otras_fuentes": ["ABC"]},
            {"titular": "b", "fuente": "El País", "otras_fuentes": []},
            {"titular": "c", "fuente": "RTVE"},
        ],
        "ciencia": [],
    }
    resultado = revisar_guion({}, noticias)
    assert resultado.fuentes_por_bloque == {
        "espana": {"El País": 2, "ABC": 1, "RTVE": 1},
        "ciencia": {},
    }


def test_a_dict_es_serializable():
    resultado = revisar_guion({"espana": "Álex: Ciertos medios exageran."}, {"espana": []})
    datos = json.loads(json.dumps(resultado.a_dict()))
    assert datos["limpio"] is False
    assert datos["hallazgos"][0]["tipo"] == ATRIBUCION_SIN_FUENTE


def test_los_hallazgos_se_registran_como_warning(caplog):
    with caplog.at_level("WARNING", logger="noticia.revision"):
        revisar_guion({"espana": "Álex: Ciertos medios exageran."}, {})
    assert any("atribucion_sin_fuente" in r.message for r in caplog.records)
