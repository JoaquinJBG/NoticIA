import logging
import re
from collections.abc import Callable
from datetime import date

from noticia.bloques import CATEGORIAS_NOTICIAS
from noticia.config import get_contexto, get_prompt_sistema, settings
from noticia.fechas import formatear_fecha_larga, hoy_madrid
from noticia.motor_claude import generar_texto
from noticia.personajes import Reparto, reparto_para_fecha
from noticia.seleccion import formatear_noticias_prompt

logger = logging.getLogger("noticia.generador")

# Encabezados markdown ("# Bloque") y reglas horizontales ("---"): no son
# diálogo, y el locutor los leería en voz alta.
_ENCABEZADO_O_REGLA = re.compile(r"^\s{0,3}(#{1,6}\s|-{3,}\s*$|\*{3,}\s*$)")
_SALTOS_DE_MAS = re.compile(r"\n{3,}")


def _limpiar_markdown(texto: str) -> str:
    """Deja solo el diálogo: fuera encabezados, reglas y marcas de énfasis."""
    lineas = [ln for ln in texto.splitlines() if not _ENCABEZADO_O_REGLA.match(ln)]
    limpio = "\n".join(lineas)
    for marca in ("**", "__", "*"):
        limpio = limpio.replace(marca, "")
    return _SALTOS_DE_MAS.sub("\n\n", limpio).strip()


def _con_reintento(fn: Callable[[], str], reintentos: int | None = None) -> str:
    """Reintenta `fn()` mientras devuelva una cadena vacía.

    Hace como mucho `reintentos` reintentos (además del intento inicial),
    usando `settings.reintentos_guion` si no se indica otro valor.
    """
    total_intentos = (reintentos if reintentos is not None else settings.reintentos_guion) + 1
    resultado = ""
    for intento in range(total_intentos):
        resultado = fn()
        if resultado:
            return resultado
        if intento < total_intentos - 1:
            logger.warning(
                "Respuesta vacía de la IA, reintentando (%s/%s)...",
                intento + 1,
                total_intentos - 1,
            )
    return resultado


def _texto_reparto(reparto: Reparto) -> str:
    """Aviso de quién habla hoy; se añade al prompt de sistema."""
    texto = f"REPARTO DE HOY: {', '.join(reparto.nombres)}. Solo hablan estas personas."
    if reparto.hay_invitada:
        texto += (
            f" Hoy {reparto.nombres[reparto.locutores.index('invitada')]} es la invitada del "
            "episodio: preséntala en la intro y trátala como invitada, no como presentadora fija."
        )
    return texto


def _prompt_sistema(reparto: Reparto, con_contexto: bool = False) -> str:
    sistema = f"{get_prompt_sistema(reparto)}\n\n{_texto_reparto(reparto)}"
    if con_contexto:
        sistema += f"\n\nCONTEXTO GENERAL:\n{get_contexto()}"
    return sistema


def construir_guion(
    datos_noticias, fecha: date | None = None, reparto: Reparto | None = None
) -> dict[str, list[str]]:
    fecha = fecha or hoy_madrid()
    reparto = reparto or reparto_para_fecha(fecha)
    guion_por_bloques = {}

    # 1. INTRO
    logger.info("Generando Introducción Profesional...")
    guion_por_bloques["intro"] = [generar_intro(datos_noticias, fecha, reparto)]

    # 2. BLOQUES DE NOTICIAS CON INVESTIGACIÓN
    for cat in CATEGORIAS_NOTICIAS:
        if datos_noticias.get(cat):
            logger.info("Investigando contexto para %s...", cat.upper())
            briefing = generar_briefing_contexto(cat, datos_noticias[cat], fecha)

            logger.info("Generando tertulia con autoridad para %s...", cat.upper())
            texto_bloque = construir_bloque_con_contexto(
                cat, datos_noticias[cat], briefing, fecha, reparto
            )
            guion_por_bloques[cat] = [texto_bloque]

    # 3. OUTRO, con los titulares reales para que no se los invente
    titulares = [
        datos_noticias[cat][0]["titular"] for cat in CATEGORIAS_NOTICIAS if datos_noticias.get(cat)
    ]
    logger.info("Generando Despedida Profesional...")
    guion_por_bloques["outro"] = [generar_outro(titulares, fecha, reparto)]

    return guion_por_bloques


def llamar_ia(system_prompt, user_prompt):
    return generar_texto(system_prompt, user_prompt)


