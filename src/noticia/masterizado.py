"""Masterizado final del episodio: ffmpeg ``loudnorm`` en dos pasadas.

Sustituye al mastering de pydub (`editor.aplicar_mastering`): normaliza a un
nivel de loudness objetivo (LUFS) con un límite de true peak, en vez de un
simple `normalize` + compresor sobre picos.
"""

import json
import logging
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from noticia.config import settings

logger = logging.getLogger("noticia.masterizado")

# Prefiltro aplicado antes de `loudnorm`: fuera el retumbe por debajo de 80 Hz
# y una compresión suave que evita que loudnorm tenga que estirar demasiado.
PREFILTRO = "highpass=f=80,acompressor=threshold=-18dB:ratio=2.5:attack=5:release=50"

_PATRON_BLOQUE_JSON = re.compile(r"\{[^{}]*\}")
_PATRON_LUFS = re.compile(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS")
_PATRON_PEAK = re.compile(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS")


class ErrorMasterizado(Exception):
    """Fallo al invocar ffmpeg para medir o masterizar el audio."""


@dataclass(frozen=True)
class MedicionLoudness:
    lufs_integrados: float
    true_peak_dbtp: float
    lra: float
    umbral: float
    offset: float


def _ejecutar_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    try:
        resultado = subprocess.run(args, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise ErrorMasterizado(f"ffmpeg no está disponible: {exc}") from exc
    if resultado.returncode != 0:
        cola = "\n".join(resultado.stderr.splitlines()[-20:])
        raise ErrorMasterizado(f"ffmpeg devolvió el código {resultado.returncode}:\n{cola}")
    return resultado


def parsear_json_loudnorm(stderr: str) -> MedicionLoudness:
    """Extrae el último bloque JSON que imprime `loudnorm` en stderr."""
    bloques = _PATRON_BLOQUE_JSON.findall(stderr)
    if not bloques:
        raise ErrorMasterizado("No se encontró el bloque JSON de loudnorm en la salida de ffmpeg.")
    datos = json.loads(bloques[-1])
    return MedicionLoudness(
        lufs_integrados=float(datos["input_i"]),
        true_peak_dbtp=float(datos["input_tp"]),
        lra=float(datos["input_lra"]),
        umbral=float(datos["input_thresh"]),
        offset=float(datos["target_offset"]),
    )


def medir_loudnorm(
    entrada: Path, objetivo_lufs: float, true_peak: float, lra: float = 11.0
) -> MedicionLoudness:
    """Primera pasada de `loudnorm`: mide sin tocar el audio (-f null)."""
    filtro = f"{PREFILTRO},loudnorm=I={objetivo_lufs}:TP={true_peak}:LRA={lra}:print_format=json"
    args = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(entrada),
        "-af",
        filtro,
        "-f",
        "null",
        "-",
    ]
    resultado = _ejecutar_ffmpeg(args)
    return parsear_json_loudnorm(resultado.stderr)


def medir_ebur128(ruta: Path) -> tuple[float, float]:
    """Mide el resultado final: (LUFS integrados, true peak dBTP)."""
    args = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(ruta),
        "-af",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    resultado = _ejecutar_ffmpeg(args)
    stderr = resultado.stderr
    lufs = _PATRON_LUFS.findall(stderr)
    picos = _PATRON_PEAK.findall(stderr)
    if not lufs or not picos:
        raise ErrorMasterizado("No se pudo leer la medición ebur128 de la salida de ffmpeg.")
    return float(lufs[-1]), float(picos[-1])


def masterizar_a_mp3(
    entrada_wav: Path,
    salida_mp3: Path,
    objetivo_lufs: float | None = None,
    true_peak: float | None = None,
    bitrate: str | None = None,
    metadatos: Mapping[str, str] | None = None,
) -> MedicionLoudness:
    """Masteriza `entrada_wav` a MP3 en dos pasadas de `loudnorm` y lo mide."""
    objetivo_lufs = settings.objetivo_lufs if objetivo_lufs is None else objetivo_lufs
    true_peak = settings.true_peak_dbtp if true_peak is None else true_peak
    bitrate = bitrate or settings.bitrate_mp3

    entrada_wav = Path(entrada_wav)
    salida_mp3 = Path(salida_mp3)
    salida_mp3.parent.mkdir(parents=True, exist_ok=True)

    medido = medir_loudnorm(entrada_wav, objetivo_lufs, true_peak)

    filtro = (
        f"{PREFILTRO},loudnorm=I={objetivo_lufs}:TP={true_peak}:LRA=11:"
        f"measured_I={medido.lufs_integrados}:measured_TP={medido.true_peak_dbtp}:"
        f"measured_LRA={medido.lra}:measured_thresh={medido.umbral}:"
        f"offset={medido.offset}:linear=true,aresample=44100"
    )
    args = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-nostats",
        "-i",
        str(entrada_wav),
        "-af",
        filtro,
        "-ar",
        "44100",
        "-c:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-id3v2_version",
        "3",
    ]
    for clave, valor in (metadatos or {}).items():
        args += ["-metadata", f"{clave}={valor}"]
    args.append(str(salida_mp3))

    _ejecutar_ffmpeg(args)

    lufs_final, tp_final = medir_ebur128(salida_mp3)
    if tp_final > -1.0:
        logger.warning(
            "El true peak final (%.2f dBTP) de %s supera -1.0 dBTP.", tp_final, salida_mp3
        )

    logger.info(
        "Masterizado %s: %.1f LUFS integrados, %.1f dBTP de true peak.",
        salida_mp3,
        lufs_final,
        tp_final,
    )
    return MedicionLoudness(
        lufs_integrados=lufs_final,
        true_peak_dbtp=tp_final,
        lra=medido.lra,
        umbral=medido.umbral,
        offset=medido.offset,
    )
