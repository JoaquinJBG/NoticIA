import logging

from noticia.config import get_contexto, get_prompt_sistema
from noticia.motor_claude import generar_texto

logger = logging.getLogger("noticia.generador")


def construir_guion(datos_noticias):
    guion_por_bloques = {}

    # 1. INTRO
    logger.info("Generando Introducción Profesional...")
    guion_por_bloques["intro"] = [generar_intro(datos_noticias)]

    # 2. BLOQUES DE NOTICIAS CON INVESTIGACIÓN
    categorias = ["espana", "geopolitica", "ia_y_actualidad", "ciencia", "friki", "futbol"]
    for cat in categorias:
        if cat in datos_noticias and datos_noticias[cat]:
            logger.info("Investigando contexto para %s...", cat.upper())
            briefing = generar_briefing_contexto(cat, datos_noticias[cat])

            logger.info("Generando tertulia con autoridad para %s...", cat.upper())
            texto_bloque = construir_bloque_con_contexto(cat, datos_noticias[cat], briefing)
            guion_por_bloques[cat] = [texto_bloque]

    # 3. OUTRO
    logger.info("Generando Despedida Profesional...")
    guion_por_bloques["outro"] = [generar_outro()]

    return guion_por_bloques


def llamar_ia(system_prompt, user_prompt):
    return generar_texto(system_prompt, user_prompt)


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
    return llamar_ia(prompt_sistema, prompt_usuario)


def construir_bloque_con_contexto(categoria, noticias, briefing):
    prompt_sistema = f"{get_prompt_sistema()}\n\nCONTEXTO GENERAL:\n{get_contexto()}"
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
    prompt_sistema = get_prompt_sistema()
    prompt_usuario = (
        f"TAREA: Genera la introducción con este sumario de temas: {resumen_titulares}. "
        "Saludo carismático y hook inicial."
    )

    texto = llamar_ia(prompt_sistema, prompt_usuario)
    if texto:
        return texto.replace("**", "").replace("__", "").replace("###", "").replace("*", "").strip()
    return "Álex: ¡Bienvenidos! \nSanti: ¡Hola a todos!"


def generar_outro():
    prompt_sistema = get_prompt_sistema()
    prompt_usuario = (
        "TAREA: Genera la despedida del podcast. Resumen breve, Call to Action y cierre: NoticIA."
    )

    texto = llamar_ia(prompt_sistema, prompt_usuario)
    if texto:
        return texto.replace("**", "").replace("__", "").replace("###", "").replace("*", "").strip()
    return "Álex: Gracias por escucharnos. \nSanti: ¡Hasta pronto!"
