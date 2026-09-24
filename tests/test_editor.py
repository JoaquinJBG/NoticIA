import shutil

import pytest
from pydub.generators import Sine

from noticia import editor

requiere_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="requiere ffmpeg instalado"
)


def _tono(ms, frecuencia=440):
    return Sine(frecuencia).to_audio_segment(duration=ms)


def _escribir(tmp_path, nombre, segmento, formato="wav"):
    ruta = tmp_path / nombre
    segmento.export(ruta, format=formato)
    return ruta


def test_unir_con_pausas_suma_silencio_entre_segmentos():
    segmentos = [_tono(100), _tono(100), _tono(100)]
    unido = editor._unir_con_pausas(segmentos, pausa_ms=350)
    # 3 tonos de 100 ms + 2 silencios de 350 ms
    assert abs(len(unido) - (300 + 700)) <= 2  # tolerancia de redondeo


def test_unir_con_pausas_un_solo_segmento_no_anade_silencio():
    unido = editor._unir_con_pausas([_tono(100)], pausa_ms=350)
    assert abs(len(unido) - 100) <= 2


def test_unir_con_pausas_lista_vacia():
    assert len(editor._unir_con_pausas([], pausa_ms=350)) == 0


def test_bucle_musica_alcanza_la_duracion_pedida():
    musica = _tono(2000)
    resultado = editor._bucle_musica(musica, duracion_ms=5000)
    assert abs(len(resultado) - 5000) <= 5


def test_bucle_musica_no_recorta_si_ya_es_mas_larga():
    musica = _tono(3000)
    resultado = editor._bucle_musica(musica, duracion_ms=1000)
    assert abs(len(resultado) - 1000) <= 5


def test_comprobar_sintonias_sin_faltantes(monkeypatch, tmp_path):
    ruta = tmp_path / "existe.mp3"
    _tono(200).export(ruta, format="mp3")
    monkeypatch.setattr(
        type(editor.settings),
        "sintonias",
        property(lambda self: {"espana": str(ruta)}),
    )
    assert editor.comprobar_sintonias(["espana"]) == []


def test_comprobar_sintonias_agrupa_bloques_por_fichero_faltante(monkeypatch, tmp_path, caplog):
    ruta_falta = str(tmp_path / "no_existe.mp3")
    monkeypatch.setattr(
        type(editor.settings),
        "sintonias",
        property(lambda self: {"espana": ruta_falta, "geopolitica": ruta_falta}),
    )
    with caplog.at_level("WARNING"):
        faltantes = editor.comprobar_sintonias(["espana", "geopolitica"])
    assert faltantes == [ruta_falta]
    assert "Falta la sintonía" in caplog.text
    assert "espana" in caplog.text
    assert "geopolitica" in caplog.text


def test_ensamblar_podcast_dinamico_sin_fragmentos_lanza_error():
    with pytest.raises(editor.ErrorMontaje):
        editor.ensamblar_podcast_dinamico({}, "salida.mp3")


@requiere_ffmpeg
def test_ensamblar_podcast_dinamico_produce_resultado_montaje(tmp_path, monkeypatch):
    monkeypatch.setattr(type(editor.settings), "sintonias", property(lambda self: {}))

    bloque1_wav = _escribir(tmp_path, "b1_0.wav", _tono(3000))
    bloque2_mp3 = _escribir(tmp_path, "b2_0.mp3", _tono(3000, 660), formato="mp3")

    fragmentos = {
        "espana": [bloque1_wav],
        "geopolitica": [bloque2_mp3],
    }
    salida = tmp_path / "podcast.mp3"

    resultado = editor.ensamblar_podcast_dinamico(fragmentos, salida)

    assert isinstance(resultado, editor.ResultadoMontaje)
    assert resultado.ruta == salida
    assert salida.exists()
    assert resultado.duracion_s > 0
    assert len(resultado.capitulos) == 2
    assert resultado.capitulos[0][0] == "espana"
    assert resultado.capitulos[0][1] == 0.0
    assert resultado.capitulos[1][0] == "geopolitica"
    assert resultado.capitulos[1][1] > 0.0
    assert resultado.sintonias_faltantes == []
    assert not bloque1_wav.exists()
    assert not bloque2_mp3.exists()


@requiere_ffmpeg
def test_ensamblar_podcast_dinamico_avisa_de_sintonias_faltantes(tmp_path, monkeypatch, caplog):
    ruta_falta = str(tmp_path / "no_existe.mp3")
    monkeypatch.setattr(
        type(editor.settings), "sintonias", property(lambda self: {"espana": ruta_falta})
    )

    bloque1_wav = _escribir(tmp_path, "b1_0.wav", _tono(600))
    salida = tmp_path / "podcast.mp3"

    with caplog.at_level("WARNING"):
        resultado = editor.ensamblar_podcast_dinamico({"espana": [bloque1_wav]}, salida)

    assert resultado.sintonias_faltantes == [ruta_falta]
    assert "Falta la sintonía" in caplog.text
