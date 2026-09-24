"""Detección robusta de GPU NVIDIA, sin requerir torch instalado."""

import functools
import importlib.util
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger("noticia.gpu")

_RUTAS_NVIDIA_SMI = ("/usr/lib/wsl/lib/nvidia-smi", "/usr/bin/nvidia-smi")


@dataclass(frozen=True)
class InfoGPU:
    disponible: bool
    nombre: str = ""
    vram_mib: int = 0
    driver: str = ""
    torch_cuda: bool | None = None  # None = torch no instalado
    motivo: str = ""


def buscar_nvidia_smi() -> str | None:
    """Localiza el binario `nvidia-smi`, incluidas las rutas típicas de WSL."""
    ruta = shutil.which("nvidia-smi")
    if ruta:
        return ruta
    return next((r for r in _RUTAS_NVIDIA_SMI if os.access(r, os.X_OK)), None)


def _torch_cuda() -> bool | None:
    if importlib.util.find_spec("torch") is None:
        return None
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception as exc:
        logger.warning("torch presente pero falló la comprobación de CUDA: %s", exc)
        return False


@functools.lru_cache(maxsize=1)
def detectar_gpu(comprobar_torch: bool = True) -> InfoGPU:
    """Detecta si hay una GPU NVIDIA utilizable. El resultado se cachea."""
    if os.environ.get("CUDA_VISIBLE_DEVICES") in ("", "-1"):
        return InfoGPU(disponible=False, motivo="CUDA_VISIBLE_DEVICES oculta las GPUs")

    torch_ok = _torch_cuda() if comprobar_torch else None

    smi = buscar_nvidia_smi()
    if smi is None:
        return InfoGPU(disponible=False, torch_cuda=torch_ok, motivo="nvidia-smi no encontrado")

    try:
        resultado = subprocess.run(
            [
                smi,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except Exception as exc:
        logger.info("nvidia-smi falló: %s", exc)
        return InfoGPU(disponible=False, torch_cuda=torch_ok, motivo=f"nvidia-smi falló: {exc}")

    salida = resultado.stdout.strip().splitlines()
    if not salida:
        return InfoGPU(disponible=False, torch_cuda=torch_ok, motivo="nvidia-smi sin GPUs")

    nombre, vram, driver = (campo.strip() for campo in salida[0].split(",")[:3])
    disponible = torch_ok is not False  # hay GPU; si torch está, debe ver CUDA
    motivo = "" if disponible else "GPU presente pero torch sin CUDA (¿wheel CPU?)"
    return InfoGPU(
        disponible=disponible,
        nombre=nombre,
        vram_mib=int(float(vram)),
        driver=driver,
        torch_cuda=torch_ok,
        motivo=motivo,
    )
