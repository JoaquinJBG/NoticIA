"""Bloques del episodio: orden de emisión y categorías de noticias."""

CATEGORIAS_NOTICIAS: tuple[str, ...] = (
    "espana",
    "geopolitica",
    "ia_y_actualidad",
    "ciencia",
    "friki",
    "futbol",
)

ORDEN_BLOQUES: tuple[str, ...] = ("intro", *CATEGORIAS_NOTICIAS, "outro")

NOMBRE_BLOQUE: dict[str, str] = {
    "espana": "España",
    "geopolitica": "Geopolítica",
    "ia_y_actualidad": "IA y actualidad",
    "ciencia": "Ciencia",
    "friki": "Friki",
    "futbol": "Fútbol",
    "intro": "Introducción",
    "outro": "Despedida",
}
