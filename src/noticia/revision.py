"""Control de neutralidad del guion: avisa de patrones, nunca bloquea (D-03).

Los patrones salen del texto aprobado de D-02: las posturas se atribuyen a quien
las sostiene, sin adjetivos valorativos sobre actores políticos, sin veredictos
sobre hechos en disputa, y un hecho comprobado se presenta con su fuente. La
regla anticomercial ya aprobada se comprueba con el filtro de `seleccion`.
"""

import logging
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field

from noticia.seleccion import es_contenido_comercial

logger = logging.getLogger("noticia.revision")

VEREDICTO = "veredicto"
ATRIBUCION_SIN_FUENTE = "atribucion_sin_fuente"
ADJETIVO_VALORATIVO = "adjetivo_valorativo"
PROMOCION = "promocion"

_ENCABEZADO = re.compile(r"^##\s+(\w+)\s*$")
_FRASES = re.compile(r"(?<=[.!?…])\s+")
_ENTRECOMILLADO = re.compile(r'"[^"]*"|“[^”]*”|«[^»]*»')

_VEREDICTOS = (
    re.compile(r"\bla realidad\b[^.!?]{0,80}\b(?:apunta|indica|sugiere|es que)\b", re.I),
    re.compile(
        r"\b(?:le viene genial|sirve(?:n)? más para|para legitimarse|"
        r"(?:para )?consolidar (?:el )?poder)\b",
        re.I,
    ),
)
_SIN_SEGUN = re.compile(r"\bseg[uú]n\b", re.I)
_ATRIBUCION_VAGA = re.compile(
    r"\b(?:hay|varios|algunos|ciertos|numerosos|muchos|diversos)\s+"
    r"(?:an[aá]lisis|analistas|medios|expertos|estudios|informes|fuentes|especialistas)\b",
    re.I,
)
# Afinidad política atribuida a un medio: sin fuente aunque la frase diga "según".
_AFINIDAD = re.compile(r"\bmás cercanos?\s+(?:al|a la|a los|a las|a)\s+[A-ZÁÉÍÓÚÑ]")
_ACTOR_POLITICO = re.compile(
    r"\b(?:PP|PSOE|Vox|Sumar|Podemos|Gobierno|Ejecutivo|oposición|Ayuso|Sánchez|"
    r"Feijóo|Abascal|Trump|Putin|Netanyahu|Maduro|Milei|Biden|Zelenski)\b"
)
_ADJETIVO = re.compile(
    r"\b(?:corrupt[oa]s?|mentirosos?|irresponsables?|incompetentes?|vergonzos[oa]s?|"
    r"indecentes?|impresentables?|golpistas?|fascistas?|extremistas?|demagog\w+|"
    r"hip[oó]critas?|c[ií]nic[oa]s?|tramposos?)\b",
    re.I,
)


@dataclass
class Hallazgo:
    tipo: str
    bloque: str
    linea: int
    fragmento: str


@dataclass
class ResultadoRevision:
    hallazgos: list[Hallazgo] = field(default_factory=list)
    fuentes_por_bloque: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def limpio(self) -> bool:
        return not self.hallazgos

    def a_dict(self) -> dict:
        return {
            "limpio": self.limpio,
            "hallazgos": [asdict(h) for h in self.hallazgos],
            "fuentes_por_bloque": self.fuentes_por_bloque,
        }


def _bloques(guion: Mapping[str, str] | str) -> dict[str, str]:
    if not isinstance(guion, str):
        return dict(guion)
    bloques: dict[str, list[str]] = {}
    actual = "guion"
    for linea in guion.splitlines():
        encabezado = _ENCABEZADO.match(linea)
        if encabezado:
            actual = encabezado.group(1)
            bloques.setdefault(actual, [])
        else:
            bloques.setdefault(actual, []).append(linea)
    return {bloque: "\n".join(lineas) for bloque, lineas in bloques.items()}


def _tipos_de_frase(frase: str) -> list[str]:
    tipos = []
    if any(p.search(frase) for p in _VEREDICTOS):
        tipos.append(VEREDICTO)
    if _AFINIDAD.search(frase) or (_ATRIBUCION_VAGA.search(frase) and not _SIN_SEGUN.search(frase)):
        tipos.append(ATRIBUCION_SIN_FUENTE)
    # Lo entrecomillado es una postura atribuida: se permite.
    propio = _ENTRECOMILLADO.sub(" ", frase)
    if _ACTOR_POLITICO.search(propio) and _ADJETIVO.search(propio):
        tipos.append(ADJETIVO_VALORATIVO)
    if es_contenido_comercial({"titular": frase}):
        tipos.append(PROMOCION)
    return tipos


def _fuentes_por_bloque(noticias: Mapping[str, list[dict]]) -> dict[str, dict[str, int]]:
    resultado: dict[str, dict[str, int]] = {}
    for bloque, lista in noticias.items():
        cuenta: Counter[str] = Counter()
        for noticia in lista:
            fuentes = {noticia.get("fuente") or "", *(noticia.get("otras_fuentes") or [])}
            cuenta.update(f for f in fuentes if f)
        resultado[bloque] = dict(cuenta.most_common())
    return resultado


def revisar_guion(
    guion: Mapping[str, str] | str, noticias: Mapping[str, list[dict]]
) -> ResultadoRevision:
    """Marca patrones de falta de neutralidad en `guion` (bloque -> texto, o Markdown).

    `linea` es la línea dentro del bloque (1-based). El recuento por bloque cuenta
    cada fuente una vez por noticia, sea la principal o una de `otras_fuentes`.
    """
    hallazgos: list[Hallazgo] = []
    for bloque, texto in _bloques(guion).items():
        for numero, linea in enumerate(texto.splitlines(), start=1):
            for frase in _FRASES.split(linea):
                frase = frase.strip()
                hallazgos.extend(
                    Hallazgo(tipo, bloque, numero, frase) for tipo in _tipos_de_frase(frase)
                )
    resultado = ResultadoRevision(hallazgos, _fuentes_por_bloque(noticias))
    for h in hallazgos:
        logger.warning("Revisión [%s] %s:%d: %s", h.tipo, h.bloque, h.linea, h.fragmento)
    return resultado


__all__ = [
    "ADJETIVO_VALORATIVO",
    "ATRIBUCION_SIN_FUENTE",
    "PROMOCION",
    "VEREDICTO",
    "Hallazgo",
    "ResultadoRevision",
    "revisar_guion",
]
