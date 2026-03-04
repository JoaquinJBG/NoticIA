import edge_tts
import os
from src.config import Config

async def procesar_guion_a_audio(guion_texto):
    lineas = guion_texto.split("\n")
    piezas_audio = []
    
    print("🎙️ Empezando la locución...")

    # Usamos la carpeta temporal configurada
    os.makedirs(Config.CARPETA_TEMP, exist_ok=True)

    contador = 0
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        
        # Un parser más robusto: buscamos "alex" o "santi" al principio de la línea
        linea_lower = linea.lower()
        
        if "álex:" in linea_lower or "alex:" in linea_lower:
            texto = linea.split(":", 1)[1].strip()
            voz = Config.VOZ_ALEX
            nombre_locutor = "Álex"
        elif "santi:" in linea_lower:
            texto = linea.split(":", 1)[1].strip()
            voz = "es-ES-ElviraNeural" # Cambiado a Elvira para que se note la diferencia al 100%
            nombre_locutor = "Santi"
        else:
            # Si no hay prefijo claro, intentamos adivinarlo o lo saltamos
            print(f"⚠️ Saltando línea sin locutor: {linea[:30]}...")
            continue 

        if not texto: continue

        temp_file = os.path.join(Config.CARPETA_TEMP, f"fragmento_{contador}.mp3")
        
        try:
            print(f"🎙️ Grabando a {nombre_locutor} con voz {voz}...")
            communicate = edge_tts.Communicate(texto, voz)
            await communicate.save(temp_file)
            piezas_audio.append(temp_file)
            contador += 1
            print(f"✅ [{contador}] Grabado: {texto[:40]}...")
        except Exception as e:
            print(f"❌ Error grabando línea {contador}: {e}")
            continue

    print(f"🎬 Se han generado {len(piezas_audio)} fragmentos.")
    return piezas_audio