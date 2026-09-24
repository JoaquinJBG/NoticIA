"""Tests del selector de cadena de motores de voz y de las muestras de audio."""

import asyncio
import logging
from pathlib import Path

import pytest

from noticia.voz.base import LOCUTORES, MotorNoDisponible
from noticia.voz.gpu import InfoGPU


class _MotorFalso:
    """Motor de voz falso e inyectable en `MOTORES`, controlable por test."""

    def __init__(
        self,
        nombre: str,
        disponible: bool = True,
        motivo: str = "",
        falla_al_cargar: bool = False,
    ) -> None:
        self.nombre = nombre
        self.extension = "wav"
        self.concurrencia_maxima = 1
        self._disponible = disponible
        self._motivo = motivo
        self._falla_al_cargar = falla_al_cargar
        self.cargado = False
        self.cerrado = False
        self.sintetizados: list[tuple[str, str]] = []

    def disponible(self) -> tuple[bool, str]:
        return self._disponible, self._motivo

    async def cargar(self) -> None:
        if self._falla_al_cargar:
            raise MotorNoDisponible(f"{self.nombre} no carga")
        self.cargado = True

    async def sintetizar(self, texto, locutor, ruta):
        self.sintetizados.append((texto, locutor))
        ruta.write_text(f"{self.nombre}:{locutor}:{texto}", encoding="utf-8")
        return ruta

    async def cerrar(self) -> None:
        self.cerrado = True


def _gpu(disponible: bool) -> InfoGPU:
    return InfoGPU(disponible=disponible)


@pytest.fixture
def registro_motores(monkeypatch):
    """Registro de fábricas falsas, sustituyendo `selector.MOTORES`."""
    from noticia.voz import selector

    registro: dict[str, _MotorFalso] = {}

    def _fabrica(nombre, **kwargs):
        def _crear():
            motor = _MotorFalso(nombre, **kwargs)
            registro[nombre] = motor
            return motor

        return _crear

    fabricas = {
        "edge": _fabrica("edge"),
        "kokoro": _fabrica("kokoro"),
        "chatterbox": _fabrica("chatterbox"),
    }
    monkeypatch.setattr(selector, "MOTORES", fabricas)
    return registro


# --------------------------------------------------------------- orden_preferido


@pytest.mark.parametrize(
    "preferencia,con_gpu,esperado",
    [
        ("auto", True, ["chatterbox", "kokoro", "edge"]),
        ("auto", False, ["kokoro", "edge"]),
        ("chatterbox", False, ["chatterbox", "kokoro", "edge"]),
        ("chatterbox", True, ["chatterbox", "kokoro", "edge"]),
        ("kokoro", True, ["kokoro", "edge"]),
        ("edge", True, ["edge"]),
    ],
)
def test_orden_preferido(preferencia, con_gpu, esperado):
    from noticia.voz.selector import orden_preferido

    assert orden_preferido(preferencia, _gpu(con_gpu)) == esperado


def test_orden_preferido_invalido_lanza():
    from noticia.voz.selector import orden_preferido

    with pytest.raises(ValueError):
        orden_preferido("inventado", _gpu(False))


# --------------------------------------------------------------- resolver_motores


def test_resolver_motores_auto_con_gpu_da_los_tres(registro_motores):
    from noticia.voz.selector import resolver_motores

    cadena = resolver_motores("auto", _gpu(True))

    assert [m.nombre for m in cadena] == ["chatterbox", "kokoro", "edge"]


def test_resolver_motores_auto_sin_gpu_da_kokoro_y_edge(registro_motores):
    from noticia.voz.selector import resolver_motores

    cadena = resolver_motores("auto", _gpu(False))

    assert [m.nombre for m in cadena] == ["kokoro", "edge"]


def test_resolver_motores_descarta_no_disponibles_y_loguea(registro_motores, caplog):
    from noticia.voz import selector

    selector.MOTORES["kokoro"] = lambda: _MotorFalso(
        "kokoro", disponible=False, motivo="faltan los pesos"
    )

    with caplog.at_level(logging.INFO):
        cadena = selector.resolver_motores("auto", _gpu(True))

    nombres = [m.nombre for m in cadena]
    assert "kokoro" not in nombres
    assert "chatterbox" in nombres
    assert "edge" in nombres
    assert any("faltan los pesos" in registro.message for registro in caplog.records)


def test_resolver_motores_preferencia_explicita_no_disponible_loguea_warning(
    registro_motores, caplog
):
    from noticia.voz import selector

    selector.MOTORES["kokoro"] = lambda: _MotorFalso(
        "kokoro", disponible=False, motivo="faltan los pesos"
    )

    with caplog.at_level(logging.INFO):
        cadena = selector.resolver_motores("kokoro", _gpu(False))

    assert [m.nombre for m in cadena] == ["edge"]
    registros_kokoro = [r for r in caplog.records if "faltan los pesos" in r.message]
    assert len(registros_kokoro) == 1
    assert registros_kokoro[0].levelname == "WARNING"


