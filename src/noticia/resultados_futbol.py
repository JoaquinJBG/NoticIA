"""Resultados de La Liga y Segunda desde openfootball (football.json, CC0).

Contrato: `obtener_resultados` nunca lanza; si la fuente falla devuelve `[]`.
"""

import gzip
import json
import logging
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from noticia.fechas import ZONA

logger = logging.getLogger("noticia.resultados_futbol")

URL_BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"

# (código del fichero, nombre legible), en orden de prioridad para el guion.
COMPETICIONES = (("es.1", "LaLiga"), ("es.2", "Segunda"))

_DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


@dataclass(frozen=True)
class Gol:
    jugador: str
    minuto: str
    equipo: str


@dataclass(frozen=True)
class Partido:
    competicion: str
    prioridad: int
    inicio: datetime
    local: str
    visitante: str
    goles_local: int
    goles_visitante: int
    goles: tuple[Gol, ...]


def _temporada(fecha: date) -> str:
    inicio = fecha.year if fecha.month >= 7 else fecha.year - 1
    return f"{inicio}-{(inicio + 1) % 100:02d}"


def _descargar(url: str, timeout: float) -> bytes:
    peticion = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        datos = respuesta.read()
    if datos[:2] == b"\x1f\x8b":
        datos = gzip.decompress(datos)
    return datos


def _resultado_final(score) -> tuple[int, int] | None:
    ft = score.get("ft") if isinstance(score, dict) else score
    if not isinstance(ft, list) or len(ft) != 2:
        return None
    if not all(isinstance(g, int) and not isinstance(g, bool) for g in ft):
        return None
    return ft[0], ft[1]


def _inicio(texto_fecha: str, texto_hora: str | None) -> datetime:
    hora = time.fromisoformat(texto_hora) if texto_hora else time(0, 0)
    return datetime.combine(date.fromisoformat(texto_fecha), hora, tzinfo=ZONA)


def _parsear_partido(crudo: dict, competicion: str, prioridad: int) -> Partido | None:
    resultado = _resultado_final(crudo.get("score"))
    if resultado is None:
        return None
    return Partido(
        competicion=competicion,
        prioridad=prioridad,
        inicio=_inicio(crudo["date"], crudo.get("time")),
        local=crudo["team1"],
        visitante=crudo["team2"],
        goles_local=resultado[0],
        goles_visitante=resultado[1],
        goles=(),
    )


def _partidos_de_competicion(
    codigo: str, competicion: str, prioridad: int, fecha: date, dias: int, timeout: float
) -> list[Partido]:
    url = f"{URL_BASE}/{_temporada(fecha)}/{codigo}.json"
    try:
        crudo = _descargar(url, timeout)
        partidos_crudos = json.loads(crudo)["matches"]
    except Exception as exc:
        logger.warning("sin resultados de %s (%s): %s", competicion, url, exc)
        return []

    desde, hasta = fecha - timedelta(days=dias), fecha - timedelta(days=1)
    partidos = []
    for partido_crudo in partidos_crudos:
        try:
            partido = _parsear_partido(partido_crudo, competicion, prioridad)
        except Exception as exc:
            logger.warning("partido ignorado en %s: %s", competicion, exc)
            continue
        if partido is not None and desde <= partido.inicio.date() <= hasta:
            partidos.append(partido)
    return partidos


def obtener_resultados(fecha: date, dias: int = 3, timeout: float = 10) -> list[Partido]:
    """Partidos terminados de `fecha-dias` a `fecha-1`. Nunca lanza."""
    try:
        vistos = set()
        partidos = []
        for prioridad, (codigo, competicion) in enumerate(COMPETICIONES):
            for partido in _partidos_de_competicion(
                codigo, competicion, prioridad, fecha, dias, timeout
            ):
                clave = (
                    partido.competicion,
                    partido.inicio.date(),
                    partido.local,
                    partido.visitante,
                )
                if clave not in vistos:
                    vistos.add(clave)
                    partidos.append(partido)
        return partidos
    except Exception as exc:
        logger.warning("resultados de fútbol no disponibles: %s", exc)
        return []


def _linea(partido: Partido) -> str:
    dia = partido.inicio.date()
    linea = (
        f"{partido.competicion} ({_DIAS[dia.weekday()]} {dia.day}): "
        f"{partido.local} {partido.goles_local}-{partido.goles_visitante} {partido.visitante}"
    )
    if partido.goles:
        goles = ", ".join(f"{g.jugador} {g.minuto}" for g in partido.goles)
        linea += f" — goles: {goles}"
    return linea


def formatear_resultados_prompt(partidos: list[Partido], maximo: int = 25) -> str:
    """Una línea por partido: por prioridad de competición y, dentro, el más reciente primero."""
    ordenados = sorted(partidos, key=lambda p: (p.prioridad, -p.inicio.timestamp()))
    return "\n".join(_linea(p) for p in ordenados[:maximo])


def resultados_a_json(partidos: list[Partido]) -> list[dict]:
    return [
        {
            "competicion": p.competicion,
            "inicio": p.inicio.isoformat(),
            "local": p.local,
            "visitante": p.visitante,
            "goles_local": p.goles_local,
            "goles_visitante": p.goles_visitante,
            "goles": [
                {"jugador": g.jugador, "minuto": g.minuto, "equipo": g.equipo} for g in p.goles
            ],
        }
        for p in partidos
    ]
