import re
import unicodedata

from rapidfuzz import fuzz

from noticia.fuentes import CATEGORIAS_CON_CONTRASTE

_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "y",
    "o", "a", "en", "que", "por", "con", "para", "su", "sus", "al", "se",
    "lo", "es", "the",
}
_NO_ALFANUM = re.compile(r"[^a-z0-9\s]")


def _normalizar(texto):
    """minúsculas, sin acentos, sin puntuación, sin stopwords ni palabras de 1 letra."""
    texto = texto.lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    texto = _NO_ALFANUM.sub(" ", texto)
    palabras = [p for p in texto.split() if p not in _STOPWORDS and len(p) > 1]
    return " ".join(palabras)


def agrupar_categoria(articulos, umbral=70):
    """Agrupa artículos por similitud léxica de titulares.

    Devuelve [{"tema": str, "articulos": [...]}], priorizando los clusters
    con más fuentes distintas (más contrastables).
    """
    clusters = []
    for art in articulos:
        norm = _normalizar(art["titular"])
        destino = None
        for cluster in clusters:
            if fuzz.token_set_ratio(norm, cluster["_norm"]) >= umbral:
                destino = cluster
                break
        if destino is not None:
            destino["articulos"].append(art)
        else:
            clusters.append({"tema": art["titular"], "_norm": norm, "articulos": [art]})

    for cluster in clusters:
        del cluster["_norm"]

    clusters.sort(
        key=lambda c: len({a["fuente"] for a in c["articulos"]}),
        reverse=True,
    )
    return clusters


def agrupar(pool):
    """Aplica clustering a las categorías de contraste; deja el resto plano."""
    resultado = {}
    for categoria, articulos in pool.items():
        if categoria in CATEGORIAS_CON_CONTRASTE:
            resultado[categoria] = {"clusters": agrupar_categoria(articulos)}
        else:
            resultado[categoria] = articulos
    return resultado
