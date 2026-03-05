import os
from groq import Groq
from src.config import Config

# Configuramos el cliente de Groq
if not Config.GROQ_API_KEY:
    raise ValueError("❌ No se encontró la GROQ_API_KEY. Revisa tu archivo .env")

client = Groq(api_key=Config.GROQ_API_KEY)
MODELO_GROQ = "llama-3.3-70b-versatile"

def construir_guion(datos_noticias):
    guion_completo = ""

    # 1. Generar la INTRO con sumario
    print(f"🎙️ Generando Introducción (Groq - {MODELO_GROQ})...")
    guion_completo += generar_intro(datos_noticias)
    guion_completo += "\n\n"

    # 2. Bloques de noticias
    categorias = ["espana", "geopolitica", "ia_y_actualidad", "ciencia", "friki", "futbol"]
    for cat in categorias:
        if cat in datos_noticias and datos_noticias[cat]:
            print(f"🧠 Generando bloque de tertulia: {cat.upper()}...")
            guion_completo += construir_bloque(cat, datos_noticias[cat])
            guion_completo += "\n\n"

    # 3. Generar el OUTRO
    print("🎙️ Generando Despedida...")
    guion_completo += generar_outro()

    return guion_completo

def llamar_ia(system_prompt, user_prompt):
    try:
        completion = client.chat.completions.create(
            model=MODELO_GROQ,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.85, # Mayor creatividad para evitar bucles
            max_tokens=4096
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Error llamando a Groq: {e}")
        return ""

def generar_intro(datos_noticias):
    titulares = []
    for cat in datos_noticias:
        if datos_noticias[cat]:
            titulares.append(datos_noticias[cat][0]["titular"])
    
    resumen_titulares = "\n".join(titulares[:3])

    prompt_sistema = Config.get_prompt_sistema()
    prompt_usuario = f"""
    TAREA: Genera la introducción del podcast.
    ESTRUCTURA:
    1. Saludo enérgico y carismático de Álex y Santi.
    2. Presentación de los 3 temas estrella:
    {resumen_titulares}
    3. Gancho final.
    DURACIÓN: Unos 2 minutos de charla.
    """
    
    texto = llamar_ia(prompt_sistema, prompt_usuario)
    if texto:
        # Limpieza profunda de Markdown
        return texto.replace("**", "").replace("__", "").replace("###", "").replace("*", "").strip()
    return "Álex: ¡Bienvenidos! \nSanti: ¡Hola a todos!"

def generar_outro():
    prompt_sistema = Config.get_prompt_sistema()
    prompt_usuario = "TAREA: Genera la despedida del podcast. Resumen breve, Call to Action y cierre con el nombre: NoticIA."
    
    texto = llamar_ia(prompt_sistema, prompt_usuario)
    if texto:
        # Limpieza profunda de Markdown
        return texto.replace("**", "").replace("__", "").replace("###", "").replace("*", "").strip()
    return "Álex: Gracias por escucharnos. \nSanti: ¡Hasta pronto!"

def construir_bloque(categoria, noticias):
    prompt_sistema = f"{Config.get_prompt_sistema()}\n\nCONTEXTO GENERAL:\n{Config.get_contexto()}"
    prompt_usuario = f"""
    BLOQUE ACTUAL: {categoria.upper()}
    INSTRUCCIONES CRÍTICAS: 
    - NO REPITAS frases como "Sí, es cierto", "Exacto", "Tienes razón" al inicio de cada frase.
    - VARÍA las transiciones y la estructura de las respuestas.
    - Charlad de forma apasionada y profunda sobre estas noticias durante 8-10 minutos. 
    - Bajad la noticia al suelo y aportad contexto real.
    
    NOTICIAS:
    {str(noticias)}
    """

    texto = llamar_ia(prompt_sistema, prompt_usuario)
    if texto:
        # Limpieza profunda de Markdown
        return texto.replace("**", "").replace("__", "").replace("###", "").replace("*", "").strip()
    return ""
