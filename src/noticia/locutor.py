import logging
import os

import edge_tts

from noticia.config import settings

logger = logging.getLogger("noticia.locutor")


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
