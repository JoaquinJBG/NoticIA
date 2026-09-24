import json
import logging
import time

import pytest

from noticia import seleccion


def _art(titular, fuente, fecha=None, resumen=""):
    return {
        "titular": titular,
        "resumen": resumen,
        "fuente": fuente,
        "url": f"https://{fuente}/{titular}",
        "fecha": fecha,
    }


def _fecha(dias_atras=0):
    """time.struct_time UTC, como lo produce feedparser."""
    epoch = time.time() - dias_atras * 86400
    return time.gmtime(epoch)


def test_seleccionar_noticias_respeta_max_por_categoria():
    pool = {
        "futbol": [_art(f"Noticia {i}", "marca.com", _fecha(i)) for i in range(5)],
    }
    resultado = seleccion.seleccionar_noticias(pool, max_por_categoria=2)
    assert len(resultado["futbol"]) == 2


def test_seleccionar_noticias_pone_primero_el_cluster_con_mas_fuentes():
    pool = {
        "espana": [
            _art("El Gobierno aprueba la reforma laboral", "elpais.com"),
            _art("El Gobierno aprueba reforma laboral hoy", "abc.es"),
            _art("Otra noticia sin relación con nadie", "elmundo.es"),
        ],
    }
    resultado = seleccion.seleccionar_noticias(pool, max_por_categoria=8)
    principal = resultado["espana"][0]
    assert principal["fuente"] in ("elpais.com", "abc.es")
    assert principal["otras_fuentes"] == [
        f for f in ("elpais.com", "abc.es") if f != principal["fuente"]
    ]


def test_seleccionar_noticias_categoria_sin_contraste_se_ordena_por_fecha():
    pool = {
        "futbol": [
            _art("Antigua", "marca.com", _fecha(5)),
            _art("Reciente", "marca.com", _fecha(0)),
            _art("Sin fecha", "marca.com", None),
        ],
    }
    resultado = seleccion.seleccionar_noticias(pool, max_por_categoria=8)
    titulares = [n["titular"] for n in resultado["futbol"]]
    assert titulares == ["Reciente", "Antigua", "Sin fecha"]


def test_seleccionar_noticias_pool_vacio_por_categoria():
    resultado = seleccion.seleccionar_noticias({"ciencia": [], "friki": []})
    assert resultado == {"ciencia": [], "friki": []}


def test_formatear_noticias_prompt_no_contiene_struct_time():
    noticias = [
        {
            "titular": "Test",
            "fuente": "elpais.com",
            "otras_fuentes": ["abc.es"],
            "resumen": "Un resumen cualquiera",
            "fecha": time.gmtime(),
        }
    ]
    texto = seleccion.formatear_noticias_prompt(noticias)
    assert "struct_time" not in texto
    assert "Test" in texto
    assert "elpais.com" in texto
    assert "también: abc.es" in texto


def test_formatear_noticias_prompt_sin_otras_fuentes():
    noticias = [{"titular": "T", "fuente": "f", "resumen": "r", "otras_fuentes": []}]
    texto = seleccion.formatear_noticias_prompt(noticias)
    assert texto == "- T (f): r"


def test_noticias_a_json_es_serializable_y_filtra_campos():
    noticias = {
        "espana": [
            {
                "titular": "T",
                "fuente": "f",
                "url": "https://f/t",
                "otras_fuentes": ["g"],
                "resumen": "esto no debe salir",
                "fecha": time.gmtime(),
            }
        ]
    }
    resultado = seleccion.noticias_a_json(noticias)
    assert resultado == {
        "espana": [{"titular": "T", "fuente": "f", "url": "https://f/t", "otras_fuentes": ["g"]}]
    }
    assert json.dumps(resultado)  # no lanza


def test_epoch_o_menos_infinito_orden():
    reciente = seleccion._epoch_o_menos_infinito(_fecha(0))
    antigua = seleccion._epoch_o_menos_infinito(_fecha(5))
    assert reciente > antigua
    assert seleccion._epoch_o_menos_infinito(None) < antigua


# --------------------------------------------------------------- es_contenido_comercial


def _noticia(titular, resumen=""):
    return {"titular": titular, "resumen": resumen}


CASOS_COMERCIALES = [
    "Las primeras ofertas de Prime Day de Roborock",
    "TurboTax lanza cupones para septiembre",
    "Black Friday: los mejores chollos en portátiles",
    "Cyber Monday 2026: hasta el 70% de descuento en electrónica",
    "Rebajas de verano: precio mínimo histórico para este móvil",
    "Este código promocional te da un 20% off en tu próxima compra",
    "El mejor deal del día: auriculares a mitad de precio",
    "Amazon Sale: los mejores chollos de la semana",
    "Estas son las mejores ofertas para el regreso al cole",
]

CASOS_NO_COMERCIALES = [
    "El Gobierno amplía la oferta de vivienda pública",
    "Oferta pública de empleo de 2026",
    "El ministerio publica la oferta de empleo de bombero",
    "Las universidades amplían su oferta de plazas para el curso que viene",
    "El PIB sale disparado tras el dato de empleo",
    "El paciente sale del hospital tras la operación",
    "España sale de la recesión según el último informe económico",
    "Un estudio confirma que el cambio climático avanza más rápido de lo previsto",
]


@pytest.mark.parametrize("titular", CASOS_COMERCIALES)
def test_es_contenido_comercial_detecta_casos_reales(titular):
    assert seleccion.es_contenido_comercial(_noticia(titular)) is True


@pytest.mark.parametrize("titular", CASOS_NO_COMERCIALES)
def test_es_contenido_comercial_no_marca_falsos_positivos(titular):
    assert seleccion.es_contenido_comercial(_noticia(titular)) is False


def test_es_contenido_comercial_sin_distinguir_mayusculas_ni_tildes():
    assert seleccion.es_contenido_comercial(_noticia("CUPÓN de descuento del 50%")) is True
    assert seleccion.es_contenido_comercial(_noticia("cupon de descuento del 50%")) is True


def test_es_contenido_comercial_mira_tambien_el_resumen():
    noticia = _noticia("Nueva colección de zapatillas", resumen="chollo: 30% de descuento hoy")
    assert seleccion.es_contenido_comercial(noticia) is True


def test_es_contenido_comercial_resumen_none_no_rompe():
    noticia = {"titular": "Oferta pública de empleo de 2026", "resumen": None}
    assert seleccion.es_contenido_comercial(noticia) is False


def test_seleccionar_noticias_descarta_contenido_comercial_antes_de_seleccionar():
    pool = {
        "espana": [
            _art("Las primeras ofertas de Prime Day de Roborock", "elpais.com"),
            _art("El Gobierno amplía la oferta de vivienda pública", "elmundo.es"),
        ],
    }
    resultado = seleccion.seleccionar_noticias(pool, max_por_categoria=8)
    titulares = [n["titular"] for n in resultado["espana"]]
    assert titulares == ["El Gobierno amplía la oferta de vivienda pública"]


def test_seleccionar_noticias_registra_las_descartadas_por_categoria(caplog):
    pool = {
        "espana": [
            _art("Las primeras ofertas de Prime Day de Roborock", "elpais.com"),
            _art("TurboTax lanza cupones para septiembre", "abc.es"),
            _art("El Gobierno amplía la oferta de vivienda pública", "elmundo.es"),
        ],
    }
    with caplog.at_level(logging.INFO, logger="noticia.seleccion"):
        seleccion.seleccionar_noticias(pool, max_por_categoria=8)

    mensajes = [r.message for r in caplog.records]
    assert any("2" in m and "espana" in m for m in mensajes)
