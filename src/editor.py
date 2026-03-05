from pydub import AudioSegment, effects
import os
from src.config import Config

def aplicar_mastering_pro(audio):
    """
    Aplica una cadena de mastering: Normalización de pico, 
    compresión de rango dinámico y ganancia de calidez.
    """
    print("🎚️ Aplicando Mastering Profesional (EQ + Compresión)...")
    
    # 1. Normalizar para asegurar que trabajamos con buen nivel
    audio = effects.normalize(audio)
    
    # 2. Compresión de rango dinámico (hace que las voces suenen constantes y potentes)
    # Simulamos un compresor reduciendo los picos y subiendo el nivel medio
    audio = effects.compress_dynamic_range(
        audio, 
        threshold=-20.0, 
        ratio=3.0, 
        attack=5.0, 
        release=50.0
    )
    
    # 3. Pequeño refuerzo de graves para dar calidez de estudio (EQ básica)
    # Subimos un poco las frecuencias bajas (frecuencia de corte aproximada)
    audio = audio.low_pass_filter(3000).apply_gain(1.5).overlay(audio)
    
    # 4. Limitador final para evitar distorsión
    return effects.normalize(audio, headroom=0.1)

def ensamblar_podcast_dinamico(fragmentos_por_bloque, archivo_salida="noticIA_final.mp3"):
    if not fragmentos_por_bloque:
        print("❌ No hay fragmentos para unir.")
        return

    print("🎬 Iniciando montaje dinámico profesional...")
    podcast_completo = AudioSegment.empty()
    ms_solapamiento = 250

    for categoria, archivos in fragmentos_por_bloque.items():
        if not archivos: continue
        
        print(f"🎵 Procesando bloque: {categoria}...")
        
        voces_bloque = AudioSegment.empty()
        for i, f in enumerate(archivos):
            try:
                segmento = AudioSegment.from_mp3(f)
                if i == 0:
                    voces_bloque = segmento
                else:
                    voces_bloque = voces_bloque.append(segmento, crossfade=ms_solapamiento)
            except: continue
        
        ruta_musica = Config.SINTONIAS.get(categoria, Config.RUTA_SINTONIA)
        try:
            if os.path.exists(ruta_musica):
                musica = AudioSegment.from_mp3(ruta_musica)
                vol_fondo = -28
                vol_rafaga = -12
                
                if len(musica) < len(voces_bloque):
                    musica = musica * (len(voces_bloque) // len(musica) + 1)
                
                musica = musica[:len(voces_bloque) + 2000]
                rafaga = musica[:2000] + vol_rafaga
                fondo = musica[2000:] + vol_fondo
                musica_final = (rafaga + fondo).fade_out(3000)
                
                bloque_mezclado = musica_final.overlay(voces_bloque, position=500)
            else:
                bloque_mezclado = voces_bloque
        except:
            bloque_mezclado = voces_bloque
            
        if len(podcast_completo) == 0:
            podcast_completo = bloque_mezclado
        else:
            podcast_completo = podcast_completo.append(bloque_mezclado, crossfade=1000)

    # --- FASE DE MASTERING ---
    podcast_final = aplicar_mastering_pro(podcast_completo)

    # 4. Exportar y limpiar
    podcast_final.export(archivo_salida, format="mp3", bitrate="192k", tags={"artist": "NoticIA", "album": "Podcast Diario"})
    
    for cat in fragmentos_por_bloque:
        for f in fragmentos_por_bloque[cat]:
            try: os.remove(f)
            except: pass
            
    print(f"✅ ¡MASTERING COMPLETADO! Podcast listo para subir: {archivo_salida}")

def ensamblar_podcast(fragmentos, archivo_salida="noticIA_final.mp3"):
    ensamblar_podcast_dinamico({'espana': fragmentos}, archivo_salida)
