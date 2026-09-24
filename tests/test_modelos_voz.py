"""Tests de la descarga y verificación de los modelos de Kokoro."""

import hashlib
import io
from urllib.error import URLError

import pytest

from noticia.voz import modelos as modulo_modelos
from noticia.voz.modelos import (
    FICHEROS_KOKORO,
    FicheroModelo,
    asegurar_modelos_kokoro,
    descargar_fichero,
    main,
    modelos_kokoro_presentes,
    rutas_kokoro,
)


def _fichero_falso(contenido: bytes) -> FicheroModelo:
    return FicheroModelo(
        nombre="fichero.bin",
        url="https://ejemplo.invalido/fichero.bin",
        sha256=hashlib.sha256(contenido).hexdigest(),
    )


def test_ficheros_kokoro_tiene_los_dos_pesos():
    nombres = {f.nombre for f in FICHEROS_KOKORO}
    assert nombres == {"kokoro-v1.0.onnx", "voices-v1.0.bin"}


def test_rutas_kokoro_devuelve_onnx_y_voices(tmp_path):
    onnx, voices = rutas_kokoro(tmp_path)
    assert onnx.name == "kokoro-v1.0.onnx"
    assert voices.name == "voices-v1.0.bin"
    assert onnx.parent == tmp_path


def test_modelos_kokoro_presentes_falso_si_faltan(tmp_path):
    assert modelos_kokoro_presentes(tmp_path) is False


def test_descargar_fichero_verifica_hash_y_escribe(tmp_path, monkeypatch):
    contenido = b"contenido de prueba"
    fichero = _fichero_falso(contenido)
    destino = tmp_path / fichero.nombre

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: io.BytesIO(contenido))

    ruta = descargar_fichero(fichero, destino)

    assert ruta == destino
    assert destino.read_bytes() == contenido
    assert not destino.with_suffix(".part").exists()


def test_descargar_fichero_hash_incorrecto_lanza_y_no_deja_fichero(tmp_path, monkeypatch):
    fichero = _fichero_falso(b"esperado")
    destino = tmp_path / fichero.nombre

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: io.BytesIO(b"otro contenido"))

    with pytest.raises(ValueError):
        descargar_fichero(fichero, destino)

    assert not destino.exists()
    assert not destino.with_suffix(".part").exists()


def test_asegurar_modelos_kokoro_no_descarga_si_ya_existen(tmp_path, monkeypatch):
    onnx, voices = rutas_kokoro(tmp_path)
    onnx.write_bytes(b"onnx")
    voices.write_bytes(b"voices")

    # No nos importa el contenido real: simulamos que el hash siempre coincide
    # con el esperado para ese nombre de fichero.
    hashes_esperados = {f.nombre: f.sha256 for f in FICHEROS_KOKORO}
    monkeypatch.setattr("noticia.voz.modelos._sha256_de", lambda ruta: hashes_esperados[ruta.name])

    llamadas = []
    monkeypatch.setattr(
        "noticia.voz.modelos.descargar_fichero",
        lambda *a, **k: llamadas.append(a) or a[1],
    )

    resultado = asegurar_modelos_kokoro(tmp_path)

    assert llamadas == []
    assert resultado == [onnx, voices]


def test_descargar_fichero_error_de_red_no_deja_parcial(tmp_path, monkeypatch):
    fichero = _fichero_falso(b"x")
    destino = tmp_path / fichero.nombre

    def _urlopen_falla(*_a, **_k):
        raise URLError("sin conexión")

    monkeypatch.setattr("urllib.request.urlopen", _urlopen_falla)

    with pytest.raises(URLError):
        descargar_fichero(fichero, destino)

    assert not destino.with_suffix(".part").exists()


# --------------------------------------------------------------- main()


def test_main_configura_el_logging_antes_de_descargar(monkeypatch):
    llamadas = []
    monkeypatch.setattr(modulo_modelos, "configurar_logging", lambda: llamadas.append("log"))
    monkeypatch.setattr(modulo_modelos, "asegurar_modelos_kokoro", lambda: llamadas.append("ok"))

    assert main() == 0
    assert llamadas == ["log", "ok"]


def test_main_devuelve_1_si_falla_la_descarga(monkeypatch):
    monkeypatch.setattr(modulo_modelos, "configurar_logging", lambda: None)

    def _falla():
        raise RuntimeError("sin red")

    monkeypatch.setattr(modulo_modelos, "asegurar_modelos_kokoro", _falla)

    assert main() == 1
