import asyncio
import os
from src.generador import llamar_ia, generar_briefing_contexto
from src.locutor import procesar_guion_a_audio
from src.editor import ensamblar_podcast_dinamico
from src.config import Config

# Mock de noticias para que el test sea rápido y predecible
NOTICIAS_TEST = {
    "geopolitica": [
        {
            "titular": "Tensiones en el Mar Rojo afectan el comercio global",
            "resumen": "Los recientes ataques a buques de carga han obligado a las navieras a desviar sus rutas por el Cabo de Buena Esperanza, aumentando costes y tiempos de entrega.",
            "fuente": "reuters.com"
        }
    ],
    "friki": [
        {
            "titular": "Anunciado nuevo Pokémon Legends: Z-A",
            "resumen": "The Pokémon Company ha revelado un nuevo título de la saga Legends que tendrá lugar íntegramente en Ciudad Luminalia. El lanzamiento está previsto para 2025.",
            "fuente": "nintenderos.com"
        }
    ]
}

def construir_guion_test(datos_noticias):
    """Genera un guion optimizado para una duración total de ~5 minutos."""
    guion_por_bloques = {}

    # 1. INTRO (30-45 segundos)
    print("🎙️ Generando Introducción (Test 5min)...")
    prompt_sistema = Config.get_prompt_sistema()
    prompt_usuario = "TAREA: Genera una intro de 45 segundos. Álex y Santi saludan y presentan el programa especial de 5 minutos."
    guion_por_bloques["intro"] = [llamar_ia(prompt_sistema, prompt_usuario).strip()]

    # 2. BLOQUES (2 min cada uno aprox)
    for cat in ["geopolitica", "friki"]:
        print(f"🧠 Generando bloque {cat} (2 min)...")
        briefing = generar_briefing_contexto(cat, datos_noticias[cat])
        
        prompt_sistema = f"{Config.get_prompt_sistema()}\n\nCONTEXTO:\n{Config.get_contexto()}"
        prompt_usuario = f"""
        BLOQUE: {cat.upper()}
        INVESTIGACIÓN: {briefing}
        NOTICIAS: {str(datos_noticias[cat])}
        
        INSTRUCCIÓN DE TIEMPO: Hablad durante exactamente 2 MINUTOS. 
        Mantened un ritmo fluido y natural. Álex aporta el contexto y Santi la energía.
        """
        texto = llamar_ia(prompt_sistema, prompt_usuario)
        guion_por_bloques[cat] = [texto.strip() if texto else ""]

    # 3. OUTRO (30 segundos)
    print("🎙️ Generando Despedida (Test 5min)...")
    prompt_usuario = "TAREA: Genera un cierre de 30 segundos. Resumen rápido, recomendación final y despedida de NoticIA."
    guion_por_bloques["outro"] = [llamar_ia(prompt_sistema, prompt_usuario).strip()]

    return guion_por_bloques

async def test_produccion_5min():
    print("🚀 INICIANDO TEST DE PRODUCCIÓN (OBJETIVO: 5 MINUTOS) 🚀")
    
    os.makedirs("output", exist_ok=True)
    os.makedirs("temp", exist_ok=True)

    # Generamos guion con tiempos controlados
    guion = construir_guion_test(NOTICIAS_TEST)
    
    fragmentos_audio_por_bloque = {}
    
    for categoria, lineas in guion.items():
        if not lineas or not lineas[0]: continue
        print(f"🎙️ Locución: {categoria}...")
        texto_bloque = "\n".join(lineas)
        # Procesamos el audio (esto llamará a edge-tts)
        fragmentos_audio_por_bloque[categoria] = await procesar_guion_a_audio(texto_bloque)
    
    if fragmentos_audio_por_bloque:
        archivo_final = os.path.join("output", "TEST_5min_NoticIA.mp3")
        print("🎬 Ensamblando audio final...")
        ensamblar_podcast_dinamico(fragmentos_audio_por_bloque, archivo_final)
        print(f"\n✅ TEST COMPLETADO: {archivo_final}")
        print("Nota: El archivo debería durar aproximadamente 5 minutos.")
    else:
        print("❌ Error en la generación de fragmentos.")

if __name__ == "__main__":
    # Para ejecutarlo manualmente: python test_5min.py
    # Pero no lo ejecuto ahora como pediste.
    print("Test de 5 minutos preparado en test_5min.py")
