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
