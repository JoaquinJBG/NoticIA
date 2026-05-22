# Diseño: Ingesta multifuente con contraste para neutralidad

**Fecha:** 2026-05-22
**Estado:** Aprobado (pendiente de plan de implementación)
**Alcance:** Reescritura del paso de ingesta de NoticIA. NO incluye cambios en `generador.py` (fase posterior).

---

## 1. Objetivo

Transformar la ingesta actual —que recoge titulares sueltos por categoría— en un sistema que:

1. Recoja noticias de **muchas fuentes** diversas.
2. **Detecte cuándo varios medios cubren el mismo hecho** y los agrupe.
3. Entregue esos grupos al generador para que construya una versión **políticamente neutral por contraste**.

La neutralidad se logra por **pluralidad de fuentes + contraste a ciegas de la IA**. No se etiquetan medios por orientación política.

Categorías donde NO aplica la neutralidad (Friki, Fútbol) mantienen el comportamiento actual de titulares sueltos.

---

## 2. Decisiones de diseño (cerradas)

| Decisión | Elección |
|----------|----------|
| Mecanismo de contraste | Agrupar la misma noticia entre medios; la IA contrasta cada grupo |
| Alcance del agrupamiento | España, Geopolítica, Ciencia, IA. Friki y Fútbol quedan simples |
| Estrategia de fuentes | Lista curada amplia (RSS) + Google News RSS por sección |
| Método de agrupamiento | Léxico ligero con `rapidfuzz` (sin embeddings ni LLM) |
| Etiquetas de orientación | NO se usan |
| Cambios en `generador.py` | Fuera de alcance (fase posterior) |

---

## 3. Arquitectura

La ingesta (hoy todo en `src/ingesta.py`) se divide en tres unidades con responsabilidad única:

```
src/fuentes.py     → Catálogo de feeds curados + constructores de URLs de Google News.
src/ingesta.py     → Descarga paralela, limpieza, recencia, dedup. Devuelve pool de artículos por categoría.
src/agrupador.py   → Agrupamiento léxico de artículos en clusters de "mismo hecho".
```

Flujo de datos:

```
fuentes.py (catálogo)
        │
        ▼
ingesta.py  ──►  pool de artículos por categoría  (limpios, recientes, sin duplicados)
        │
        ▼
agrupador.py ──► estructura final por categoría
        │
        ▼
generador.py (consumidor; se adapta en fase posterior)
```

---

## 4. Componentes

### 4.1 `src/fuentes.py`

Responsabilidad: declarar de dónde se obtiene la información. Sin lógica de red.

- `FEEDS_CURADOS`: dict `categoria -> [url, ...]`. Amplía la lista actual a ~25-40 medios
  (incluye izquierda, centro, derecha, internacionales y estatales para garantizar pluralidad),
  **sin** metadato de orientación.
- `SECCIONES_GOOGLE_NEWS`: dict `categoria -> [seccion, ...]` mapeando categorías a secciones de
  Google News (Nación, Mundo, Ciencia, Tecnología).
- `url_google_news(seccion_o_query)`: construye la URL de Google News RSS en español de España
  (`hl=es&gl=ES&ceid=ES:es`). Soporta tanto feeds de sección como búsquedas por término.
- `categorias_con_contraste()`: helper que devuelve `{"espana", "geopolitica", "ciencia", "ia_y_actualidad"}`.

### 4.2 `src/ingesta.py`

Responsabilidad: obtener y normalizar artículos. No agrupa.

- `obtener_pool() -> dict[str, list[Articulo]]`:
  - Reúne, por categoría, las URLs de `FEEDS_CURADOS` + las de Google News.
  - Descarga **en paralelo** con un **timeout por feed** (un feed colgado no bloquea la ejecución).
  - Por cada entrada construye un `Articulo` con `titular`, `resumen`, `fuente`, `url`, `fecha`.
  - **Limpieza de HTML real**: elimina etiquetas y desescapa entidades (no el `split('<')` actual).
  - **Filtro de recencia**: descarta entradas con fecha de publicación anterior a una ventana
    configurable (por defecto 48h). Entradas sin fecha fiable se conservan (no se descartan por defecto).
  - **Dedup**: elimina artículos con URL idéntica o titular idéntico tras normalización.
