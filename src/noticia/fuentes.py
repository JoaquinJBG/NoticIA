from urllib.parse import quote_plus

_GN_BASE = "https://news.google.com/rss"
_GN_PARAMS = "hl=es&gl=ES&ceid=ES:es"

CATEGORIAS_CON_CONTRASTE = frozenset({"espana", "geopolitica", "ciencia", "ia_y_actualidad"})

# Lista curada amplia y plural (izquierda, centro, derecha, internacional,
# estatal). Sin etiquetas de orientación: la pluralidad la aporta la mezcla.
FEEDS_CURADOS = {
    "espana": [
        "https://elpais.com/rss/espana/el_pais.xml",
        "https://e00-elmundo.static.preney.com/elmundo/rss/espana.xml",
        "https://www.eldiario.es/rss/",
        "https://www.publico.es/rss/",
        "https://www.abc.es/rss/feeds/abc_Espana.xml",
        "https://www.larazon.es/rss/portada.xml",
        "https://www.elconfidencial.com/rss/espana/",
        "https://www.lavanguardia.com/rss/home.xml",
        "https://www.20minutos.es/rss/",
        "https://www.infolibre.es/rss/",
    ],
    "geopolitica": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.globaltimes.cn/rss/china.xml",
        "https://feeds.feedburner.com/euronews/es/home/",
        "https://www.descifrandolaguerra.es/feed/",
        "https://www.lavanguardia.com/rss/internacional.xml",
        "https://elpais.com/rss/internacional/portada.xml",
    ],
    "ia_y_actualidad": [
        "https://www.xataka.com/tag/inteligencia-artificial/rss.xml",
        "https://www.genbeta.com/tag/inteligencia-artificial/rss.xml",
        "https://www.wired.com/feed/category/gear/latest/rss",
        "https://www.technologyreview.es/rss",
    ],
    "ciencia": [
        "https://www.agenciasinc.es/rss",
        "https://elpais.com/rss/ciencia/el_pais.xml",
        "https://naukas.com/feed/",
        "https://www.scientificamerican.com/custom-feeds/rss-all/",
    ],
    "friki": [
        "https://noticias.crunchyroll.com/rss",
        "https://www.nintenderos.com/feed/",
        "https://www.cpokemon.com/feed/",
        "https://victoryroadvgc.com/feed/",
        "https://vgc.news/feed/",
        "https://www.3djuegos.com/index.php?noticias=rss",
    ],
    "futbol": [
        "https://e00-marca.static.preney.com/rss/futbol/liga_campeones.xml",
        "https://as.com/rss/futbol/primera.xml",
        "https://www.mundodeportivo.com/rss/futbol/la-liga.xml",
    ],
}

# Topics oficiales de Google News (sección "headlines/section/topic/<TOPIC>").
SECCIONES_GOOGLE_NEWS = {
    "espana": ["NATION"],
    "geopolitica": ["WORLD"],
    "ciencia": ["SCIENCE"],
    "ia_y_actualidad": ["TECHNOLOGY"],
}


def url_google_news(valor, es_busqueda=False):
    """Construye una URL de Google News RSS en español de España.

    - es_busqueda=False: feed de sección por topic (ej. "WORLD", "NATION").
    - es_busqueda=True: feed de búsqueda por término.
    """
    if es_busqueda:
        return f"{_GN_BASE}/search?q={quote_plus(valor)}&{_GN_PARAMS}"
    return f"{_GN_BASE}/headlines/section/topic/{valor}?{_GN_PARAMS}"
