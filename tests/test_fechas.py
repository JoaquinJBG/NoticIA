from datetime import date, datetime

import pytest

from noticia import fechas


def test_hoy_madrid_coincide_con_zona_madrid():
    assert fechas.hoy_madrid() == datetime.now(fechas.ZONA).date()


def test_ahora_madrid_tiene_zona_madrid():
    ahora = fechas.ahora_madrid()
    assert ahora.tzinfo is not None
    assert ahora.utcoffset() == datetime.now(fechas.ZONA).utcoffset()


@pytest.mark.parametrize(
    ("fecha", "esperado"),
    [
        (date(2026, 9, 21), "lunes 21 de septiembre de 2026"),
        (date(2026, 9, 22), "martes 22 de septiembre de 2026"),
        (date(2026, 9, 23), "miércoles 23 de septiembre de 2026"),
        (date(2026, 9, 24), "jueves 24 de septiembre de 2026"),
        (date(2026, 9, 25), "viernes 25 de septiembre de 2026"),
        (date(2026, 9, 26), "sábado 26 de septiembre de 2026"),
        (date(2026, 9, 27), "domingo 27 de septiembre de 2026"),
    ],
)
def test_formatear_fecha_larga_dias(fecha, esperado):
    assert fechas.formatear_fecha_larga(fecha) == esperado


@pytest.mark.parametrize(
    ("mes", "nombre_mes"),
    [
        (1, "enero"),
        (2, "febrero"),
        (3, "marzo"),
        (4, "abril"),
        (5, "mayo"),
        (6, "junio"),
        (7, "julio"),
        (8, "agosto"),
        (9, "septiembre"),
        (10, "octubre"),
        (11, "noviembre"),
        (12, "diciembre"),
    ],
)
def test_formatear_fecha_larga_meses(mes, nombre_mes):
    resultado = fechas.formatear_fecha_larga(date(2026, mes, 1))
    assert nombre_mes in resultado


def test_parsear_fecha_valida():
    assert fechas.parsear_fecha("2026-09-24") == date(2026, 9, 24)


def test_parsear_fecha_invalida_lanza_value_error():
    with pytest.raises(ValueError):
        fechas.parsear_fecha("24-09-2026")
