"""Tests del detector de GPU NVIDIA."""

import subprocess
from dataclasses import FrozenInstanceError

import pytest

from noticia.voz.gpu import InfoGPU, buscar_nvidia_smi, detectar_gpu


@pytest.fixture(autouse=True)
def _limpiar_cache():
    detectar_gpu.cache_clear()
    yield
    detectar_gpu.cache_clear()


def test_sin_nvidia_smi_da_no_disponible(monkeypatch):
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr("os.access", lambda *_a, **_k: False)
    monkeypatch.setattr("importlib.util.find_spec", lambda _: None)

    info = detectar_gpu()

    assert info.disponible is False
    assert info.motivo


def test_salida_de_nvidia_smi_se_parsea(monkeypatch):
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/nvidia-smi")
    monkeypatch.setattr("importlib.util.find_spec", lambda _: None)

    def _run_falso(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="NVIDIA GeForce RTX 3060, 12288, 576.02\n",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", _run_falso)

    info = detectar_gpu(comprobar_torch=False)

    assert info.disponible is True
    assert info.nombre == "NVIDIA GeForce RTX 3060"
    assert info.vram_mib == 12288
    assert info.driver == "576.02"


def test_cuda_visible_devices_vacio_desactiva_gpu(monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")

    info = detectar_gpu()

    assert info.disponible is False
    assert "CUDA_VISIBLE_DEVICES" in info.motivo


def test_nvidia_smi_que_lanza_excepcion_da_no_disponible(monkeypatch, caplog):
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/nvidia-smi")
    monkeypatch.setattr("importlib.util.find_spec", lambda _: None)

    def _run_falla(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, "nvidia-smi")

    monkeypatch.setattr("subprocess.run", _run_falla)

    with caplog.at_level("INFO"):
        info = detectar_gpu(comprobar_torch=False)

    assert info.disponible is False


def test_torch_sin_cuda_da_no_disponible(monkeypatch):
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/nvidia-smi")

    def _run_falso(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="NVIDIA GeForce RTX 3060, 12288, 576.02\n",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", _run_falso)
    monkeypatch.setattr("importlib.util.find_spec", lambda _: object())

    import sys
    import types

    torch_falso = types.ModuleType("torch")
    torch_falso.cuda = types.SimpleNamespace(is_available=lambda: False)
    monkeypatch.setitem(sys.modules, "torch", torch_falso)

    info = detectar_gpu(comprobar_torch=True)

    assert info.disponible is False
    assert info.torch_cuda is False


def test_buscar_nvidia_smi_usa_rutas_conocidas(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)

    def _access(ruta, _modo):
        return ruta == "/usr/lib/wsl/lib/nvidia-smi"

    monkeypatch.setattr("os.access", _access)

    assert buscar_nvidia_smi() == "/usr/lib/wsl/lib/nvidia-smi"


def test_info_gpu_es_frozen():
    info = InfoGPU(disponible=False)
    with pytest.raises(FrozenInstanceError):
        info.disponible = True
