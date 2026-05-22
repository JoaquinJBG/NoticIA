# Ingesta multifuente con contraste — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reescribir la ingesta de NoticIA para recoger noticias de muchas fuentes (lista curada + Google News RSS), agrupar léxicamente los artículos que cubren el mismo hecho en España/Geopolítica/Ciencia/IA, y devolver clusters para que el generador contraste a ciegas.

**Architecture:** Tres módulos con responsabilidad única: `src/fuentes.py` (catálogo de feeds + URLs de Google News), `src/ingesta.py` (descarga paralela con timeout, limpieza HTML, recencia, dedup) y `src/agrupador.py` (clustering léxico). `generador.py` NO se toca en este plan.

**Tech Stack:** Python 3.12, `feedparser`, `rapidfuzz` (nuevo), `concurrent.futures` (stdlib), `pytest` (nuevo, dev).

**Spec:** `docs/superpowers/specs/2026-05-22-ingesta-multifuente-contraste-design.md`

---

## File Structure

| Archivo | Responsabilidad |
|---------|-----------------|
| `src/fuentes.py` (crear) | Catálogo `FEEDS_CURADOS`, `SECCIONES_GOOGLE_NEWS`, `CATEGORIAS_CON_CONTRASTE`, builder `url_google_news` |
| `src/ingesta.py` (reescribir) | `limpiar_html`, `es_reciente`, `_parsear_entrada`, `_dedup`, `_descargar_feed`, `obtener_pool` |
| `src/agrupador.py` (crear) | `_normalizar`, `agrupar_categoria`, `agrupar` |
| `tests/` (crear) | Tests unitarios deterministas (sin red) |
| `requirements.txt` (modificar) | +`rapidfuzz`, +`pytest`; −`asyncio` |

**Contrato de artículo (dict):** `{"titular": str, "resumen": str, "fuente": str, "url": str, "fecha": time.struct_time | None}`

**Contrato de salida de `agrupar`:**
- Categorías con contraste: `{"clusters": [{"tema": str, "articulos": [art, ...]}, ...]}`
- Categorías simples (friki, futbol): `[art, ...]`

---

## Task 1: Setup de dependencias y tests

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `pytest.ini`

- [ ] **Step 1: Editar `requirements.txt`**

Quitar la línea `asyncio` (es stdlib; el paquete PyPI rompe entornos modernos) y añadir las nuevas dependencias. Resultado final del archivo:

```
feedparser==6.0.11
google-generativeai==0.8.3
groq==0.18.0
python-dotenv==1.0.1
edge-tts==6.1.12
pydub==0.25.1
rapidfuzz==3.9.7
pytest==8.3.4
```

- [ ] **Step 2: Crear `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 3: Crear `tests/__init__.py`** (archivo vacío)

```python
```

- [ ] **Step 4: Instalar dependencias**

Run: `.venv/bin/pip install rapidfuzz==3.9.7 pytest==8.3.4`
Expected: instalación correcta de ambos paquetes.

- [ ] **Step 5: Verificar que pytest arranca**

Run: `.venv/bin/python -m pytest -q`
Expected: `no tests ran` (sin errores de colección).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini tests/__init__.py
git commit -m "$(cat <<'EOF'
chore: setup de pytest y rapidfuzz para la nueva ingesta

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `src/fuentes.py` — catálogo y URLs de Google News

**Files:**
- Create: `src/fuentes.py`
- Test: `tests/test_fuentes.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_fuentes.py
from src import fuentes


def test_url_google_news_seccion():
    url = fuentes.url_google_news("WORLD")
    assert "/headlines/section/topic/WORLD" in url
    assert "hl=es" in url and "gl=ES" in url and "ceid=ES:es" in url


def test_url_google_news_busqueda():
    url = fuentes.url_google_news("reforma laboral", es_busqueda=True)
    assert "/search?q=reforma+laboral" in url
    assert "hl=es" in url


def test_categorias_con_contraste():
    assert fuentes.CATEGORIAS_CON_CONTRASTE == frozenset(
        {"espana", "geopolitica", "ciencia", "ia_y_actualidad"}
    )


