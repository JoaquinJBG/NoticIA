"""Selección de las noticias que entran en el guion de cada bloque.

Reduce el pool de la ingesta a las N noticias más relevantes por categoría:
en las categorías de contraste, una por cluster (la más contrastada primero);
en el resto, las más recientes.
"""

import calendar
import logging
from collections.abc import Mapping

from noticia.agrupador import agrupar_categoria
from noticia.config import settings
from noticia.fuentes import CATEGORIAS_CON_CONTRASTE

logger = logging.getLogger("noticia.seleccion")


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
