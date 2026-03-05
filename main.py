import asyncio
import os
from src.ingesta import obtener_noticias
from src.generador import construir_guion
from src.locutor import procesar_guion_a_audio
from src.editor import ensamblar_podcast_dinamico

async def produccion_completa_pro():
    print("--- 🎙️ INICIANDO PRODUCCIÓN DE NOTICIA: PROFESSIONAL EDITION ---")
    
    # 1. Aseguramos que existan las carpetas necesarias
    os.makedirs("output", exist_ok=True)
    os.makedirs("temp", exist_ok=True)

    # 2. Obtener noticias reales de los RSS actualizados (incluye Anime, Nintendo, Pokemon)
    print("📡 Capturando noticias de todas las fuentes...")
    noticias = obtener_noticias()
    
    # 3. El LLM genera el diálogo con investigación y estructura pro
    # Devuelve un dict: {'intro': [txt], 'espana': [txt], ...}
    print("🧠 Generando guion inteligente por bloques (esto puede tardar unos minutos)...")
    guion_por_bloques = construir_guion(noticias)
    
    # 4. Convertir cada línea de diálogo a audio (usando edge-tts + rate/pitch realista)
    # Los fragmentos se guardarán en temp/
    print("🎙️ Iniciando locución de voces realistas...")
    fragmentos_audio_por_bloque = {}
    
    for categoria, lineas in guion_por_bloques.items():
        if not lineas: continue
        print(f"🎬 Procesando locución del bloque: {categoria}...")
        # Unimos las líneas del bloque en un solo string para el locutor
        texto_bloque = "\n".join(lineas)
        fragmentos_audio_por_bloque[categoria] = await procesar_guion_a_audio(texto_bloque)
    
    # 5. Unir todos los fragmentos con diseño sonoro dinámico y mastering pro
    if fragmentos_audio_por_bloque:
        archivo_final = os.path.join("output", "NoticIA_PRO_Final.mp3")
        print("🎬 Iniciando montaje dinámico y mastering final...")
        ensamblar_podcast_dinamico(fragmentos_audio_por_bloque, archivo_final)
        print(f"\n--- ✨ PODCAST PROFESIONAL FINALIZADO: {archivo_final} ---")
    else:
        print("❌ Error: No se generaron audios para ensamblar.")

if __name__ == "__main__":
    asyncio.run(produccion_completa_pro())
