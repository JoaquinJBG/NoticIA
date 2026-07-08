import calendar
import html
import logging
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import feedparser

from noticia import fuentes

logger = logging.getLogger("noticia.ingesta")

_TAGS = re.compile(r"<[^>]+>")


def limpiar_html(texto):
    """Elimina etiquetas HTML y desescapa entidades. None -> ''."""
    if not texto:
        return ""
    sin_tags = _TAGS.sub("", texto)
    return html.unescape(sin_tags).strip()


def es_reciente(fecha_struct, ventana_horas=48, ahora=None):
    """True si la fecha (time.struct_time UTC) está dentro de la ventana.

    Artículos sin fecha (None) se conservan (devuelve True).
    """
    if fecha_struct is None:
        return True
    if ahora is None:
        ahora = time.time()
    epoch = calendar.timegm(fecha_struct)
    return (ahora - epoch) <= ventana_horas * 3600


def _parsear_entrada(entry, fuente_por_defecto):
    """Convierte una entrada de feedparser en un dict de artículo, o None."""
    titular = entry.get("title")
    if not titular:
        return None

    fuente = fuente_por_defecto
    src = entry.get("source")
    if src and src.get("title"):
        fuente = src["title"]
        sufijo = f" - {fuente}"
        if titular.endswith(sufijo):
            titular = titular[: -len(sufijo)]

    return {
        "titular": titular.strip(),
        "resumen": limpiar_html(entry.get("summary", ""))[:500],
        "fuente": fuente,
        "url": entry.get("link", ""),
        "fecha": entry.get("published_parsed"),
    }


def _dedup(articulos):
    """Elimina artículos con URL idéntica o, a falta de URL, titular idéntico."""
    vistos = set()
    salida = []
    for art in articulos:
        clave = art.get("url") or art["titular"]
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append(art)
    return salida


def _dominio(url):
    net = urlparse(url).netloc
    return net[4:] if net.startswith("www.") else net


def _descargar_feed(url, fuente_por_defecto, max_entradas=15):
    feed = feedparser.parse(url)
    articulos = []
    for entry in feed.entries[:max_entradas]:
        art = _parsear_entrada(entry, fuente_por_defecto)
        if art:
            articulos.append(art)
    return articulos


def obtener_pool(ventana_horas=48, timeout=10, max_workers=12):
    """Devuelve {categoria: [articulo, ...]} limpio, reciente y sin duplicados."""
    socket.setdefaulttimeout(timeout)

    # (categoria, url, fuente_por_defecto)
    tareas = []
    for categoria, urls in fuentes.FEEDS_CURADOS.items():
        for url in urls:
            tareas.append((categoria, url, _dominio(url)))
    for categoria, topics in fuentes.SECCIONES_GOOGLE_NEWS.items():
        for topic in topics:
            tareas.append((categoria, fuentes.url_google_news(topic), "news.google.com"))

    pool = {categoria: [] for categoria in fuentes.FEEDS_CURADOS}

    def _trabajo(tarea):
        categoria, url, fuente = tarea
        try:
            return categoria, _descargar_feed(url, fuente)
        except Exception as exc:
            logger.warning("Feed fallido %s: %s", url, exc)
            return categoria, []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for categoria, articulos in executor.map(_trabajo, tareas):
            pool.setdefault(categoria, []).extend(articulos)

    for categoria in pool:
        recientes = [a for a in pool[categoria] if es_reciente(a["fecha"], ventana_horas)]
        pool[categoria] = _dedup(recientes)

    return pool
