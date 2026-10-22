# Catálogo de fuentes

Las fuentes de cada bloque están en `src/noticia/fuentes.py` (`FEEDS_CURADOS`).

## Medios de titularidad estatal (D-07)

Se quita `globaltimes.cn` del catálogo hasta que el dueño verifique su titularidad.
Su carácter estatal no se ha comprobado en el repositorio. Si la verificación lo confirma,
la decisión se revisa antes de volver a añadirlo.

## Criterio de pluralidad (D-06)

Tope por medio y bloque, mínimo de temas distintos, trato de las noticias de fuente única,
mínimo de fuentes por noticia política, y si el fútbol se equilibra por equipo.

El tope por bloque es `noticias_por_bloque` (`src/noticia/config.py`), aplicado en
`src/noticia/seleccion.py`. Los demás puntos del criterio están pendientes de implementar.

## Guardia de dominios

`tests/test_fuentes.py` fija un mínimo de dominios distintos por bloque de contraste
(España 10, Geopolítica 5, IA y actualidad 4, Ciencia 4). Si un cambio de catálogo lo
baja, el test falla y hay que justificar la cifra nueva.
