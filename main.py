import asyncio
import os
from src.ingesta import obtener_noticias
from src.generador import construir_guion
from src.locutor import procesar_guion_a_audio
from src.editor import ensamblar_podcast

async def produccion_completa():
    print("--- 🎙️ INICIANDO PRODUCCIÓN DE NOTICIA ---")
    
    # Aseguramos que existan las carpetas necesarias
    os.makedirs("output", exist_ok=True)
    os.makedirs("temp", exist_ok=True)

    # 1. Obtener noticias reales de los RSS
    noticias = obtener_noticias()
    
    # 2. El LLM genera el diálogo entre Álex y Santi
    guion = construir_guion(noticias)
    print("📝 Guion generado con éxito.")
    
    # 3. Convertir cada línea de diálogo a audio (usando edge-tts)
    # Los fragmentos se guardarán en temp/ por defecto
    archivos_temp = await procesar_guion_a_audio(guion)
    
    # 4. Unir todos los fragmentos con la sintonía de fondo
    if archivos_temp:
        archivo_final = os.path.join("output", "noticIA_final.mp3")
        ensamblar_podcast(archivos_temp, archivo_final)
    else:
        print("❌ Error: No se generaron audios para ensamblar.")
    
    print(f"--- ✨ PODCAST FINALIZADO: {archivo_final} ---")

if __name__ == "__main__":
    asyncio.run(produccion_completa())