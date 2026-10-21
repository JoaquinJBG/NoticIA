import itertools

import pytest

from noticia import agrupador


def test_normalizar_quita_acentos_stopwords_y_puntuacion():
    assert (
        agrupador._normalizar("El Gobierno de España aprueba la Reforma!")
        == "gobierno espana aprueba reforma"
    )


def test_normalizar_vacio():
    assert agrupador._normalizar("") == ""


def _art(titular, fuente):
    return {"titular": titular, "resumen": "", "fuente": fuente, "url": titular + fuente}


def test_agrupar_junta_misma_noticia_de_fuentes_distintas():
    arts = [
        _art("El Gobierno aprueba la reforma laboral", "elpais.com"),
        _art("El Gobierno aprueba reforma laboral hoy", "abc.es"),
        _art("Resultados de la Champions League", "marca.com"),
    ]
    clusters = agrupador.agrupar_categoria(arts, umbral=70)
    # El cluster con 2 fuentes va primero
    assert len(clusters[0]["articulos"]) == 2
    fuentes_primer_cluster = {a["fuente"] for a in clusters[0]["articulos"]}
    assert fuentes_primer_cluster == {"elpais.com", "abc.es"}
    # La noticia no relacionada queda en su propio cluster
    assert any(len(c["articulos"]) == 1 for c in clusters)


def test_agrupar_categoria_clusters_tienen_tema():
    arts = [_art("Noticia única importante", "medio.com")]
    clusters = agrupador.agrupar_categoria(arts)
    assert clusters[0]["tema"] == "Noticia única importante"
    assert not any(k.startswith("_") for k in clusters[0])


def test_agrupar_categoria_vacia_devuelve_lista_vacia():
    assert agrupador.agrupar_categoria([]) == []


def test_titular_de_una_palabra_no_se_funde_con_el_que_lo_contiene():
    arts = [
        _art("Sánchez", "x"),
        _art("Sánchez anuncia un nuevo plan de vivienda para jóvenes", "y"),
    ]
    assert len(agrupador.agrupar_categoria(arts)) == 2


def test_titular_ampliado_se_agrupa_con_el_corto():
    arts = [
        _art("Feijóo pide elecciones anticipadas", "x"),
        _art("Feijóo pide elecciones anticipadas tras la derrota del PP en Galicia", "y"),
    ]
    clusters = agrupador.agrupar_categoria(arts)
    assert len(clusters) == 1
    assert len(clusters[0]["articulos"]) == 2


def test_un_solo_token_compartido_no_agrupa():
    arts = [_art("Gobierno", "x"), _art("Gobierno aprueba presupuestos", "z")]
    assert len(agrupador.agrupar_categoria(arts)) == 2


def test_titular_corto_identico_de_varias_fuentes_se_agrupa():
    arts = [_art("Dimite Mazón", f) for f in ("x", "y", "z")]
    clusters = agrupador.agrupar_categoria(arts)
    assert len(clusters) == 1
    assert len(clusters[0]["articulos"]) == 3


def test_titular_corto_no_se_funde_con_el_largo_que_lo_contiene():
    arts = [
        _art("Pedro Sánchez", "x"),
        _art("Pedro Sánchez anuncia un nuevo plan de vivienda", "y"),
    ]
    assert len(agrupador.agrupar_categoria(arts)) == 2


def test_principal_no_depende_del_orden_de_entrada():
    arts = [
        _art("Feijóo pide elecciones anticipadas", "elpais.com"),
        _art("Feijóo pide elecciones anticipadas tras la derrota del PP en Galicia", "abc.es"),
        _art("Feijóo pide elecciones anticipadas tras la derrota en Galicia", "elmundo.es"),
    ]
    directo = agrupador.agrupar_categoria(arts)
    inverso = agrupador.agrupar_categoria(list(reversed(arts)))
    assert len(directo) == len(inverso) == 1
    assert directo[0]["articulos"][0] == inverso[0]["articulos"][0]
    assert directo[0]["tema"] == inverso[0]["tema"]


def test_principal_es_el_de_mayor_similitud_media():
    arts = [
        _art("Feijóo pide elecciones anticipadas", "a.com"),
        _art("Feijóo pide elecciones anticipadas tras la derrota del PP en Galicia", "b.com"),
        _art("Feijóo pide elecciones anticipadas derrota PP Galicia", "c.com"),
    ]
    principal = agrupador.agrupar_categoria(arts)[0]["articulos"][0]
    assert principal["fuente"] == "c.com"


def test_empate_de_similitud_se_resuelve_por_fuente_alfabetica():
    arts = [
        _art("El Gobierno aprueba la reforma laboral", "zeta.com"),
        _art("El Gobierno aprueba la reforma laboral", "alfa.com"),
    ]
    for orden in (arts, list(reversed(arts))):
        principal = agrupador.agrupar_categoria(orden)[0]["articulos"][0]
        assert principal["fuente"] == "alfa.com"


def test_agrupar_ya_no_existe():
    assert not hasattr(agrupador, "agrupar")


def _n_clusters(t1, t2):
    return len(agrupador.agrupar_categoria([_art(t1, "x"), _art(t2, "y")]))


@pytest.mark.parametrize(
    "t1, t2",
    [
        ("Rusia ataca Kiev con drones", "Ucrania ataca Moscú con drones"),
        ("Muere el actor Robert Redford", "Muere el actor Gene Hackman"),
    ],
)
def test_dos_palabras_genericas_comunes_no_funden_hechos_distintos(t1, t2):
    assert _n_clusters(t1, t2) == 2


@pytest.mark.parametrize(
    "t1, t2",
    [
        (
            "Feijóo pide elecciones anticipadas",
            "Feijóo pide elecciones anticipadas tras la derrota del PP en Galicia y anuncia "
            "una ofensiva parlamentaria contra el Gobierno de Sánchez",
        ),
        (
            "Feijóo pide unas elecciones anticipadas",
            "Feijóo pide elección anticipada tras la derrota del PP en Galicia",
        ),
        (
            "Feijóo pide elecciones anticipadas",
            "Feijóo, tras la derrota en Galicia: «Hay que ir a elecciones anticipadas ya»",
        ),
    ],
)
def test_titular_ampliado_o_con_otro_numero_sigue_siendo_la_misma_historia(t1, t2):
    assert _n_clusters(t1, t2) == 1


def test_composicion_del_cluster_no_depende_del_orden_de_entrada():
    arts = [
        _art("Feijóo pide elecciones anticipadas", "elpais"),
        _art("Feijóo pide elecciones anticipadas tras la derrota del PP en Galicia", "abc"),
        _art("Derrota del PP en Galicia", "eldiario"),
    ]
    resultados = set()
    for orden in itertools.permutations(arts):
        clusters = agrupador.agrupar_categoria(list(orden))
        resultados.add(
            tuple((c["tema"], tuple(a["fuente"] for a in c["articulos"])) for c in clusters)
        )
    assert len(resultados) == 1
