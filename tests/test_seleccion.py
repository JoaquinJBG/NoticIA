import json
import time

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