def test_catalogos_cubren_todas_las_categorias():
    # friki y futbol solo en curados; las 4 de contraste en ambos catálogos
    for cat in fuentes.CATEGORIAS_CON_CONTRASTE:
        assert cat in fuentes.FEEDS_CURADOS
        assert cat in fuentes.SECCIONES_GOOGLE_NEWS
    assert "friki" in fuentes.FEEDS_CURADOS
    assert "futbol" in fuentes.FEEDS_CURADOS
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_fuentes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.fuentes'`.

- [ ] **Step 3: Implementar `src/fuentes.py`**

```python
from urllib.parse import quote_plus

_GN_BASE = "https://news.google.com/rss"
_GN_PARAMS = "hl=es&gl=ES&ceid=ES:es"

CATEGORIAS_CON_CONTRASTE = frozenset(
    {"espana", "geopolitica", "ciencia", "ia_y_actualidad"}
)

# Lista curada amplia y plural (izquierda, centro, derecha, internacional,
# estatal). Sin etiquetas de orientación: la pluralidad la aporta la mezcla.
FEEDS_CURADOS = {
    "espana": [
        "https://elpais.com/rss/espana/el_pais.xml",
        "https://e00-elmundo.static.preney.com/elmundo/rss/espana.xml",
        "https://www.eldiario.es/rss/",
        "https://www.publico.es/rss/",
        "https://www.abc.es/rss/feeds/abc_Espana.xml",
        "https://www.larazon.es/rss/portada.xml",
        "https://www.elconfidencial.com/rss/espana/",
        "https://www.lavanguardia.com/rss/home.xml",
        "https://www.20minutos.es/rss/",
        "https://www.infolibre.es/rss/",
    ],
    "geopolitica": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.globaltimes.cn/rss/china.xml",
        "https://feeds.feedburner.com/euronews/es/home/",
        "https://www.descifrandolaguerra.es/feed/",
        "https://www.lavanguardia.com/rss/internacional.xml",
        "https://elpais.com/rss/internacional/portada.xml",
    ],
    "ia_y_actualidad": [
        "https://www.xataka.com/tag/inteligencia-artificial/rss.xml",
        "https://www.genbeta.com/tag/inteligencia-artificial/rss.xml",
        "https://www.wired.com/feed/category/gear/latest/rss",
        "https://www.technologyreview.es/rss",
    ],
    "ciencia": [
        "https://www.agenciasinc.es/rss",
        "https://elpais.com/rss/ciencia/el_pais.xml",
        "https://naukas.com/feed/",
        "https://www.scientificamerican.com/custom-feeds/rss-all/",
    ],
    "friki": [
        "https://noticias.crunchyroll.com/rss",
        "https://www.nintenderos.com/feed/",
        "https://www.cpokemon.com/feed/",
        "https://victoryroadvgc.com/feed/",
        "https://vgc.news/feed/",
        "https://www.3djuegos.com/index.php?noticias=rss",
    ],
    "futbol": [
        "https://e00-marca.static.preney.com/rss/futbol/liga_campeones.xml",
        "https://as.com/rss/futbol/primera.xml",
        "https://www.mundodeportivo.com/rss/futbol/la-liga.xml",
    ],
}

# Topics oficiales de Google News (sección "headlines/section/topic/<TOPIC>").
SECCIONES_GOOGLE_NEWS = {
    "espana": ["NATION"],
    "geopolitica": ["WORLD"],
    "ciencia": ["SCIENCE"],
    "ia_y_actualidad": ["TECHNOLOGY"],
}


def url_google_news(valor, es_busqueda=False):
    """Construye una URL de Google News RSS en español de España.

    - es_busqueda=False: feed de sección por topic (ej. "WORLD", "NATION").
    - es_busqueda=True: feed de búsqueda por término.
    """
    if es_busqueda:
        return f"{_GN_BASE}/search?q={quote_plus(valor)}&{_GN_PARAMS}"
    return f"{_GN_BASE}/headlines/section/topic/{valor}?{_GN_PARAMS}"
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_fuentes.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/fuentes.py tests/test_fuentes.py
git commit -m "$(cat <<'EOF'
feat: catálogo de fuentes y builder de Google News RSS

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `src/ingesta.py` — `limpiar_html`

**Files:**
- Modify: `src/ingesta.py` (reescritura progresiva; empezamos por las funciones puras)
- Test: `tests/test_ingesta.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_ingesta.py
from src import ingesta


