"""Selección de las noticias que entran en el guion de cada bloque.

Reduce el pool de la ingesta a las N noticias más relevantes por categoría:
en las categorías de contraste, una por cluster (la más contrastada primero);
en el resto, las más recientes.
"""

import calendar
import logging
import re
import unicodedata
from collections.abc import Mapping

from noticia.agrupador import agrupar_categoria
from noticia.config import settings
from noticia.fuentes import CATEGORIAS_CON_CONTRASTE

logger = logging.getLogger("noticia.seleccion")

# --------------------------------------------------------------- filtro comercial

# Términos que, por sí solos, ya delatan contenido comercial (publirreportajes,
# guías de compra, cazadores de chollos...). No hace falta contexto adicional.
_PATRON_COMERCIAL_DIRECTO = re.compile(
    r"\b("
    r"descuentos?"
    r"|chollos?"
    r"|rebajas?"
    r"|cupon(?:es)?"
    r"|prime day"
    r"|black friday"
    r"|cyber monday"
    r"|a mitad de precio"
    r"|precio minimo"
    r"|codigos?\s+promocionales?"
    r"|deals?"
    r"|mejores ofertas"
    r")\b"
)
_PATRON_PORCENTAJE_COMERCIAL = re.compile(r"%\s*(?:de\s+descuento|off)\b")

# "oferta(s)" y "sale" son ambiguos en español ("oferta de empleo", "el PIB
# sale disparado"): solo cuentan como comerciales si aparecen junto a alguna
# de estas palabras de contexto, o "ofertas" en plural seguido de "de"/"en"
# (salvo que sea una oferta de empleo/plazas/vivienda/formación).
_CONTEXTO_COMERCIAL = r"(?:precio|€|descuento|prime|amazon|tienda|chollo)"
_PATRON_CONTEXTO_COMERCIAL = re.compile(_CONTEXTO_COMERCIAL)
_PATRON_OFERTA_PALABRA = re.compile(r"\bofertas?\b")
_PATRON_OFERTAS_PLURAL_DE_EN = re.compile(r"\bofertas\s+(?:de|en)\b")
_PATRON_OFERTA_NO_COMERCIAL = re.compile(
    r"\bofertas?\s+(?:de|en)\s+"
    r"(?:empleo(?:\s+publico)?|trabajo|vivienda|formacion|becas?|matricula|plazas?)\b"
)
_PATRON_SALE_PALABRA = re.compile(r"\bsale\b")


