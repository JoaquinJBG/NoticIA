from pydub import AudioSegment
import os
from src.config import Config

def ensamblar_podcast_dinamico(fragmentos_por_bloque, archivo_salida="noticIA_final.mp3"):
    """
    fragmentos_por_bloque: dict { 'intro': [f1, f2], 'espana': [f3, f4], ... }
    """
    if not fragmentos_por_bloque:
        print("❌ No hay fragmentos para unir.")
        return

    print("🎬 Iniciando montaje dinámico con música por categorías...")
    podcast_completo = AudioSegment.empty()
    ms_solapamiento = 250

    for categoria, archivos in fragmentos_por_bloque.items():
        if not archivos: continue
        
        print(f"🎵 Procesando bloque: {categoria}...")
        
        # 1. Unir voces del bloque con solapamiento
        voces_bloque = AudioSegment.empty()
        for i, f in enumerate(archivos):
            segmento = AudioSegment.from_mp3(f)
            if i == 0:
                voces_bloque = segmento
            else:
                voces_bloque = voces_bloque.append(segmento, crossfade=ms_solapamiento)
        
        # 2. Cargar música de la categoría
        ruta_musica = Config.SINTONIAS.get(categoria, Config.RUTA_SINTONIA)
        try:
            if os.path.exists(ruta_musica):
                musica = AudioSegment.from_mp3(ruta_musica)
                
                # Efecto Ráfaga: Música alta al principio (2 seg) y luego baja
                vol_fondo = -28
                vol_rafaga = -12
                
                # Repetir música si es corta
                if len(musica) < len(voces_bloque):
                    musica = musica * (len(voces_bloque) // len(musica) + 1)
                
                musica = musica[:len(voces_bloque) + 2000]
                
                # Crear la ráfaga (primeros 2 segundos más altos)
                rafaga = musica[:2000] + vol_rafaga
                fondo = musica[2000:] + vol_fondo
                musica_final = rafaga + fondo
                
                musica_final = musica_final.fade_out(3000)
                bloque_mezclado = musica_final.overlay(voces_bloque, position=500)
            else:
                bloque_mezclado = voces_bloque
        except Exception as e:
            print(f"⚠️ Error música en {categoria}: {e}")
            bloque_mezclado = voces_bloque
            
        # 3. Añadir bloque al podcast completo
        if len(podcast_completo) == 0:
            podcast_completo = bloque_mezclado
        else:
            # Transición suave entre bloques
            podcast_completo = podcast_completo.append(bloque_mezclado, crossfade=1000)

    # 4. Exportar y limpiar
    podcast_completo.export(archivo_salida, format="mp3", bitrate="192k")
    
    for cat in fragmentos_por_bloque:
        for f in fragmentos_por_bloque[cat]:
            try: os.remove(f)
            except: pass
            
    print(f"✅ ¡Podcast Profesional terminado! {archivo_salida}")

def ensamblar_podcast(fragmentos, archivo_salida="noticIA_final.mp3"):
    """Mantener compatibilidad básica para pruebas simples"""
    from src.editor import ensamblar_podcast_dinamico
    ensamblar_podcast_dinamico({'espana': fragmentos}, archivo_salida)
