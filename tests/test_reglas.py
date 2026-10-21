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
    assert "jaja" in entretenimiento
    assert "(risas)" in entretenimiento
