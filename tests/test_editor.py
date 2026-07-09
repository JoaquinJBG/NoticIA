from pydub import AudioSegment
from pydub.generators import Sine

from noticia import editor


def _tono(ms):
    return Sine(440).to_audio_segment(duration=ms)


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


def test_aplicar_mastering_deja_margen_y_no_satura():
    resultado = editor.aplicar_mastering(_tono(500))
    # normalize(headroom=1.0) deja el pico 1 dB por debajo de fondo de escala
    assert -1.5 <= resultado.max_dBFS <= -0.5


def test_aplicar_mastering_devuelve_audiosegment():
    assert isinstance(editor.aplicar_mastering(_tono(200)), AudioSegment)