def test_limpiar_html_quita_tags_y_entidades():
    crudo = "<p>Hola <b>mundo</b> &amp; adi&oacute;s</p>"
    assert ingesta.limpiar_html(crudo) == "Hola mundo & adiós"


def test_limpiar_html_vacio():
    assert ingesta.limpiar_html("") == ""
    assert ingesta.limpiar_html(None) == ""
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: FAIL — `AttributeError: module 'src.ingesta' has no attribute 'limpiar_html'` (o `ModuleNotFoundError` si aún no existe; reescribiremos el archivo).

- [ ] **Step 3: Reescribir `src/ingesta.py` con los imports y `limpiar_html`**

Reemplaza TODO el contenido de `src/ingesta.py` por:

```python
import calendar
import html
import logging
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import feedparser

from src import fuentes

logger = logging.getLogger("noticia.ingesta")

_TAGS = re.compile(r"<[^>]+>")


def limpiar_html(texto):
    """Elimina etiquetas HTML y desescapa entidades. None -> ''."""
    if not texto:
        return ""
    sin_tags = _TAGS.sub("", texto)
    return html.unescape(sin_tags).strip()
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/ingesta.py tests/test_ingesta.py
git commit -m "$(cat <<'EOF'
feat: limpieza real de HTML en la ingesta

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `src/ingesta.py` — `es_reciente`

**Files:**
- Modify: `src/ingesta.py`
- Test: `tests/test_ingesta.py`

- [ ] **Step 1: Añadir el test que falla**

```python
# tests/test_ingesta.py  (añadir al final)
import time as _time


def test_es_reciente_dentro_de_ventana():
    ahora = _time.time()
    hace_10h = _time.gmtime(ahora - 10 * 3600)
    assert ingesta.es_reciente(hace_10h, ventana_horas=48, ahora=ahora) is True


def test_es_reciente_fuera_de_ventana():
    ahora = _time.time()
    hace_5dias = _time.gmtime(ahora - 5 * 24 * 3600)
    assert ingesta.es_reciente(hace_5dias, ventana_horas=48, ahora=ahora) is False


def test_es_reciente_sin_fecha_se_conserva():
    assert ingesta.es_reciente(None) is True
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: FAIL — `AttributeError: ... 'es_reciente'`.

- [ ] **Step 3: Añadir `es_reciente` a `src/ingesta.py`** (debajo de `limpiar_html`)

```python
def es_reciente(fecha_struct, ventana_horas=48, ahora=None):
    """True si la fecha (time.struct_time UTC) está dentro de la ventana.

    Artículos sin fecha (None) se conservan (devuelve True).
    """
    if fecha_struct is None:
        return True
    if ahora is None:
        ahora = time.time()
    epoch = calendar.timegm(fecha_struct)
    return (ahora - epoch) <= ventana_horas * 3600
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/ingesta.py tests/test_ingesta.py
git commit -m "$(cat <<'EOF'
feat: filtro de recencia de noticias en la ingesta

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `src/ingesta.py` — `_parsear_entrada` y `_dedup`

`_parsear_entrada` debe extraer la fuente real de las entradas de Google News
(que vienen como `"Titular - Medio"` con `entry.source.title`), no la del feed.

**Files:**
- Modify: `src/ingesta.py`
- Test: `tests/test_ingesta.py`

- [ ] **Step 1: Añadir los tests que fallan**

```python
# tests/test_ingesta.py  (añadir al final)
def test_parsear_entrada_basica():
    entry = {
        "title": "Titular de prueba",
        "summary": "<p>Resumen &amp; co</p>",
        "link": "https://medio.com/n1",
        "published_parsed": _time.gmtime(),
    }
    art = ingesta._parsear_entrada(entry, "medio.com")
    assert art["titular"] == "Titular de prueba"
    assert art["resumen"] == "Resumen & co"
    assert art["fuente"] == "medio.com"
    assert art["url"] == "https://medio.com/n1"