- `Articulo`: estructura ligera (dataclass o dict tipado) con los campos anteriores.

### 4.3 `src/agrupador.py`

Responsabilidad: agrupar artículos del mismo hecho. Solo lógica, sin red.

- `agrupar(pool) -> dict[str, ...]`:
  - Para categorías **con contraste**: agrupa los artículos por **similitud léxica de titulares**
    (`rapidfuzz`, normalizando acentos/mayúsculas/stopwords; refuerzo por entidades/palabras clave
    compartidas). Devuelve clusters.
    - Cada cluster: `{"tema": <titular representativo o keywords>, "articulos": [Articulo, ...]}`.
    - Clusters ordenados priorizando los de **≥2 fuentes distintas** (más contrastables).
    - Artículos sueltos (1 sola fuente) se conservan como clusters de tamaño 1 al final.
  - Para categorías **simples** (friki, futbol): devuelve la lista plana de artículos, sin clustering.

---

## 5. Estructura de salida (contrato con el generador)

```python
{
  # Categorías con contraste:
  "espana": {
    "clusters": [
      {
        "tema": "reforma laboral",
        "articulos": [
          {"titular": "...", "resumen": "...", "fuente": "elpais.com", "url": "...", "fecha": "..."},
          {"titular": "...", "resumen": "...", "fuente": "abc.es",     "url": "...", "fecha": "..."},
        ]
      },
      ...
    ]
  },
  "geopolitica": { "clusters": [...] },
  "ciencia":     { "clusters": [...] },
  "ia_y_actualidad": { "clusters": [...] },

  # Categorías simples (formato actual, lista plana):
  "friki":  [ {"titular": "...", "resumen": "...", "fuente": "..."}, ... ],
  "futbol": [ {"titular": "...", "resumen": "...", "fuente": "..."}, ... ],
}
```

Nota: el generador actual espera listas planas en todas las categorías. La adaptación del
generador a este nuevo contrato es **fase posterior** y queda fuera de este spec. Para no romper
la producción mientras tanto, el plan de implementación decidirá la estrategia de transición
(p. ej. feature flag o función puente).

---

## 6. Manejo de errores

- **Feed inaccesible / timeout**: se registra (logging) y se omite ese feed; el resto continúa.
- **Entrada malformada** (sin título, sin resumen): se omite la entrada concreta, no el feed.
- **Sin fecha de publicación**: se conserva el artículo (no se descarta por recencia).
- **Categoría sin artículos tras filtros**: devuelve estructura vacía válida (`{"clusters": []}` o `[]`),
  no lanza excepción.
- Se sustituyen los `except:` desnudos por `except Exception as e:` con mensaje de log.
- Se introduce el módulo `logging` (sustituye `print`); preparado para escribir a `produccion.log`.

---

## 7. Dependencias

- **Nueva:** `rapidfuzz` (agrupamiento léxico; ligera, sin descargas de modelos).
- **Se mantiene:** `feedparser`.
- **A eliminar de `requirements.txt`:** `asyncio` (es stdlib; el paquete PyPI puede romper el entorno).
- Limpieza de HTML con stdlib (`html.unescape` + stripping de tags) o utilidad ligera; sin añadir
  dependencias pesadas.

---

## 8. Pruebas

- `agrupador`: tests unitarios deterministas con artículos de ejemplo —
  - títulos casi idénticos de fuentes distintas → mismo cluster;
  - títulos no relacionados → clusters distintos;
  - categoría simple → lista plana sin agrupar.
- `ingesta`: tests de limpieza de HTML, dedup y filtro de recencia con entradas simuladas
  (sin red real; feeds mockeados).
- `fuentes`: test de que `url_google_news` produce URLs bien formadas en español de España.

---

## 9. Fuera de alcance

- Cambios en `generador.py`, `locutor.py`, `editor.py`.
- Sustituir Groq por Claude como cerebro del guion (posible fase futura; el usuario tiene Claude Max).
- Embeddings semánticos o agrupamiento por LLM.
- Etiquetado de medios por orientación política.
