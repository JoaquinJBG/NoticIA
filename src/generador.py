import google.generativeai as genai
from src.config import Config

# Configuramos la API
if not Config.GEMINI_API_KEY:
    raise ValueError("❌ No se encontró la API Key. Revisa tu archivo .env")

genai.configure(api_key=Config.GEMINI_API_KEY)

def construir_guion(datos_noticias):
    guion_completo = ""

    # Lista de categorías a procesar secuencialmente
    categorias = ["espana", "geopolitica", "ia_y_actualidad", "ciencia", "friki", "futbol"]

    for cat in categorias:
        if cat in datos_noticias and datos_noticias[cat]:
            print(f"🧠 Generando bloque de tertulia: {cat.upper()}...")
            guion_completo += construir_bloque(cat, datos_noticias[cat])
            guion_completo += "\n\n" # Separación entre bloques

    return guion_completo

def construir_bloque(categoria, noticias):
    # Prompt específico para cada bloque para forzar la profundidad
    prompt_bloque = f"{Config.get_prompt_sistema()}\n\n"
    prompt_bloque += f"CONTEXTO GENERAL:\n{Config.get_contexto()}\n\n"
    prompt_bloque += f"BLOQUE ACTUAL: {categoria.upper()}\n"
    prompt_bloque += "INSTRUCCIONES DE DURACIÓN: Este bloque debe durar al menos 8-10 minutos de charla. "
    prompt_bloque += "No te limites a leer las noticias. Debatid sobre ellas, buscad el ángulo polémico, "
    prompt_bloque += "contad anécdotas personales relacionadas (puedes inventarlas para los personajes) y "
    prompt_bloque += "discutid sobre cómo afecta esto al futuro de España. Mojaros de verdad.\n\n"
    prompt_bloque += f"NOTICIAS DEL BLOQUE:\n{str(noticias)}"

    model = genai.GenerativeModel(
        model_name="gemini-flash-latest", 
        system_instruction=prompt_bloque
    )

    try:
        respuesta = model.generate_content("Empezad la tertulia sobre este bloque. Recordad: profundidad, debate y sin prisa.")
        texto = respuesta.text
        # Limpieza básica
        texto = texto.replace("**", "").replace("__", "").replace("###", "")
        return texto
    except Exception as e:
        print(f"❌ Error generando bloque {categoria}: {e}")
        return ""