import re
import unicodedata

_STOPWORDS = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "de",
    "del",
    "y",
    "o",
    "a",
    "en",
    "que",
    "por",
    "con",
    "para",
    "su",
    "sus",
    "al",
    "se",
    "lo",
    "es",
    "the",
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


_MIN_TOKENS_COMPARTIDOS = 2


def _tokens(norm):
    return frozenset(norm.split())


def _similitud(a, b):
    """Dice sobre tokens (0-100); 0 si comparten menos de _MIN_TOKENS_COMPARTIDOS.

    A diferencia de un ratio de subconjunto, un titular de una palabra no se
    funde con otro largo que la contiene.
    """
    comunes = len(a & b)
    if comunes < _MIN_TOKENS_COMPARTIDOS:
        return 0.0
    return 200 * comunes / (len(a) + len(b))


def _elegir_principal(articulos, tokens):
    """Titular con mayor similitud media con el resto; empate: fuente y titular alfabéticos.

    No depende del orden de entrada ni pondera medios.
    """
    if len(articulos) == 1:
        return articulos[0]

    def clave(i):
        otros = [_similitud(tokens[i], tokens[j]) for j in range(len(articulos)) if j != i]
        return (-sum(otros) / len(otros), articulos[i]["fuente"], articulos[i]["titular"])

    return articulos[min(range(len(articulos)), key=clave)]


def agrupar_categoria(articulos, umbral=50):
    """Agrupa artículos por similitud léxica de titulares (Dice sobre tokens, 0-100).

    Devuelve [{"tema": str, "articulos": [...]}], priorizando los clusters
    con más fuentes distintas (más contrastables). El principal de cada
    cluster va el primero y da el `tema`.
    """
    clusters = []
    for art in articulos:
        tokens = _tokens(_normalizar(art["titular"]))
        destino = None
        for cluster in clusters:
            if _similitud(tokens, cluster["_fundador"]) >= umbral:
                destino = cluster
                break
        if destino is not None:
            destino["articulos"].append(art)
            destino["_tokens"].append(tokens)
        else:
            clusters.append({"_fundador": tokens, "_tokens": [tokens], "articulos": [art]})

    for cluster in clusters:
        principal = _elegir_principal(cluster["articulos"], cluster["_tokens"])
        cluster["articulos"] = [principal] + [a for a in cluster["articulos"] if a is not principal]
        cluster["tema"] = principal["titular"]
        del cluster["_fundador"], cluster["_tokens"]

    clusters.sort(
        key=lambda c: len({a["fuente"] for a in c["articulos"]}),
        reverse=True,
    )
    return clusters