def test_resolver_motores_sin_edge_disponible_lanza(registro_motores):
    from noticia.voz import selector

    for nombre in ("edge", "kokoro", "chatterbox"):
        selector.MOTORES[nombre] = lambda nombre=nombre: _MotorFalso(nombre, disponible=False)

    with pytest.raises(MotorNoDisponible):
        selector.resolver_motores("auto", _gpu(True))


def test_resolver_motores_preferencia_por_defecto_usa_settings(registro_motores, monkeypatch):
    from noticia.config import settings
    from noticia.voz.selector import resolver_motores

    monkeypatch.setattr(settings, "motor_voz", "edge")
    monkeypatch.setattr("noticia.voz.selector.detectar_gpu", lambda: _gpu(False))

    cadena = resolver_motores()

    assert [m.nombre for m in cadena] == ["edge"]


# --------------------------------------------------------------- preparar_cadena


def test_preparar_cadena_carga_el_primero(registro_motores):
    from noticia.voz.selector import preparar_cadena, resolver_motores

    cadena = resolver_motores("auto", _gpu(True))

    resultado = asyncio.run(preparar_cadena(cadena))

    assert resultado[0].nombre == "chatterbox"
    assert resultado[0].cargado is True


def test_preparar_cadena_descarta_el_primero_si_falla_la_carga(registro_motores):
    from noticia.voz import selector

    selector.MOTORES["chatterbox"] = lambda: _MotorFalso("chatterbox", falla_al_cargar=True)
    cadena = selector.resolver_motores("auto", _gpu(True))

    resultado = asyncio.run(selector.preparar_cadena(cadena))

    assert [m.nombre for m in resultado] == ["kokoro", "edge"]
    assert resultado[0].cargado is True


# --------------------------------------------------------------- generar_muestras


def test_generar_muestras_crea_un_fichero_por_motor_y_locutor(registro_motores, tmp_path):
    from noticia.voz.muestras import generar_muestras

    rutas = asyncio.run(generar_muestras(tmp_path, nombres=("edge", "kokoro")))

    assert len(rutas) == len(LOCUTORES) * 2
    for ruta in rutas:
        assert ruta.exists()
    nombres_fichero = {ruta.name for ruta in rutas}
    for locutor in LOCUTORES:
        assert f"edge_{locutor}.wav" in nombres_fichero
        assert f"kokoro_{locutor}.wav" in nombres_fichero


def test_generar_muestras_omite_motor_no_disponible(registro_motores, tmp_path, caplog):
    from noticia.voz import selector
    from noticia.voz.muestras import generar_muestras

    selector.MOTORES["chatterbox"] = lambda: _MotorFalso(
        "chatterbox", disponible=False, motivo="sin GPU"
    )

    with caplog.at_level(logging.INFO):
        rutas = asyncio.run(generar_muestras(tmp_path, nombres=("edge", "chatterbox")))

    assert len(rutas) == len(LOCUTORES)
    assert any("sin GPU" in registro.message for registro in caplog.records)


def test_muestras_main_configura_logging_y_dice_donde_deja_los_ficheros(
    tmp_path, monkeypatch, caplog
):
    import noticia.config as config
    from noticia.voz import muestras

    llamadas = []
    monkeypatch.setattr(muestras, "configurar_logging", lambda: llamadas.append("log"))
    monkeypatch.setattr(config.settings, "carpeta_output", str(tmp_path))

    async def _fake_generar_muestras(carpeta, nombres=("edge", "kokoro", "chatterbox")):
        return [Path(carpeta) / "edge_alex.wav"]

    monkeypatch.setattr(muestras, "generar_muestras", _fake_generar_muestras)

    with caplog.at_level(logging.INFO):
        codigo = muestras.main()

    assert codigo == 0
    assert llamadas == ["log"]
    carpeta_esperada = str(tmp_path / "muestras")
    assert any(carpeta_esperada in registro.message for registro in caplog.records)


def test_muestras_main_devuelve_1_si_no_hay_ninguna_muestra(tmp_path, monkeypatch):
    import noticia.config as config
    from noticia.voz import muestras

    monkeypatch.setattr(muestras, "configurar_logging", lambda: None)
    monkeypatch.setattr(config.settings, "carpeta_output", str(tmp_path))

    async def _sin_muestras(carpeta, nombres=("edge", "kokoro", "chatterbox")):
        return []

    monkeypatch.setattr(muestras, "generar_muestras", _sin_muestras)

    assert muestras.main() == 1
