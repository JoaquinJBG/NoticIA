import logging
import os
import unicodedata

import edge_tts

from noticia.config import settings

logger = logging.getLogger("noticia.locutor")

_LOCUTORES = ("alex", "maria")

_NOMBRE_MOSTRADO = {"alex": "Álex", "maria": "María"}


def _normalizar(texto: str) -> str:
    """minúsculas y sin tildes, para comparar el prefijo del locutor."""
    texto = texto.strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _parsear_linea(linea: str) -> tuple[str, str] | None:
    """ "Álex: hola" -> ("alex", "hola"). None si la línea no es diálogo.

    El prefijo es lo que hay ANTES del primer dos puntos, y debe ser un locutor
    conocido. Así una mención a otro locutor dentro de la frase no confunde la
    atribución, y un dos puntos dentro del texto no rompe el corte.
    """
    if ":" not in linea:
        return None
    prefijo, resto = linea.split(":", 1)
    locutor = _normalizar(prefijo)
    if locutor not in _LOCUTORES:
        return None
    texto = resto.strip()
    if not texto:
        return None
    return locutor, texto


def _voz_y_rate(locutor: str) -> tuple[str, str]:
    if locutor == "alex":
        return settings.voz_alex, settings.rate_alex
    return settings.voz_maria, settings.rate_maria


async def procesar_guion_a_audio(guion_texto):
    piezas_audio = []

    logger.info("Empezando la locución...")
    os.makedirs(settings.carpeta_temp, exist_ok=True)

    contador = 0
    for linea in guion_texto.split("\n"):
        parseada = _parsear_linea(linea.strip())
        if parseada is None:
            if linea.strip():
                logger.warning("Saltando línea sin locutor: %s...", linea.strip()[:30])
            continue

        locutor_id, texto = parseada
        voz, rate = _voz_y_rate(locutor_id)
        temp_file = os.path.join(settings.carpeta_temp, f"fragmento_{contador}.mp3")

        nombre = _NOMBRE_MOSTRADO.get(locutor_id, locutor_id)
        try:
            logger.info("Grabando a %s con voz %s (rate %s)...", nombre, voz, rate)
            communicate = edge_tts.Communicate(texto, voz, rate=rate)
            await communicate.save(temp_file)
            piezas_audio.append(temp_file)
            logger.info("Fragmento %s grabado para %s.", contador, nombre)
            contador += 1
        except Exception as exc:
            logger.error("Error grabando la línea %s: %s", contador, exc)
            continue

    logger.info("Se han generado %s fragmentos.", len(piezas_audio))
    return piezas_audio
