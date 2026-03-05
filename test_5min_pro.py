import asyncio
import os
from src.ingesta import obtener_noticias
from src.generador import generar_intro, construir_bloque, generar_outro
from src.locutor import procesar_guion_a_audio
from src.editor import ensamblar_podcast

async def prueba_5min_pro():
    print("🧪 INICIANDO PRUEBA DE 5 MINUTOS (Motor: Groq - Llama 3.3 70B)")
    
    # 1. Ingesta de noticias real (solo usaremos una categoría para la prueba)
    print("📡 Obteniendo noticias reales...")
    todas_las_noticias = obtener_noticias()
    noticias_prueba = {"espana": todas_las_noticias.get("espana", [])[:3]} # Solo 3 noticias de España
    
    # 2. Generación de guion estructurado
    print("🧠 Generando guion con Groq/Llama (esto debería ser muy rápido)...")
    
    # Intro
    intro = generar_intro(noticias_prueba)
    print("✅ Intro generada.")
    
    # Bloque de España (le pediremos que sea un poco más corto para la prueba de 5 min)
    bloque_espana = construir_bloque("espana", noticias_prueba["espana"])
    print("✅ Bloque de noticias generado.")
    
    # Outro
    outro = generar_outro()
    print("✅ Outro generado.")
    
    guion_final = f"{intro}\n\n{bloque_espana}\n\n{outro}"
    
    # 3. Locución
    print("🎙️ Convirtiendo a audio (voces realistas)...")
    archivos_temp = await procesar_guion_a_audio(guion_final)
    
    # 4. Montaje
    if archivos_temp:
        archivo_final = "output/test_5min_pro.mp3"
        os.makedirs("output", exist_ok=True)
        ensamblar_podcast(archivos_temp, archivo_final)
        print(f"\n✨ PRUEBA FINALIZADA: {archivo_final}")
        print("Este archivo debería durar entre 5 y 8 minutos con la nueva estructura y calidad Pro.")
    else:
        print("❌ Error: No se generaron audios.")

if __name__ == "__main__":
    asyncio.run(prueba_5min_pro())
