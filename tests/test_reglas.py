from noticia.bloques import NOMBRE_BLOQUE, ORDEN_BLOQUES
from noticia.config import ROOT

CONTEXTO = (ROOT / "reglas" / "contexto.md").read_text(encoding="utf-8")
INSTRUCCIONES = (ROOT / "reglas" / "instrucciones.md").read_text(encoding="utf-8")


def _seccion(texto: str, inicio: str, fin: str) -> str:
    return texto.split(inicio, 1)[1].split(fin, 1)[0]


def test_contexto_no_contiene_texto_de_chat():
    minusculas = CONTEXTO.lower()
    for fragmento in ("te paso", "conversaci", "siguiente paso"):
        assert fragmento not in minusculas


def test_contexto_no_ordena_juzgar_medios_ni_menciona_fuentes_retiradas():
    minusculas = CONTEXTO.lower()
    for fragmento in ("sesgos mediáticos", "global times", "biohacking"):
        assert fragmento not in minusculas


def test_estructura_de_contexto_usa_los_bloques_del_codigo():
    estructura = _seccion(CONTEXTO, "Estructura del Guion:", "Reglas de Estilo:")
    nombres = [linea.strip() for linea in estructura.splitlines() if linea.strip()]
    assert nombres == [NOMBRE_BLOQUE[clave] for clave in ORDEN_BLOQUES]


def test_instrucciones_prohibe_risas_escritas():
    entretenimiento = _seccion(INSTRUCCIONES, "# PAUTAS DE ENTRETENIMIENTO", "# ESTILO").lower()
    reglas = [linea for linea in entretenimiento.splitlines() if "jaja" in linea]
    assert len(reglas) == 1
    assert "prohibido" in reglas[0]
    assert "(risas)" in reglas[0]


D02 = (
    "Los locutores comentan la actualidad sin tomar partido. Cuando un tema divide a la opinión "
    "pública, presentan las posturas de cada parte atribuyéndolas a quien las sostiene, sin "
    "adjetivos valorativos sobre actores políticos. No dan veredictos sobre hechos en disputa; "
    "un hecho comprobado se presenta con su fuente."
)
D08 = "María es experta en tecnología, Nintendo y Pokémon"
D10 = (
    "En temas de salud se citan solo fuentes oficiales o de organismos profesionales, "
    "y no se dan recomendaciones médicas personales."
)


def test_instrucciones_contiene_politica_de_neutralidad_literal():
    assert D02 in INSTRUCCIONES
    assert "antes de opinar" not in INSTRUCCIONES


def test_instrucciones_contiene_politica_de_salud_literal():
    assert D10 in INSTRUCCIONES


def test_contexto_contiene_ficha_de_maria_literal():
    assert D08 in CONTEXTO
