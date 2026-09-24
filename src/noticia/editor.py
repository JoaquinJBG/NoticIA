"""Montaje del episodio: sintonías por bloque + masterizado ffmpeg."""

import logging
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydub import AudioSegment

from noticia.bloques import ORDEN_BLOQUES
from noticia.config import settings
from noticia.masterizado import MedicionLoudness, masterizar_a_mp3

logger = logging.getLogger("noticia.editor")

# Crossfade al enlazar bloques entre sí y al hacer bucle con la música de
# fondo, para no dejar cortes secos.
CROSSFADE_BLOQUES_MS = 1500
CROSSFADE_MUSICA_MS = 1500

VOL_FONDO_DB = -28
VOL_RAFAGA_DB = -12
DURACION_RAFAGA_MS = 2000


class ErrorMontaje(Exception):
    """Fallo irrecuperable al montar el episodio."""


@dataclass(frozen=True)
class ResultadoMontaje:
    ruta: Path
    duracion_s: float
    capitulos: list[tuple[str, float]]
    sintonias_faltantes: list[str]
    loudness: MedicionLoudness


def _unir_con_pausas(segmentos: list[AudioSegment], pausa_ms: int) -> AudioSegment:
    """Concatena segmentos separándolos por silencio. Sin crossfade.

    El crossfade solapaba el final de cada frase con el principio de la
    siguiente: en voz eso pisa sílabas.
    """
    if not segmentos:
        return AudioSegment.empty()
    silencio = AudioSegment.silent(duration=pausa_ms)
    resultado = segmentos[0]
    for segmento in segmentos[1:]:
        resultado = resultado + silencio + segmento
    return resultado


def comprobar_sintonias(bloques: Iterable[str] = ORDEN_BLOQUES) -> list[str]:
    """Comprueba qué sintonías de `bloques` faltan en disco.

    Devuelve las rutas únicas que faltan (en el orden en que aparecen) y
    registra un aviso por cada una, listando los bloques afectados.
    """
    mapa = settings.sintonias
    bloques_por_ruta: dict[str, list[str]] = {}
    orden: list[str] = []
    for bloque in bloques:
        ruta = mapa.get(bloque)
        if not ruta:
            continue
        if Path(ruta).exists():
            continue
        if ruta not in bloques_por_ruta:
            bloques_por_ruta[ruta] = []
            orden.append(ruta)
        bloques_por_ruta[ruta].append(bloque)

    for ruta in orden:
        logger.warning(
            "Falta la sintonía %s (bloques: %s). El bloque irá sin música. "
            "Copia el fichero a sintonias/ (no está en git).",
            ruta,
            ", ".join(bloques_por_ruta[ruta]),
        )
    return orden


def _bucle_musica(
    musica: AudioSegment, duracion_ms: int, crossfade_ms: int = CROSSFADE_MUSICA_MS
) -> AudioSegment:
    """Repite `musica` en bucle (con crossfade) hasta cubrir `duracion_ms`."""
    if len(musica) == 0 or duracion_ms <= 0:
        return musica[:duracion_ms] if duracion_ms > 0 else AudioSegment.empty()

    crossfade = min(crossfade_ms, len(musica) - 1) if len(musica) > 1 else 0
    resultado = musica
    while len(resultado) < duracion_ms:
        if crossfade > 0:
            resultado = resultado.append(musica, crossfade=crossfade)
        else:
            resultado = resultado + musica
    return resultado[:duracion_ms]


def _cargar_fragmentos(rutas: Sequence[str | Path]) -> list[AudioSegment]:
    segmentos = []
    for ruta in rutas:
        try:
            segmentos.append(AudioSegment.from_file(ruta))
        except Exception as exc:
            logger.warning("No se pudo cargar el fragmento %s: %s", ruta, exc)
    return segmentos


