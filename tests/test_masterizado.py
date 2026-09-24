import shutil
import subprocess
import time
from pathlib import Path

import pytest

from noticia import masterizado
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


# --------------------------------------------------------------- pasada 2: ganancia + limiter


def test_ganancia_db_es_la_diferencia_entre_objetivo_y_medido():
    assert masterizado._ganancia_db(-16.0, -20.0) == pytest.approx(4.0)
    assert masterizado._ganancia_db(-16.0, -10.0) == pytest.approx(-6.0)
    assert masterizado._ganancia_db(-16.0, -16.0) == pytest.approx(0.0)


def test_limite_lineal_convierte_dbtp_a_amplitud():
    assert masterizado._limite_lineal(0.0) == pytest.approx(1.0)
    assert masterizado._limite_lineal(-1.5) == pytest.approx(10 ** (-1.5 / 20))
    assert 0.0 < masterizado._limite_lineal(-1.5) < 1.0


def test_construir_filtro_pasada_2_usa_volume_y_alimiter_sin_linear():
    filtro = masterizado._construir_filtro_pasada_2(4.0, 0.8414)
    assert "volume=4.000dB" in filtro
    assert "alimiter=limit=0.841400:level=false" in filtro
    assert "aresample=44100" in filtro
    # La pasada 2 ya no debe usar el modo `linear=true` de loudnorm (la parte
    # lenta que sobremuestrea a 192k): no debe quedar ni rastro de loudnorm.
    assert "loudnorm" not in filtro
    assert "linear=true" not in filtro


def test_masterizar_a_mp3_una_sola_codificacion_si_no_hace_falta_corregir(monkeypatch, tmp_path):
    entrada = tmp_path / "tono.wav"
    entrada.write_bytes(b"contenido de prueba")
    salida = tmp_path / "salida.mp3"

    llamadas_encode = []

    def _fake_ejecutar_ffmpeg(args):
        llamadas_encode.append(args)
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(masterizado, "_ejecutar_ffmpeg", _fake_ejecutar_ffmpeg)
    monkeypatch.setattr(
        masterizado,
        "medir_loudnorm",
        lambda *a, **k: MedicionLoudness(
            lufs_integrados=-23.0, true_peak_dbtp=-10.0, lra=5.0, umbral=-30.0, offset=0.0
        ),
    )
    monkeypatch.setattr(masterizado, "medir_ebur128", lambda ruta: (-16.1, -1.3))

    resultado = masterizar_a_mp3(entrada, salida, objetivo_lufs=-16.0, true_peak=-1.5)

    assert len(llamadas_encode) == 1
    assert resultado.lufs_integrados == -16.1
    assert resultado.true_peak_dbtp == -1.3


def test_masterizar_a_mp3_corrige_con_una_segunda_pasada_si_el_limiter_se_desvia(
    monkeypatch, tmp_path
):
    """Si el `alimiter` recorta tanto que el LUFS final se desvía >0.5 LU del
    objetivo, se corrige con una segunda medición barata y una única
    iteración de ganancia (una segunda codificación), no con un bucle."""
    entrada = tmp_path / "tono.wav"
    entrada.write_bytes(b"contenido de prueba")
    salida = tmp_path / "salida.mp3"

    llamadas_encode = []

    def _fake_ejecutar_ffmpeg(args):
        llamadas_encode.append(args)
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    medidas = iter([(-18.0, -2.0), (-16.05, -1.3)])

    monkeypatch.setattr(masterizado, "_ejecutar_ffmpeg", _fake_ejecutar_ffmpeg)
    monkeypatch.setattr(
        masterizado,
        "medir_loudnorm",
        lambda *a, **k: MedicionLoudness(
            lufs_integrados=-23.0, true_peak_dbtp=-10.0, lra=5.0, umbral=-30.0, offset=0.0
        ),
    )
    monkeypatch.setattr(masterizado, "medir_ebur128", lambda ruta: next(medidas))

    resultado = masterizar_a_mp3(entrada, salida, objetivo_lufs=-16.0, true_peak=-1.5)

    assert len(llamadas_encode) == 2
    # La segunda pasada de ganancia compensa exactamente la desviación medida.
    ganancia_1 = next(a for a in llamadas_encode[0] if a.startswith("highpass"))
    ganancia_2 = next(a for a in llamadas_encode[1] if a.startswith("highpass"))
    assert ganancia_1 != ganancia_2
    assert resultado.lufs_integrados == -16.05
    assert resultado.true_peak_dbtp == -1.3


@requiere_ffmpeg
def test_masterizar_a_mp3_es_mucho_mas_rapido_que_loudnorm_lineal_en_dos_pasadas(tmp_path):
    """Regresión de rendimiento: la pasada 2 ya no debe sobremuestrear a 192k
    con `loudnorm(linear=true)` (varios minutos para un episodio real). Con
    volume+alimiter, masterizar un clip de 60s debe tardar unos pocos
    segundos, no decenas."""
    entrada = tmp_path / "tono.wav"
    _generar_tono(entrada, duracion_s=60)
    salida = tmp_path / "salida.mp3"

    inicio = time.monotonic()
    masterizar_a_mp3(entrada, salida)
    duracion = time.monotonic() - inicio

    assert salida.exists()
    assert duracion < 15.0
