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

# Si el `alimiter` de la pasada 2 recorta tanto que el LUFS final se desvía
# más de esto (LU) del objetivo, se corrige con una segunda pasada de
# ganancia (ver `masterizar_a_mp3`).
MARGEN_CORRECCION_LUFS = 0.5


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


def _ganancia_db(objetivo_lufs: float, medido_lufs: float) -> float:
    """Ganancia (dB) para llevar `medido_lufs` a `objetivo_lufs`."""
    return objetivo_lufs - medido_lufs


def _limite_lineal(true_peak_dbtp: float) -> float:
    """Convierte un límite de true peak en dBTP a amplitud lineal (0-1)

    para el parámetro `limit` de `alimiter`.
    """
    return 10 ** (true_peak_dbtp / 20)


def _construir_filtro_pasada_2(ganancia_db: float, limite_lineal: float) -> str:
    """Filtro de la pasada 2: ganancia fija + limitador de picos.

    Sustituye al `loudnorm(linear=true)` de dos pasadas (que sobremuestrea a
    192 kHz y es muy lento en episodios largos) por una ganancia calculada a
    partir de la medición de la pasada 1 (`measured_I`) y un `alimiter` que
    solo actúa sobre los picos que superarían `true_peak`. `level=false`
    evita que el limitador reajuste el nivel medio por su cuenta.
    """
    return (
        f"{PREFILTRO},volume={ganancia_db:.3f}dB,"
        f"alimiter=limit={limite_lineal:.6f}:level=false,aresample=44100"
    )


def _codificar_mp3(
    entrada_wav: Path,
    salida_mp3: Path,
    filtro: str,
    bitrate: str,
    metadatos: Mapping[str, str] | None,
) -> None:
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


def masterizar_a_mp3(
    entrada_wav: Path,
    salida_mp3: Path,
    objetivo_lufs: float | None = None,
    true_peak: float | None = None,
    bitrate: str | None = None,
    metadatos: Mapping[str, str] | None = None,
) -> MedicionLoudness:
    """Masteriza `entrada_wav` a MP3: mide con `loudnorm` y aplica ganancia + limiter.

    Pasada 1: `loudnorm` sin tocar el audio (-f null), solo para medir
    `measured_I`/`measured_TP` (ver `medir_loudnorm`).

    Pasada 2: en vez de un segundo `loudnorm(linear=true)` (dos pasadas que
    sobremuestrean a 192 kHz para ajustar el true peak; varios minutos en un
    episodio real), se aplica la ganancia fija `objetivo_lufs - measured_I`
    con `volume=<g>dB` y se limitan los picos que la superen con `alimiter`,
    todo en una sola codificación a MP3 -- mucho más rápido.

    Si el propio limitador recorta tanto que el LUFS final medido con
    `ebur128` se desvía más de `MARGEN_CORRECCION_LUFS` del objetivo, se
    corrige con una segunda medición (la misma `ebur128` final, que ya hacía
    falta) y una única iteración de ganancia extra -- no un bucle.
    """
    objetivo_lufs = settings.objetivo_lufs if objetivo_lufs is None else objetivo_lufs
    true_peak = settings.true_peak_dbtp if true_peak is None else true_peak
    bitrate = bitrate or settings.bitrate_mp3

    entrada_wav = Path(entrada_wav)
    salida_mp3 = Path(salida_mp3)
    salida_mp3.parent.mkdir(parents=True, exist_ok=True)

    medido = medir_loudnorm(entrada_wav, objetivo_lufs, true_peak)

    ganancia_db = _ganancia_db(objetivo_lufs, medido.lufs_integrados)
    limite_lineal = _limite_lineal(true_peak)

    _codificar_mp3(
        entrada_wav,
        salida_mp3,
        _construir_filtro_pasada_2(ganancia_db, limite_lineal),
        bitrate,
        metadatos,
    )
    lufs_final, tp_final = medir_ebur128(salida_mp3)

    desviacion = lufs_final - objetivo_lufs
    if abs(desviacion) > MARGEN_CORRECCION_LUFS:
        logger.info(
            "El LUFS tras el limiter (%.1f) se desvía %.1f LU del objetivo (%.1f): "
            "corrigiendo con una segunda pasada de ganancia.",
            lufs_final,
            abs(desviacion),
            objetivo_lufs,
        )
        ganancia_db -= desviacion
        _codificar_mp3(
            entrada_wav,
            salida_mp3,
            _construir_filtro_pasada_2(ganancia_db, limite_lineal),
            bitrate,
            metadatos,
        )
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