def test_parsear_entrada_google_news_usa_fuente_real():
    entry = {
        "title": "Sube el paro - El País",
        "summary": "texto",
        "link": "https://news.google.com/x",
        "source": {"title": "El País"},
    }
    art = ingesta._parsear_entrada(entry, "news.google.com")
    assert art["fuente"] == "El País"
    assert art["titular"] == "Sube el paro"  # se quita el sufijo " - El País"


def test_parsear_entrada_sin_titulo_devuelve_none():
    assert ingesta._parsear_entrada({"summary": "x"}, "medio.com") is None


def test_dedup_por_url_y_titular():
    arts = [
        {"titular": "A", "url": "u1"},
        {"titular": "A-dup", "url": "u1"},     # misma url -> fuera
        {"titular": "B", "url": ""},
        {"titular": "B", "url": ""},            # mismo titular sin url -> fuera
        {"titular": "C", "url": "u3"},
    ]
    out = ingesta._dedup(arts)
    assert [a["titular"] for a in out] == ["A", "B", "C"]
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: FAIL — `AttributeError: ... '_parsear_entrada'`.

- [ ] **Step 3: Añadir `_parsear_entrada` y `_dedup` a `src/ingesta.py`**

```python
def _parsear_entrada(entry, fuente_por_defecto):
    """Convierte una entrada de feedparser en un dict de artículo, o None."""
    titular = entry.get("title")
    if not titular:
        return None

    fuente = fuente_por_defecto
    src = entry.get("source")
    if src and src.get("title"):
        fuente = src["title"]
        sufijo = f" - {fuente}"
        if titular.endswith(sufijo):
            titular = titular[: -len(sufijo)]

    return {
        "titular": titular.strip(),
        "resumen": limpiar_html(entry.get("summary", ""))[:500],
        "fuente": fuente,
        "url": entry.get("link", ""),
        "fecha": entry.get("published_parsed"),
    }


def _dedup(articulos):
    """Elimina artículos con URL idéntica o, a falta de URL, titular idéntico."""
    vistos = set()
    salida = []
    for art in articulos:
        clave = art.get("url") or art["titular"]
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append(art)
    return salida
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add src/ingesta.py tests/test_ingesta.py
git commit -m "$(cat <<'EOF'
feat: parseo de entradas con fuente real y dedup en la ingesta

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `src/ingesta.py` — `_descargar_feed` y `obtener_pool`

**Files:**
- Modify: `src/ingesta.py`
- Test: `tests/test_ingesta.py`

- [ ] **Step 1: Añadir los tests que fallan**

```python
# tests/test_ingesta.py  (añadir al final)
class _FakeFeed:
    def __init__(self, entries):
        self.entries = entries


def test_descargar_feed_parsea_entradas(monkeypatch):
    entradas = [
        {"title": "N1", "summary": "s1", "link": "u1", "published_parsed": _time.gmtime()},
        {"title": "N2", "summary": "s2", "link": "u2", "published_parsed": _time.gmtime()},
    ]
    monkeypatch.setattr(ingesta.feedparser, "parse", lambda url: _FakeFeed(entradas))
    arts = ingesta._descargar_feed("http://x", "x.com")
    assert [a["titular"] for a in arts] == ["N1", "N2"]
    assert arts[0]["fuente"] == "x.com"