def generar_briefing_contexto(categoria, noticias, fecha: date | None = None) -> str:
    """Fase de investigación: La IA busca en su 'memoria' datos extra"""
    fecha_texto = formatear_fecha_larga(fecha or hoy_madrid())
    prompt_sistema = "Eres un investigador experto y documentalista de podcasts de alto nivel."
    prompt_usuario = f"""
    Hoy es {fecha_texto}.

    Basándote en estas noticias de {categoria}:
    {formatear_noticias_prompt(noticias)}

    TAREA: Genera un BRIEFING DE INVESTIGACIÓN que incluya:
    1. Antecedentes históricos (¿Qué pasó antes de esto?).
    2. Curiosidades o datos poco conocidos relacionados.
    3. Una analogía con la cultura pop (cine, series, libros).
    4. Una pregunta "incómoda" o profunda para debatir.

    IMPORTANTE: No inventes hechos actuales, solo aporta contexto histórico y cultural real.
    """
    return _con_reintento(lambda: llamar_ia(prompt_sistema, prompt_usuario))


def construir_bloque_con_contexto(
    categoria, noticias, briefing, fecha: date | None = None, reparto: Reparto | None = None
) -> str:
    fecha = fecha or hoy_madrid()
    reparto = reparto or reparto_para_fecha(fecha)
    fecha_texto = formatear_fecha_larga(fecha)
    prompt_sistema = _prompt_sistema(reparto, con_contexto=True)
    prompt_usuario = f"""
    Hoy es {fecha_texto}.

    BLOQUE ACTUAL: {categoria.upper()}

    INVESTIGACIÓN DISPONIBLE (Úsala para dar autoridad a la charla):
    {briefing}

    NOTICIAS DEL DÍA:
    {formatear_noticias_prompt(noticias)}

    INSTRUCCIONES:
    - Cada personaje habla según su perfil: usad los datos del BRIEFING como munición
      para opinar, no para dar una clase.
    - Ritmo vivo: frases cortas, interrupciones breves, humor y opiniones claras.
    - Evitad repeticiones robóticas. Charlad durante 8-10 minutos de forma apasionada.
    - DESCARTAD sin comentarla cualquier noticia de la lista que en realidad sea
      publicidad, una promoción, un cupón de descuento o contenido comercial, o
      que no tenga interés real para una audiencia española: no forméis parte de
      su promoción.

    FORMATO DE RESPUESTA (obligatorio):
    - Responde ÚNICAMENTE con el diálogo, empezando directamente por {reparto.prefijos_texto}.
    - Sin preámbulo, sin explicar lo que vas a hacer, sin resumen final.
    - Sin encabezados, sin markdown, sin separadores.
    """

    texto = _con_reintento(lambda: llamar_ia(prompt_sistema, prompt_usuario))
    if texto:
        return _limpiar_markdown(texto)
    return ""


def generar_intro(datos_noticias, fecha: date | None = None, reparto: Reparto | None = None) -> str:
    fecha = fecha or hoy_madrid()
    reparto = reparto or reparto_para_fecha(fecha)
    titulares = []
    for cat in CATEGORIAS_NOTICIAS:
        if datos_noticias.get(cat):
            titulares.append(datos_noticias[cat][0]["titular"])

    resumen_titulares = "\n".join(titulares[:3])
    fecha_texto = formatear_fecha_larga(fecha)
    prompt_sistema = _prompt_sistema(reparto)
    prompt_usuario = (
        f"Hoy es {fecha_texto}. "
        f"TAREA: Genera la introducción con este sumario de temas: {resumen_titulares}. "
        "Saludo carismático y hook inicial. "
        "Responde ÚNICAMENTE con el diálogo, sin preámbulo ni markdown."
    )

    texto = _con_reintento(lambda: llamar_ia(prompt_sistema, prompt_usuario))
    if texto:
        return _limpiar_markdown(texto)
    primero, segundo = reparto.nombres
    return f"{primero}: ¡Bienvenidos! \n{segundo}: ¡Hola a todos!"


def generar_outro(
    titulares: list[str] | None = None,
    fecha: date | None = None,
    reparto: Reparto | None = None,
) -> str:
    fecha = fecha or hoy_madrid()
    reparto = reparto or reparto_para_fecha(fecha)
    resumen_titulares = "\n".join(titulares or [])
    fecha_texto = formatear_fecha_larga(fecha)
    prompt_sistema = _prompt_sistema(reparto)
    prompt_usuario = (
        f"Hoy es {fecha_texto}. "
        "TAREA: Genera la despedida del podcast, recordando brevemente estos titulares "
        f"reales de hoy (no os inventéis otros):\n{resumen_titulares}\n"
        "Resumen breve, Call to Action y cierre: NoticIA. "
        "Responde ÚNICAMENTE con el diálogo, sin preámbulo ni markdown."
    )

    texto = _con_reintento(lambda: llamar_ia(prompt_sistema, prompt_usuario))
    if texto:
        return _limpiar_markdown(texto)
    primero, segundo = reparto.nombres
    return f"{primero}: Gracias por escucharnos. \n{segundo}: ¡Hasta pronto!"
