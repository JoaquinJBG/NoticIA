import re
import unicodedata

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
