import logging
import os

from pydub import AudioSegment, effects

from noticia.config import settings

logger = logging.getLogger("noticia.editor")


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


def aplicar_mastering(audio: AudioSegment) -> AudioSegment:
    """Cadena sobria: limpia graves, nivela, comprime suave y deja margen.

    La versión anterior sumaba una copia filtrada sobre el original
    (low_pass_filter().apply_gain().overlay()), lo que enturbiaba y saturaba,
    y normalizaba a 0.1 dB del máximo.
    """
    logger.info("Aplicando mastering...")
    audio = audio.high_pass_filter(80)  # fuera el retumbe: esto sí es una EQ
    audio = effects.normalize(audio)
    audio = effects.compress_dynamic_range(
        audio, threshold=-18.0, ratio=2.5, attack=5.0, release=50.0
    )
    return effects.normalize(audio, headroom=1.0)


def ensamblar_podcast_dinamico(fragmentos_por_bloque, archivo_salida="noticIA_final.mp3"):
    if not fragmentos_por_bloque:
        logger.error("No hay fragmentos para unir.")
        return

    logger.info("Iniciando montaje dinámico profesional...")
    podcast_completo = AudioSegment.empty()

    for categoria, archivos in fragmentos_por_bloque.items():
        if not archivos:
            continue

        logger.info("Procesando bloque: %s...", categoria)

        segmentos = []
        for f in archivos:
            try:
                segmentos.append(AudioSegment.from_mp3(f))
            except Exception as exc:
                logger.warning("No se pudo cargar el fragmento %s: %s", f, exc)
                continue
        voces_bloque = _unir_con_pausas(segmentos, settings.pausa_entre_turnos_ms)
        if len(voces_bloque) == 0:
            continue

        ruta_musica = settings.sintonias.get(categoria, settings.ruta_sintonia)
        try:
            if os.path.exists(ruta_musica):
                musica = AudioSegment.from_mp3(ruta_musica)
                vol_fondo = -28
                vol_rafaga = -12

                if len(musica) < len(voces_bloque):
                    musica = musica * (len(voces_bloque) // len(musica) + 1)

                musica = musica[: len(voces_bloque) + 2000]
                rafaga = musica[:2000] + vol_rafaga
                fondo = musica[2000:] + vol_fondo
                musica_final = (rafaga + fondo).fade_out(3000)

                bloque_mezclado = musica_final.overlay(voces_bloque, position=500)
            else:
                bloque_mezclado = voces_bloque
        except Exception as exc:
            logger.warning("Fallo al mezclar música del bloque %s: %s", categoria, exc)
            bloque_mezclado = voces_bloque

        if len(podcast_completo) == 0:
            podcast_completo = bloque_mezclado
        else:
            podcast_completo = podcast_completo.append(bloque_mezclado, crossfade=1000)

    # --- FASE DE MASTERING ---
    podcast_final = aplicar_mastering(podcast_completo)

    # 4. Exportar y limpiar
    podcast_final.export(
        archivo_salida,
        format="mp3",
        bitrate="192k",
        tags={"artist": "NoticIA", "album": "Podcast Diario"},
    )

    for cat in fragmentos_por_bloque:
        for f in fragmentos_por_bloque[cat]:
            try:
                os.remove(f)
            except Exception as exc:
                logger.debug("No se pudo borrar el temporal %s: %s", f, exc)

    logger.info("¡MASTERING COMPLETADO! Podcast listo para subir: %s", archivo_salida)
