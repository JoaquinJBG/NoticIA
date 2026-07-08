import html
import logging
import re

logger = logging.getLogger("noticia.ingesta")

_TAGS = re.compile(r"<[^>]+>")


def limpiar_html(texto):
    """Elimina etiquetas HTML y desescapa entidades. None -> ''."""
    if not texto:
        return ""
    sin_tags = _TAGS.sub("", texto)
    return html.unescape(sin_tags).strip()
