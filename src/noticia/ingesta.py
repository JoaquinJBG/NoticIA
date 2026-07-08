import calendar
import html
import logging
import re
import time

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
