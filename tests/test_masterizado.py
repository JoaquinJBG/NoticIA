import shutil
import subprocess
from pathlib import Path

import pytest

from noticia.masterizado import (
    ErrorMasterizado,
    MedicionLoudness,
    masterizar_a_mp3,
    medir_ebur128,
    medir_loudnorm,
    parsear_json_loudnorm,
)

requiere_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="requiere ffmpeg instalado"
)

STDERR_LOUDNORM_EJEMPLO = """[out#0/null] video:0kB audio:1875kB
[Parsed_loudnorm_2 @ 0x1]
{
\t"input_i" : "-22.25",
\t"input_tp" : "-17.09",
\t"input_lra" : "0.00",
\t"input_thresh" : "-32.25",
\t"output_i" : "-15.97",
\t"output_tp" : "-10.88",
\t"output_lra" : "0.00",
\t"output_thresh" : "-25.97",
\t"normalization_type" : "dynamic",
\t"target_offset" : "-0.03"
}
"""


def _generar_tono(ruta: Path, duracion_s: int = 20) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duracion_s}",
            "-ar",
            "44100",
            str(ruta),
        ],
        check=True,
    )


def test_parsear_json_loudnorm_extrae_el_ultimo_bloque():
    medicion = parsear_json_loudnorm(STDERR_LOUDNORM_EJEMPLO)
    assert medicion == MedicionLoudness(
        lufs_integrados=-22.25,
        true_peak_dbtp=-17.09,
        lra=0.0,
        umbral=-32.25,
        offset=-0.03,
    )


def test_parsear_json_loudnorm_sin_bloque_lanza_error():
    with pytest.raises(ErrorMasterizado):
        parsear_json_loudnorm("no hay ningún bloque json aquí")


@requiere_ffmpeg
def test_medir_loudnorm_devuelve_medicion_del_tono(tmp_path):
    entrada = tmp_path / "tono.wav"
    _generar_tono(entrada)
    medicion = medir_loudnorm(entrada, objetivo_lufs=-16.0, true_peak=-1.5)
    assert isinstance(medicion, MedicionLoudness)
    assert medicion.lufs_integrados < 0


@requiere_ffmpeg
def test_masterizar_a_mp3_deja_el_mp3_en_torno_a_16_lufs(tmp_path):
    entrada = tmp_path / "tono.wav"
    _generar_tono(entrada)
    salida = tmp_path / "salida.mp3"
    medicion = masterizar_a_mp3(entrada, salida)
    assert salida.exists()
    assert -17.0 <= medicion.lufs_integrados <= -15.0
    assert medicion.true_peak_dbtp <= -1.0


@requiere_ffmpeg
def test_masterizar_a_mp3_admite_objetivo_y_bitrate_explicitos(tmp_path):
    entrada = tmp_path / "tono.wav"
    _generar_tono(entrada)
    salida = tmp_path / "salida.mp3"
    medicion = masterizar_a_mp3(entrada, salida, objetivo_lufs=-19.0, bitrate="128k")
    assert salida.exists()
    assert -20.0 <= medicion.lufs_integrados <= -18.0


@requiere_ffmpeg
def test_masterizar_a_mp3_incluye_metadatos(tmp_path):
    entrada = tmp_path / "tono.wav"
    _generar_tono(entrada)
    salida = tmp_path / "salida.mp3"
    masterizar_a_mp3(entrada, salida, metadatos={"title": "Episodio de prueba"})

    from mutagen.mp3 import MP3

    etiquetas = MP3(salida)
    assert "TIT2" in etiquetas
    assert str(etiquetas["TIT2"]) == "Episodio de prueba"


@requiere_ffmpeg
def test_medir_ebur128_sobre_mp3_masterizado(tmp_path):
    entrada = tmp_path / "tono.wav"
    _generar_tono(entrada)
    salida = tmp_path / "salida.mp3"
    masterizar_a_mp3(entrada, salida)
    lufs, pico = medir_ebur128(salida)
    assert -17.0 <= lufs <= -15.0
    assert pico <= -1.0


def test_masterizar_a_mp3_sin_ffmpeg_lanza_error(monkeypatch, tmp_path):
    def _no_encontrado(*args, **kwargs):
        raise FileNotFoundError("ffmpeg no está instalado")

    monkeypatch.setattr(subprocess, "run", _no_encontrado)
    entrada = tmp_path / "tono.wav"
    entrada.write_bytes(b"")
    with pytest.raises(ErrorMasterizado):
        masterizar_a_mp3(entrada, tmp_path / "salida.mp3")


def test_medir_ebur128_con_ffmpeg_que_falla_lanza_error(monkeypatch, tmp_path):
    def _falla(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", _falla)
    with pytest.raises(ErrorMasterizado):
        medir_ebur128(tmp_path / "cualquiera.mp3")
