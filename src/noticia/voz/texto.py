"""Limpieza y troceo de texto para enviarlo a un motor de locución."""

import re
import unicodedata

_RE_ACOTACION_PARENTESIS = re.compile(r"\([^)]*\)")
_RE_ACOTACION_CORCHETE = re.compile(r"\[[^\]]*\]")
_RE_URL = re.compile(r"https?://\S+")
_RE_MARKDOWN = re.compile(r"[*_#`]")
_RE_ESPACIOS = re.compile(r"\s+")

_RE_FIN_FRASE = re.compile(r"(?<=[.!?…;])\s+")
_RE_FIN_COMA = re.compile(r"(?<=,)\s+")

# Diccionario de pronunciación para el motor de voz: palabras que un TTS lee
# mal (p.ej. edge-tts lee "podcast" como "padcat"). Solo afecta al audio: no
# se aplica al guion.md ni a las notas del feed. Ampliable desde
# `Settings.pronunciacion_extra` (ver `noticia.config`).
PRONUNCIACION: dict[str, str] = {
    "podcast": "pódcast",
    "podcasts": "pódcasts",
}


def _diccionario_pronunciacion() -> dict[str, str]:
    from noticia.config import settings

    diccionario = {clave.lower(): valor for clave, valor in PRONUNCIACION.items()}
    diccionario.update(
        {clave.lower(): valor for clave, valor in settings.pronunciacion_extra.items()}
    )
    return diccionario


def _con_mayuscula_inicial_de(original: str, reemplazo: str) -> str:
    if original[:1].isupper():
        return reemplazo[:1].upper() + reemplazo[1:]
    return reemplazo


def aplicar_pronunciacion(texto: str, diccionario: dict[str, str] | None = None) -> str:
    """Sustituye, palabra completa y sin distinguir mayúsculas, cada entrada del
    diccionario de pronunciación por su grafía fonética (conservando la mayúscula
    inicial de la palabra original). Por defecto usa `PRONUNCIACION` + la
    ampliación de `settings.pronunciacion_extra`.
    """
    dic = diccionario if diccionario is not None else _diccionario_pronunciacion()
    if not dic:
        return texto

    patron = re.compile(
        r"\b("
        + "|".join(re.escape(palabra) for palabra in sorted(dic, key=len, reverse=True))
        + r")\b",
        re.IGNORECASE,
    )

    def _sustituir(coincidencia: re.Match) -> str:
        original = coincidencia.group(0)
        return _con_mayuscula_inicial_de(original, dic[original.lower()])

    return patron.sub(_sustituir, texto)


def limpiar_texto_locucion(texto: str) -> str:
    """Deja el texto listo para locutarlo: sin acotaciones, URL, emojis ni markdown.

    Aplica también el diccionario de pronunciación (`aplicar_pronunciacion`): es
    el único punto por el que pasa el texto de todos los motores de voz antes
    de sintetizarlo.
    """
    texto = _RE_ACOTACION_PARENTESIS.sub(" ", texto)
    texto = _RE_ACOTACION_CORCHETE.sub(" ", texto)
    texto = _RE_URL.sub(" ", texto)
    texto = "".join(
        caracter for caracter in texto if unicodedata.category(caracter) not in ("So", "Cs")
    )
    texto = _RE_MARKDOWN.sub("", texto)
    texto = _RE_ESPACIOS.sub(" ", texto).strip()
    return aplicar_pronunciacion(texto)


def trocear_frases(texto: str, max_caracteres: int = 280) -> list[str]:
    """Trocea `texto` en fragmentos de como mucho `max_caracteres`.

    Corta preferentemente tras `. ! ? … ;`, conservando la puntuación, y junta
    frases cortas hasta acercarse al máximo. Una frase más larga que el máximo
    se parte por comas y, si no basta, por espacios. Ningún fragmento supera
    el máximo ni sale vacío.
    """
    texto = texto.strip()
    if not texto:
        return []
    if len(texto) <= max_caracteres:
        return [texto]

    frases = _RE_FIN_FRASE.split(texto)
    return _acumular(frases, max_caracteres, _partir_larga)


def _acumular(fragmentos: list[str], max_caracteres: int, partir_largo) -> list[str]:
    trozos: list[str] = []
    actual = ""
    for fragmento in fragmentos:
        fragmento = fragmento.strip()
        if not fragmento:
            continue
        if len(fragmento) > max_caracteres:
            if actual:
                trozos.append(actual)
                actual = ""
            trozos.extend(partir_largo(fragmento, max_caracteres))
            continue
        candidato = f"{actual} {fragmento}".strip() if actual else fragmento
        if len(candidato) <= max_caracteres:
            actual = candidato
        else:
            if actual:
                trozos.append(actual)
            actual = fragmento
    if actual:
        trozos.append(actual)
    return trozos


def _partir_larga(fragmento: str, max_caracteres: int) -> list[str]:
    partes = _RE_FIN_COMA.split(fragmento)
    if len(partes) == 1:
        return _partir_por_espacios(fragmento, max_caracteres)
    return _acumular(partes, max_caracteres, _partir_por_espacios)


def _partir_por_espacios(fragmento: str, max_caracteres: int) -> list[str]:
    trozos: list[str] = []
    actual = ""
    for palabra in fragmento.split():
        candidato = f"{actual} {palabra}".strip() if actual else palabra
        if len(candidato) <= max_caracteres:
            actual = candidato
            continue
        if actual:
            trozos.append(actual)
            actual = ""
        if len(palabra) > max_caracteres:
            for inicio in range(0, len(palabra), max_caracteres):
                trozos.append(palabra[inicio : inicio + max_caracteres])
        else:
            actual = palabra
    if actual:
        trozos.append(actual)
    return trozos
