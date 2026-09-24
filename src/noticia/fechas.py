"""Fechas y horas en la zona de Madrid, sin depender del locale del sistema."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("Europe/Madrid")

_DIAS_SEMANA = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}

_MESES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def hoy_madrid() -> date:
    return datetime.now(ZONA).date()


def ahora_madrid() -> datetime:
    return datetime.now(ZONA)


def formatear_fecha_larga(fecha: date) -> str:
    dia_semana = _DIAS_SEMANA[fecha.weekday()]
    mes = _MESES[fecha.month]
    return f"{dia_semana} {fecha.day} de {mes} de {fecha.year}"


def parsear_fecha(texto: str) -> date:
    return datetime.strptime(texto, "%Y-%m-%d").date()