def _sin_tildes(texto: str) -> str:
    """Quita diacríticos: 'código' -> 'codigo'. No toca '€' ni '%'."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _normalizar(texto: str) -> str:
    return _sin_tildes(texto).lower()


def _oferta_es_comercial(texto: str) -> bool:
    if not _PATRON_OFERTA_PALABRA.search(texto):
        return False
    if _PATRON_OFERTA_NO_COMERCIAL.search(texto):
        return False
    if _PATRON_CONTEXTO_COMERCIAL.search(texto):
        return True
    return bool(_PATRON_OFERTAS_PLURAL_DE_EN.search(texto))


def _sale_es_comercial(texto: str) -> bool:
    if not _PATRON_SALE_PALABRA.search(texto):
        return False
    return bool(_PATRON_CONTEXTO_COMERCIAL.search(texto))


def es_contenido_comercial(noticia: dict) -> bool:
    """True si el titular/resumen de `noticia` es contenido comercial.

    Detecta ofertas, descuentos, chollos, cupones, Black Friday/Cyber Monday/
    Prime Day, códigos promocionales, etc. Sin distinguir mayúsculas ni
    tildes. 'oferta(s)' y 'sale' son términos ambiguos en español (una
    "oferta de empleo" o "el PIB sale disparado" no son contenido comercial)
    y solo cuentan si aparecen junto a contexto comercial (precio, €,
    descuento, Prime, Amazon, tienda, chollo) o, para "ofertas" en plural,
    seguido de "de"/"en" y no de empleo/plazas/vivienda/formación.
    """
    titular = noticia.get("titular", "") or ""
    resumen = noticia.get("resumen", "") or ""
    texto = _normalizar(f"{titular} {resumen}")

    if _PATRON_COMERCIAL_DIRECTO.search(texto):
        return True
    if _PATRON_PORCENTAJE_COMERCIAL.search(texto):
        return True
    if _oferta_es_comercial(texto):
        return True
    return _sale_es_comercial(texto)


def _filtrar_comercial(categoria: str, articulos: list[dict]) -> list[dict]:
    """Descarta de `articulos` el contenido comercial, con log del recuento."""
    filtradas = [a for a in articulos if not es_contenido_comercial(a)]
    descartadas = len(articulos) - len(filtradas)
    if descartadas:
        logger.info(
            "Filtro de contenido comercial: %d noticia(s) descartada(s) en '%s'.",
            descartadas,
            categoria,
        )
    return filtradas


def _epoch_o_menos_infinito(fecha):
    """Convierte un time.struct_time a epoch; None se manda al final."""
    if fecha is None:
        return float("-inf")
    return calendar.timegm(fecha)


def _seleccionar_con_contraste(articulos: list[dict], n: int) -> list[dict]:
    clusters = agrupar_categoria(articulos)
    seleccionadas = []
    for cluster in clusters[:n]:
        principal, *resto = cluster["articulos"]
        otras_fuentes = sorted({a["fuente"] for a in resto if a["fuente"] != principal["fuente"]})
        noticia = dict(principal)
        noticia["otras_fuentes"] = otras_fuentes
        seleccionadas.append(noticia)
    return seleccionadas


def _seleccionar_por_fecha(articulos: list[dict], n: int) -> list[dict]:
    ordenadas = sorted(
        articulos,
        key=lambda a: _epoch_o_menos_infinito(a.get("fecha")),
        reverse=True,
    )
    seleccionadas = []
    for art in ordenadas[:n]:
        noticia = dict(art)
        noticia.setdefault("otras_fuentes", [])
        seleccionadas.append(noticia)
    return seleccionadas


def seleccionar_noticias(
    pool: Mapping[str, list[dict]], max_por_categoria: int | None = None
) -> dict[str, list[dict]]:
    """Reduce el pool de cada categoría a lo sumo `max_por_categoria` noticias."""
    n = max_por_categoria if max_por_categoria is not None else settings.noticias_por_bloque
    resultado: dict[str, list[dict]] = {}
    for categoria, articulos in pool.items():
        articulos = _filtrar_comercial(categoria, articulos)
        if not articulos:
            resultado[categoria] = []
            continue
        if categoria in CATEGORIAS_CON_CONTRASTE:
            resultado[categoria] = _seleccionar_con_contraste(articulos, n)
        else:
            resultado[categoria] = _seleccionar_por_fecha(articulos, n)
    return resultado


def formatear_noticias_prompt(noticias: list[dict]) -> str:
    """Una línea por noticia, lista para pegar en el prompt del bloque."""
    lineas = []
    for noticia in noticias:
        titular = noticia.get("titular", "")
        fuente = noticia.get("fuente", "")
        otras = noticia.get("otras_fuentes") or []
        sufijo_fuentes = f"; también: {', '.join(otras)}" if otras else ""
        resumen = (noticia.get("resumen") or "")[:300]
        lineas.append(f"- {titular} ({fuente}{sufijo_fuentes}): {resumen}")
    return "\n".join(lineas)


def noticias_a_json(noticias: Mapping[str, list[dict]]) -> dict[str, list[dict]]:
    """Deja solo los campos serializables que necesita `episodio.json`."""
    resultado: dict[str, list[dict]] = {}
    for categoria, lista in noticias.items():
        resultado[categoria] = [
            {
                "titular": n.get("titular", ""),
                "fuente": n.get("fuente", ""),
                "url": n.get("url", ""),
                "otras_fuentes": n.get("otras_fuentes") or [],
            }
            for n in lista
        ]
    return resultado