def test_obtener_pool_filtra_recencia_y_estructura(monkeypatch):
    reciente = _time.gmtime(_time.time() - 3600)
    viejo = _time.gmtime(_time.time() - 10 * 24 * 3600)
    entradas = [
        {"title": "Nueva", "summary": "s", "link": "u-nueva", "published_parsed": reciente},
        {"title": "Vieja", "summary": "s", "link": "u-vieja", "published_parsed": viejo},
    ]
    monkeypatch.setattr(ingesta.feedparser, "parse", lambda url: _FakeFeed(entradas))
    # Catálogos mínimos para no depender de la lista real ni de la red
    monkeypatch.setattr(ingesta.fuentes, "FEEDS_CURADOS", {"espana": ["http://x"]})
    monkeypatch.setattr(ingesta.fuentes, "SECCIONES_GOOGLE_NEWS", {})

    pool = ingesta.obtener_pool(ventana_horas=48, timeout=1)
    assert set(pool.keys()) == {"espana"}
    titulares = [a["titular"] for a in pool["espana"]]
    assert "Nueva" in titulares
    assert "Vieja" not in titulares
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: FAIL — `AttributeError: ... '_descargar_feed'`.

- [ ] **Step 3: Añadir `_dominio`, `_descargar_feed` y `obtener_pool` a `src/ingesta.py`**

```python
def _dominio(url):
    net = urlparse(url).netloc
    return net[4:] if net.startswith("www.") else net


def _descargar_feed(url, fuente_por_defecto, max_entradas=15):
    feed = feedparser.parse(url)
    articulos = []
    for entry in feed.entries[:max_entradas]:
        art = _parsear_entrada(entry, fuente_por_defecto)
        if art:
            articulos.append(art)
    return articulos


def obtener_pool(ventana_horas=48, timeout=10, max_workers=12):
    """Devuelve {categoria: [articulo, ...]} limpio, reciente y sin duplicados."""
    socket.setdefaulttimeout(timeout)

    # (categoria, url, fuente_por_defecto)
    tareas = []
    for categoria, urls in fuentes.FEEDS_CURADOS.items():
        for url in urls:
            tareas.append((categoria, url, _dominio(url)))
    for categoria, topics in fuentes.SECCIONES_GOOGLE_NEWS.items():
        for topic in topics:
            tareas.append((categoria, fuentes.url_google_news(topic), "news.google.com"))

    pool = {categoria: [] for categoria in fuentes.FEEDS_CURADOS}

    def _trabajo(tarea):
        categoria, url, fuente = tarea
        try:
            return categoria, _descargar_feed(url, fuente)
        except Exception as exc:
            logger.warning("Feed fallido %s: %s", url, exc)
            return categoria, []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for categoria, articulos in executor.map(_trabajo, tareas):
            pool.setdefault(categoria, []).extend(articulos)

    for categoria in pool:
        recientes = [a for a in pool[categoria] if es_reciente(a["fecha"], ventana_horas)]
        pool[categoria] = _dedup(recientes)

    return pool
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add src/ingesta.py tests/test_ingesta.py
git commit -m "$(cat <<'EOF'
feat: descarga paralela con timeout y pool de noticias

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `src/agrupador.py` — `_normalizar`

**Files:**
- Create: `src/agrupador.py`
- Test: `tests/test_agrupador.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_agrupador.py
from src import agrupador


def test_normalizar_quita_acentos_stopwords_y_puntuacion():
    assert agrupador._normalizar("El Gobierno de España aprueba la Reforma!") == \
        "gobierno espana aprueba reforma"


def test_normalizar_vacio():
    assert agrupador._normalizar("") == ""
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_agrupador.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.agrupador'`.

- [ ] **Step 3: Implementar `src/agrupador.py` con imports y `_normalizar`**

```python
import re
import unicodedata

from rapidfuzz import fuzz

from src.fuentes import CATEGORIAS_CON_CONTRASTE

_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "y",
    "o", "a", "en", "que", "por", "con", "para", "su", "sus", "al", "se",
    "lo", "es", "the",
}
_NO_ALFANUM = re.compile(r"[^a-z0-9\s]")


def _normalizar(texto):
    """minúsculas, sin acentos, sin puntuación, sin stopwords ni palabras de 1 letra."""
    texto = texto.lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = _NO_ALFANUM.sub(" ", texto)
    palabras = [p for p in texto.split() if p not in _STOPWORDS and len(p) > 1]
    return " ".join(palabras)
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_agrupador.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/agrupador.py tests/test_agrupador.py
git commit -m "$(cat <<'EOF'
feat: normalización de titulares para agrupamiento léxico

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `src/agrupador.py` — `agrupar_categoria`

**Files:**
- Modify: `src/agrupador.py`
- Test: `tests/test_agrupador.py`

- [ ] **Step 1: Añadir los tests que fallan**

```python
# tests/test_agrupador.py  (añadir al final)
def _art(titular, fuente):
    return {"titular": titular, "resumen": "", "fuente": fuente, "url": titular + fuente}


