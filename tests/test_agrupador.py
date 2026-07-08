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
    assert "_norm" not in clusters[0]  # campo interno no se filtra


def test_agrupar_categorias_de_contraste_devuelven_clusters():
    pool = {
        "espana": [_art("Sube el IPC en abril", "elpais.com")],
        "futbol": [_art("El Madrid gana la liga", "marca.com")],
    }
    resultado = agrupador.agrupar(pool)
    # España (contraste) -> dict con clusters
    assert "clusters" in resultado["espana"]
    assert isinstance(resultado["espana"]["clusters"], list)
    # Fútbol (simple) -> lista plana sin tocar
    assert resultado["futbol"] == pool["futbol"]


def test_agrupar_categoria_vacia_devuelve_estructura_valida():
    resultado = agrupador.agrupar({"ciencia": [], "friki": []})
    assert resultado["ciencia"] == {"clusters": []}
    assert resultado["friki"] == []
