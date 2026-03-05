from pydub import AudioSegment
import os
from src.config import Config

def ensamblar_podcast(fragmentos, archivo_salida="noticIA_final.mp3"):
    if not fragmentos:
        print("❌ No hay fragmentos de voz para unir.")
        return

    print("🎬 Iniciando montaje final con sintonía y solapamiento dinámico...")

    # Usamos la sintonía configurada
    ruta_sintonia = Config.RUTA_SINTONIA

    # 2. Unimos las voces con solapamiento inteligente (crossfade)
    voces = AudioSegment.empty()
    ms_solapamiento = 250 # Milisegundos que se pisan las voces para naturalidad

    for i in range(len(fragmentos)):
        try:
            segmento_actual = AudioSegment.from_mp3(fragmentos[i])
            if i == 0:
                voces = segmento_actual
            else:
                # El crossfade de pydub hace que el final de 'voces' se mezcle con el inicio de 'segmento_actual'
                voces = voces.append(segmento_actual, crossfade=ms_solapamiento)
        except Exception as e:
            print(f"⚠️ Error procesando fragmento {fragmentos[i]}: {e}")
            continue

    # 3. Cargamos y mezclamos la música
    try:
        if os.path.exists(ruta_sintonia):
            musica = AudioSegment.from_mp3(ruta_sintonia)
            musica = musica - 28  # Volumen de fondo muy bajo
            
            # Repetir música si el podcast es largo
            if len(musica) < len(voces):
                veces_repetir = (len(voces) // len(musica)) + 1
                musica = musica * veces_repetir
            
            # Ajustar duración y aplicar fundidos
            musica = musica[:len(voces) + 2000]
            musica = musica.fade_in(2000).fade_out(3000)
            
            # Mezclar (voces entran al segundo 1)
            resultado = musica.overlay(voces, position=1000)
        else:
            print(f"⚠️ Sintonía no encontrada en {ruta_sintonia}. Generando solo voces.")
            resultado = voces
        
    except Exception as e:
        print(f"⚠️ Error con la sintonía: {e}. Generando solo voces.")
        resultado = voces

    # 4. Exportar el archivo final
    resultado.export(archivo_salida, format="mp3", bitrate="192k")
    
    # 5. Limpieza de fragmentos temporales
    for f in fragmentos:
        try:
            os.remove(f)
        except:
            pass
            
    print(f"✅ ¡Podcast terminado! El archivo es: {archivo_salida}")
