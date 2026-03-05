from pydub import AudioSegment
import os
from src.config import Config

def ensamblar_podcast(fragmentos, archivo_salida="noticIA_final.mp3"):
    if not fragmentos:
        print("❌ No hay fragmentos de voz para unir.")
        return

    print("🎬 Iniciando montaje final con sintonía...")
    
    # Usamos la sintonía configurada
    ruta_sintonia = Config.RUTA_SINTONIA
    
    # 2. Unimos las voces primero
    voces = AudioSegment.empty()
    pausa_entre_voces = AudioSegment.silent(duration=800) # Pausa un poco más larga para que respiren

    for archivo in fragmentos:
        segmento = AudioSegment.from_mp3(archivo)
        voces += segmento + pausa_entre_voces

    # 3. Cargamos y mezclamos la música
    try:
        if os.path.exists(ruta_sintonia):
            musica = AudioSegment.from_mp3(ruta_sintonia)
            musica = musica - 28  # Volumen de fondo casi imperceptible para tertulias largas
            
            # Repetir música si el podcast es largo
            if len(musica) < len(voces):
                musica = musica * (len(voces) // len(musica) + 1)
            
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