def test_agrupar_junta_misma_noticia_de_fuentes_distintas():
    arts = [
        _art("El Gobierno aprueba la reforma laboral", "elpais.com"),
        _art("El Gobierno aprueba reforma laboral hoy", "abc.es"),
        _art("Resultados de la Champions League", "marca.com"),
    ]
    clusters = agrupador.agrupar_categoria(arts, umbral=70)
    # El cluster con 2 fuentes va primero
    assert len(clusters[0]["articulos"]) == 2
    fuentes_primer_cluster = {a["fuente"] for a in clusters[0]["articulos"]}
    assert fuentes_primer_cluster == {"elpais.com", "abc.es"}
    # La noticia no relacionada queda en su propio cluster
    assert any(len(c["articulos"]) == 1 for c in clusters)


def test_agrupar_categoria_clusters_tienen_tema():
    arts = [_art("Noticia única importante", "medio.com")]
    clusters = agrupador.agrupar_categoria(arts)
    assert clusters[0]["tema"] == "Noticia única importante"
    assert "_norm" not in clusters[0]  # campo interno no se filtra
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_agrupador.py -v`
Expected: FAIL — `AttributeError: ... 'agrupar_categoria'`.

- [ ] **Step 3: Añadir `agrupar_categoria` a `src/agrupador.py`**

```python
def agrupar_categoria(articulos, umbral=70):
    """Agrupa artículos por similitud léxica de titulares.

    Devuelve [{"tema": str, "articulos": [...]}], priorizando los clusters
    con más fuentes distintas (más contrastables).
    """
    clusters = []
    for art in articulos:
        norm = _normalizar(art["titular"])
        destino = None
        for cluster in clusters:
            if fuzz.token_set_ratio(norm, cluster["_norm"]) >= umbral:
                destino = cluster
                break
        if destino is not None:
            destino["articulos"].append(art)
        else:
            clusters.append({"tema": art["titular"], "_norm": norm, "articulos": [art]})

    for cluster in clusters:
        del cluster["_norm"]

    clusters.sort(
        key=lambda c: len({a["fuente"] for a in c["articulos"]}),
        reverse=True,
    )
    return clusters
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_agrupador.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/agrupador.py tests/test_agrupador.py
git commit -m "$(cat <<'EOF'
feat: agrupamiento léxico de noticias del mismo hecho

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `src/agrupador.py` — `agrupar` (orquestador)

**Files:**
- Modify: `src/agrupador.py`
- Test: `tests/test_agrupador.py`

- [ ] **Step 1: Añadir los tests que fallan**

```python
# tests/test_agrupador.py  (añadir al final)
def test_agrupar_categorias_de_contraste_devuelven_clusters():
    pool = {
        "espana": [_art("Sube el IPC en abril", "elpais.com")],
        "futbol": [_art("El Madrid gana la liga", "marca.com")],
    }
    resultado = agrupador.agrupar(pool)
    # España (contraste) -> dict con clusters
    assert "clusters" in resultado["espana"]
    assert isinstance(resultado["espana"]["clusters"], list)
    # Fútbol (simple) -> lista plana sin tocar
    assert resultado["futbol"] == pool["futbol"]


def test_agrupar_categoria_vacia_devuelve_estructura_valida():
    resultado = agrupador.agrupar({"ciencia": [], "friki": []})
    assert resultado["ciencia"] == {"clusters": []}
    assert resultado["friki"] == []
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_agrupador.py -v`
Expected: FAIL — `AttributeError: ... 'agrupar'`.

- [ ] **Step 3: Añadir `agrupar` a `src/agrupador.py`**

