import feedparser

FEEDS = {
    "espana": [
        "https://e00-elmundo.static.preney.com/elmundo/rss/espana.xml",
        "https://elpais.com/rss/espana/el_pais.xml",
        "https://www.elconfidencial.com/rss/espana/",
        "https://www.infolibre.es/rss/",
        "https://noticias.juridicas.com/rss/"
    ],
    "geopolitica": [
        "https://www.globaltimes.cn/rss/china.xml",
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.descifrandolaguerra.es/feed/",
        "https://es.reuters.com/rss/news"
    ],
    "ia_y_actualidad": [
        "https://www.xataka.com/tag/inteligencia-artificial/rss.xml",
        "https://www.wired.com/feed/category/gear/latest/rss",
        "https://www.genbeta.com/tag/inteligencia-artificial/rss.xml",
        "https://technologyreview.es/category/inteligencia-artificial/rss"
    ],
    "ciencia": [
        "https://www.agenciasinc.es/rss",
        "https://elpais.com/rss/ciencia/el_pais.xml",
        "https://naukas.com/feed/",
        "https://www.scientificamerican.com/custom-feeds/rss-all/"
    ],
    "friki": [
        "https://noticias.crunchyroll.com/rss",
        "https://www.nintenderos.com/feed/",
        "https://www.cpokemon.com/feed/",
        "https://victoryroadvgc.com/feed/",
        "https://vgc.news/feed/",
        "https://www.3djuegos.com/index.php?noticias=rss"
    ],
    "futbol": [
        "https://e00-marca.static.preney.com/rss/futbol/liga_campeones.xml",
        "https://as.com/rss/futbol/primera.xml",
        "https://www.mundodeportivo.com/rss/futbol/la-liga.xml"
    ]
}

def obtener_noticias():
    noticias_por_bloque = {}
    
    for categoria, urls in FEEDS.items():
        noticias_por_bloque[categoria] = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                # Capturamos hasta 10 noticias para tener material de sobra para debatir
                for entry in feed.entries[:10]:
                    resumen_limpio = entry.get("summary", "Sin detalles").split('<')[0] 
                    item = {
                        "titular": entry.title,
                        "resumen": resumen_limpio[:500], # Resúmenes más largos para que la IA tenga contexto
                        "fuente": url.split('/')[2]
                    }
                    noticias_por_bloque[categoria].append(item)
            except Exception:
                pass
                
    return noticias_por_bloque

if __name__ == "__main__":
    datos = obtener_noticias()
    print(f"Noticias capturadas en {len(datos)} categorías.")