def _mezclar_musica(bloque: str, voces_bloque: AudioSegment) -> AudioSegment:
    ruta_musica = settings.sintonias.get(bloque)
    if not ruta_musica or not Path(ruta_musica).exists():
        return voces_bloque
    try:
        musica = AudioSegment.from_file(ruta_musica)
        musica_bucle = _bucle_musica(musica, len(voces_bloque) + DURACION_RAFAGA_MS)
        rafaga = musica_bucle[:DURACION_RAFAGA_MS] + VOL_RAFAGA_DB
        fondo = musica_bucle[DURACION_RAFAGA_MS:] + VOL_FONDO_DB
        musica_final = (rafaga + fondo).fade_out(3000)
        return musica_final.overlay(voces_bloque, position=500)
    except Exception as exc:
        logger.warning("Fallo al mezclar música del bloque %s: %s", bloque, exc)
        return voces_bloque


def _montar_bloque(bloque: str, archivos: Sequence[str | Path]) -> AudioSegment:
    segmentos = _cargar_fragmentos(archivos)
    voces_bloque = _unir_con_pausas(segmentos, settings.pausa_entre_turnos_ms)
    if len(voces_bloque) == 0:
        return voces_bloque
    return _mezclar_musica(bloque, voces_bloque)


def _anadir_bloque(podcast: AudioSegment, bloque_audio: AudioSegment) -> tuple[AudioSegment, float]:
    """Encadena `bloque_audio` a `podcast` con crossfade. Devuelve (podcast, inicio_s)."""
    if len(podcast) == 0:
        return bloque_audio, 0.0
    crossfade = min(CROSSFADE_BLOQUES_MS, len(podcast), len(bloque_audio))
    inicio_s = (len(podcast) - crossfade) / 1000
    if crossfade > 0:
        nuevo_podcast = podcast.append(bloque_audio, crossfade=crossfade)
    else:
        nuevo_podcast = podcast + bloque_audio
    return nuevo_podcast, inicio_s


def ensamblar_podcast_dinamico(
    fragmentos_por_bloque: Mapping[str, Sequence[str | Path]],
    archivo_salida: str | Path,
    metadatos: Mapping[str, str] | None = None,
) -> ResultadoMontaje:
    """Monta los bloques en un único episodio y lo masteriza a MP3."""
    if not fragmentos_por_bloque:
        raise ErrorMontaje("No hay fragmentos para unir.")

    sintonias_faltantes = comprobar_sintonias(fragmentos_por_bloque.keys())

    podcast_completo = AudioSegment.empty()
    capitulos: list[tuple[str, float]] = []

    for bloque, archivos in fragmentos_por_bloque.items():
        if not archivos:
            continue
        logger.info("Procesando bloque: %s...", bloque)
        bloque_audio = _montar_bloque(bloque, archivos)
        if len(bloque_audio) == 0:
            continue
        podcast_completo, inicio_s = _anadir_bloque(podcast_completo, bloque_audio)
        capitulos.append((bloque, inicio_s))

    if len(podcast_completo) == 0:
        raise ErrorMontaje("El montaje no ha producido ningún audio.")

    duracion_s = len(podcast_completo) / 1000
    archivo_salida = Path(archivo_salida)

    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_wav = Path(directorio_tmp) / "mezcla.wav"
        podcast_completo.export(ruta_wav, format="wav")
        loudness = masterizar_a_mp3(ruta_wav, archivo_salida, metadatos=metadatos)

    rutas_borradas: set[str] = set()
    for archivos in fragmentos_por_bloque.values():
        for ruta in archivos:
            ruta_str = str(ruta)
            if ruta_str in rutas_borradas:
                continue
            rutas_borradas.add(ruta_str)
            try:
                Path(ruta).unlink()
            except Exception as exc:
                logger.debug("No se pudo borrar el temporal %s: %s", ruta, exc)

    logger.info("Montaje completado: %s", archivo_salida)
    return ResultadoMontaje(
        ruta=archivo_salida,
        duracion_s=duracion_s,
        capitulos=capitulos,
        sintonias_faltantes=sintonias_faltantes,
        loudness=loudness,
    )