```python
def agrupar(pool):
    """Aplica clustering a las categorías de contraste; deja el resto plano."""
    resultado = {}
    for categoria, articulos in pool.items():
        if categoria in CATEGORIAS_CON_CONTRASTE:
            resultado[categoria] = {"clusters": agrupar_categoria(articulos)}
        else:
            resultado[categoria] = articulos
    return resultado
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_agrupador.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/agrupador.py tests/test_agrupador.py
git commit -m "$(cat <<'EOF'
feat: orquestador de agrupamiento por categoría

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Función puente y verificación final

`main.py` y `test_5min.py` llaman a `obtener_noticias()`, y `generador.py` espera
listas planas en TODAS las categorías. Para no romper la producción mientras el
generador no se adapta (fase posterior), añadimos `obtener_noticias()` como
**función puente** que devuelve listas planas, y exponemos el pipeline nuevo aparte.

**Files:**
- Modify: `src/ingesta.py`
- Test: `tests/test_ingesta.py`

- [ ] **Step 1: Añadir el test que falla**

```python
# tests/test_ingesta.py  (añadir al final)
def test_obtener_noticias_puente_aplana_clusters(monkeypatch):
    # Pool simulado: espana (contraste) + futbol (simple)
    fake_pool = {
        "espana": [
            {"titular": "A", "resumen": "", "fuente": "f1", "url": "a", "fecha": None},
            {"titular": "B", "resumen": "", "fuente": "f2", "url": "b", "fecha": None},
        ],
        "futbol": [
            {"titular": "Gol", "resumen": "", "fuente": "marca", "url": "g", "fecha": None},
        ],
    }
    monkeypatch.setattr(ingesta, "obtener_pool", lambda **kw: fake_pool)

    noticias = ingesta.obtener_noticias()
    # Todas las categorías devuelven listas planas (compatibilidad con generador actual)
    assert isinstance(noticias["espana"], list)
    assert isinstance(noticias["futbol"], list)
    assert {a["titular"] for a in noticias["espana"]} == {"A", "B"}
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_ingesta.py -v`
Expected: FAIL — `AttributeError: ... 'obtener_noticias'`.

- [ ] **Step 3: Añadir `obtener_noticias` (puente) al final de `src/ingesta.py`**

```python
def obtener_noticias(**kwargs):
    """PUENTE de compatibilidad: devuelve listas planas por categoría.

    Mantiene la firma que esperan main.py / test_5min.py / generador.py
    mientras el generador no se adapte al contrato de clusters. El nuevo
    pipeline con contraste se obtiene vía obtener_pool() + agrupador.agrupar().
    """
    pool = obtener_pool(**kwargs)
    return {categoria: articulos for categoria, articulos in pool.items()}
```

- [ ] **Step 4: Ejecutar la suite completa**

Run: `.venv/bin/python -m pytest -v`
Expected: PASS (todos los tests: fuentes 4 + ingesta 12 + agrupador 6 = 22).

- [ ] **Step 5: Verificación manual de import (sin red)**

Run: `.venv/bin/python -c "from src import ingesta, agrupador, fuentes; print('imports OK')"`
Expected: `imports OK` (confirma que no hay errores de sintaxis ni de importación circular).

- [ ] **Step 6: Commit**

```bash
git add src/ingesta.py tests/test_ingesta.py
git commit -m "$(cat <<'EOF'
feat: función puente para compatibilidad con el generador actual

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Notas para el ejecutor

- **No toques** `generador.py`, `locutor.py` ni `editor.py`: están fuera de alcance.
- Todos los tests son **deterministas y sin red** (feedparser se mockea con `monkeypatch`).
- Usa `.venv/bin/python` / `.venv/bin/pip` para no depender de activar el venv.
- El `obtener_noticias` final es un **puente temporal**; la adaptación del generador
  para consumir clusters (y aprovechar el contraste) es un plan posterior.
- Tras completar todo, el pipeline de contraste real es:
  `ingesta.obtener_pool()` → `agrupador.agrupar(pool)` → consumidor (futuro generador).
