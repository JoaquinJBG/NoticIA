import os
from groq import Groq
from src.config import Config

# Configuramos el cliente de Groq
if not Config.GROQ_API_KEY:
    raise ValueError("❌ No se encontró la GROQ_API_KEY. Revisa tu archivo .env")

client = Groq(api_key=Config.GROQ_API_KEY)
MODELO_GROQ = "llama-3.3-70b-versatile"

def construir_guion(datos_noticias):
    guion_por_bloques = {}

    # 1. INTRO
    print(f"🎙️ Generando Introducción Profesional...")
    guion_por_bloques["intro"] = [generar_intro(datos_noticias)]

    # 2. BLOQUES DE NOTICIAS CON INVESTIGACIÓN
    categorias = ["espana", "geopolitica", "ia_y_actualidad", "ciencia", "friki", "futbol"]
    for cat in categorias:
        if cat in datos_noticias and datos_noticias[cat]:
            print(f"🔍 Investigando contexto para {cat.upper()}...")
            briefing = generar_briefing_contexto(cat, datos_noticias[cat])
            
            print(f"🧠 Generando tertulia con autoridad para {cat.upper()}...")
            texto_bloque = construir_bloque_con_contexto(cat, datos_noticias[cat], briefing)
            guion_por_bloques[cat] = [texto_bloque]

    # 3. OUTRO
    print("🎙️ Generando Despedida Profesional...")
    guion_por_bloques["outro"] = [generar_outro()]

    return guion_por_bloques

def llamar_ia(system_prompt, user_prompt, temperature=0.85):
    try:
        completion = client.chat.completions.create(
            model=MODELO_GROQ,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=4096
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Error llamando a Groq: {e}")
        return ""

def generar_briefing_contexto(categoria, noticias):
    """Fase de investigación: La IA busca en su 'memoria' datos extra"""
    prompt_sistema = "Eres un investigador experto y documentalista de podcasts de alto nivel."
    prompt_usuario = f"""
    Basándote en estas noticias de {categoria}:
    {str(noticias)}
    
    TAREA: Genera un BRIEFING DE INVESTIGACIÓN que incluya:
    1. Antecedentes históricos (¿Qué pasó antes de esto?).
    2. Curiosidades o datos poco conocidos relacionados.
    3. Una analogía con la cultura pop (cine, series, libros).
    4. Una pregunta "incómoda" o profunda para debatir.
    
    IMPORTANTE: No inventes hechos actuales, solo aporta contexto histórico y cultural real.
    """
    return llamar_ia(prompt_sistema, prompt_usuario, temperature=0.5)

def construir_bloque_con_contexto(categoria, noticias, briefing):
    prompt_sistema = f"{Config.get_prompt_sistema()}\n\nCONTEXTO GENERAL:\n{Config.get_contexto()}"
    prompt_usuario = f"""
    BLOQUE ACTUAL: {categoria.upper()}
    
    INVESTIGACIÓN DISPONIBLE (Úsala para dar autoridad a la charla):
    {briefing}
    
    NOTICIAS DEL DÍA:
    {str(noticias)}
    
    INSTRUCCIONES:
    - Álex debe usar los datos del BRIEFING para sonar como un experto mentor.
    - Santi debe reaccionar a las curiosidades y analogías.
    - Evitad repeticiones robóticas. Charlad durante 8-10 minutos de forma apasionada.
    """
    
    texto = llamar_ia(prompt_sistema, prompt_usuario)
    if texto:
        return texto.replace("**", "").replace("__", "").replace("###", "").replace("*", "").strip()
    return ""

def generar_intro(datos_noticias):
    titulares = []
    for cat in datos_noticias:
        if datos_noticias[cat]:
            titulares.append(datos_noticias[cat][0]["titular"])
    
    resumen_titulares = "\n".join(titulares[:3])
    prompt_sistema = Config.get_prompt_sistema()
    prompt_usuario = f"TAREA: Genera la introducción con este sumario de temas: {resumen_titulares}. Saludo carismático y hook inicial."
    
    texto = llamar_ia(prompt_sistema, prompt_usuario)
    if texto:
        return texto.replace("**", "").replace("__", "").replace("###", "").replace("*", "").strip()
    return "Álex: ¡Bienvenidos! \nSanti: ¡Hola a todos!"

def generar_outro():
    prompt_sistema = Config.get_prompt_sistema()
    prompt_usuario = "TAREA: Genera la despedida del podcast. Resumen breve, Call to Action y cierre: NoticIA."
    
    texto = llamar_ia(prompt_sistema, prompt_usuario)
    if texto:
        return texto.replace("**", "").replace("__", "").replace("###", "").replace("*", "").strip()
    return "Álex: Gracias por escucharnos. \nSanti: ¡Hasta pronto!"
