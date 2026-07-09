import logging
import os
import unicodedata

import edge_tts

from noticia.config import settings

logger = logging.getLogger("noticia.locutor")

_LOCUTORES = ("alex", "maria")


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


async def procesar_guion_a_audio(guion_texto):
    lineas = guion_texto.split("\n")
    piezas_audio = []

    logger.info("Empezando la locución...")

    # Usamos la carpeta temporal configurada
    os.makedirs(settings.carpeta_temp, exist_ok=True)

    contador = 0
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        # Un parser más robusto: buscamos "alex" o "santi" al principio de la línea
        linea_lower = linea.lower()

        if "álex:" in linea_lower or "alex:" in linea_lower:
            texto = linea.split(":", 1)[1].strip()
            voz = settings.voz_alex
            nombre_locutor = "Álex"
        elif "santi:" in linea_lower:
            texto = linea.split(":", 1)[1].strip()
            voz = settings.voz_santi
            nombre_locutor = "Santi"
        else:
            # Si no hay prefijo claro, intentamos adivinarlo o lo saltamos
            logger.warning("Saltando línea sin locutor: %s...", linea[:30])
            continue

        if not texto:
            continue

        temp_file = os.path.join(settings.carpeta_temp, f"fragmento_{contador}.mp3")

        try:
            logger.info("Grabando a %s con voz %s...", nombre_locutor, voz)
            communicate = edge_tts.Communicate(texto, voz)
            await communicate.save(temp_file)
            piezas_audio.append(temp_file)
            contador += 1
            logger.info("[%s] Grabado: %s...", contador, texto[:40])
        except Exception as e:
            logger.error("Error grabando línea %s: %s", contador, e)
            continue

    logger.info("Se han generado %s fragmentos.", len(piezas_audio))
    return piezas_audio
