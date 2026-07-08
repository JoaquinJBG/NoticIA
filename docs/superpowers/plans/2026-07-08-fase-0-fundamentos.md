# Fase 0 — Fundamentos y estructura — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reestructurar NoticIA a un paquete Python limpio (`src/noticia/`) con tooling moderno (uv, ruff, pytest), config tipada, logging y sin código muerto, **sin cambiar el comportamiento funcional** del pipeline.

**Architecture:** Se adopta `src-layout` con el paquete `noticia`. La config pasa a `pydantic-settings`. Se centraliza el logging. Los módulos de negocio (ingesta/generador/locutor/editor) se mueven al paquete y solo se les cambia el acceso a config, los `print` por `logger` y los `except:` desnudos; su lógica no cambia. `main.py` se convierte en `cli.py`.

**Tech Stack:** Python 3.12, uv 0.10, ruff, pytest, pydantic-settings; se mantienen feedparser, groq, edge-tts, pydub.

**Spec:** `docs/superpowers/specs/2026-07-08-fase-0-fundamentos-design.md`

## Global Constraints

- Python `>=3.12`. Gestor de entorno y comandos: **`uv`** (`uv sync`, `uv run ...`).
- Layout `src/noticia/`; los imports internos son `from noticia.X import ...` (nunca `from src.X`).
- Dominio en **español** (nombres de funciones/variables se conservan).
- **No cambiar el comportamiento funcional** del pipeline (ingesta/generador/locutor/editor mantienen su lógica).
- `logging` en vez de `print`; `except Exception as exc:` con log en vez de `except:` desnudo.
- `ingesta.py` se mueve pero **no** se le migran prints/except (se reescribe entera en la Fase 1).
- Dependencias eliminadas: `asyncio`, `google-generativeai`, `python-dotenv`.

---

## File Structure

| Archivo | Responsabilidad |
|---------|-----------------|
| `pyproject.toml` (crear) | Metadata, deps, config de ruff y pytest, script `noticia` |
| `src/noticia/__init__.py` (crear) | Marca el paquete |
| `src/noticia/config.py` (reescribir) | `Settings` (pydantic-settings), singleton `settings`, `get_prompt_sistema`/`get_contexto` |
| `src/noticia/logging_setup.py` (crear) | `configurar_logging()` |
| `src/noticia/cli.py` (crear desde `main.py`) | `producir_episodio()`, `main()`, entry point |
| `src/noticia/{ingesta,generador,locutor,editor}.py` (mover) | Lógica de negocio (solo cambia config/logging/except) |
| `tests/` (crear) | Smoke test + tests de config y logging |
| `CLAUDE.md` (crear) | Instrucciones del proyecto |
| Borrar | `main.py`, `test_5min.py`, `documentacion/`, `ensamblar_podcast` en editor, destrackear `produccion.log` |

**Interfaz de config (contrato que consumen los módulos):**
- `from noticia.config import settings, get_prompt_sistema, get_contexto`
- `settings.groq_api_key: str | None`, `settings.voz_alex: str`, `settings.voz_santi: str`,
  `settings.carpeta_output: str`, `settings.carpeta_temp: str`,
  `settings.ruta_sintonia: str`, `settings.sintonias: dict[str, str]`
- `get_prompt_sistema() -> str`, `get_contexto() -> str`

---

## Task 1: Tooling y esqueleto del paquete

**Files:**
- Create: `pyproject.toml`
- Create: `src/noticia/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Crear `pyproject.toml`**

```toml
[project]
name = "noticia"
version = "0.1.0"
description = "Podcast diario automatizado con IA"
requires-python = ">=3.12"
dependencies = [
    "feedparser>=6.0.11",
    "groq>=0.18.0",
    "edge-tts>=6.1.12",
    "pydub>=0.25.1",
    "pydantic-settings>=2.5.2",
]

[project.scripts]
noticia = "noticia.cli:main"

[dependency-groups]
dev = [
    "pytest>=8.3.4",
    "ruff>=0.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/noticia"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 2: Crear `src/noticia/__init__.py`** (fichero vacío)

```python
```

- [ ] **Step 3: Crear `tests/__init__.py`** (fichero vacío)

```python
```

- [ ] **Step 4: Sincronizar el entorno con uv**

Run: `uv sync`
Expected: crea/actualiza `.venv` y `uv.lock`, instala deps + grupo `dev`, e instala `noticia` en modo editable.

- [ ] **Step 5: Verificar que el paquete importa y pytest arranca**

Run: `uv run python -c "import noticia; print('ok')"`
Expected: `ok`
Run: `uv run pytest -q`
Expected: `no tests ran` (sin errores de colección).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/noticia/__init__.py tests/__init__.py
git commit -m "$(cat <<'EOF'
chore: esqueleto de paquete noticia con pyproject, uv, ruff y pytest

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Reubicar el código a `src/noticia/` y crear `cli.py`

Mueve los módulos al paquete y arregla imports. La config sigue siendo la clase `Config`
antigua en este paso (se refactoriza en la Task 3); aquí solo cambia su ubicación e imports,
por lo que el comportamiento es idéntico.

**Files:**
- Move: `src/{config,ingesta,generador,locutor,editor}.py` → `src/noticia/`
- Move: `main.py` → `src/noticia/cli.py`
- Delete: `src/__init__.py` (antiguo)
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Mover los módulos al paquete**

```bash
git mv src/config.py src/noticia/config.py
git mv src/ingesta.py src/noticia/ingesta.py
git mv src/generador.py src/noticia/generador.py
git mv src/locutor.py src/noticia/locutor.py
git mv src/editor.py src/noticia/editor.py
git rm src/__init__.py
```

- [ ] **Step 2: Arreglar imports internos `from src.X` → `from noticia.X`**

En `src/noticia/generador.py`, `src/noticia/locutor.py` y `src/noticia/editor.py`, cambiar:

```python
from src.config import Config
```
por:
```python
from noticia.config import Config
```

(`ingesta.py` no importa otros módulos del paquete; no se toca.)

- [ ] **Step 3: Convertir `main.py` en `src/noticia/cli.py`**

```bash
git mv main.py src/noticia/cli.py
```

Reemplazar TODO el contenido de `src/noticia/cli.py` por (mismo comportamiento, imports del paquete y `main()`):

```python
import asyncio
import os

from noticia.editor import ensamblar_podcast_dinamico
from noticia.generador import construir_guion
from noticia.ingesta import obtener_noticias
from noticia.locutor import procesar_guion_a_audio


async def producir_episodio():
    print("--- 🎙️ INICIANDO PRODUCCIÓN DE NOTICIA: PROFESSIONAL EDITION ---")

    os.makedirs("output", exist_ok=True)
    os.makedirs("temp", exist_ok=True)

    print("📡 Capturando noticias de todas las fuentes...")
    noticias = obtener_noticias()

    print("🧠 Generando guion inteligente por bloques (esto puede tardar unos minutos)...")
    guion_por_bloques = construir_guion(noticias)

    print("🎙️ Iniciando locución de voces realistas...")
    fragmentos_audio_por_bloque = {}
    for categoria, lineas in guion_por_bloques.items():
        if not lineas:
            continue
        print(f"🎬 Procesando locución del bloque: {categoria}...")
        texto_bloque = "\n".join(lineas)
        fragmentos_audio_por_bloque[categoria] = await procesar_guion_a_audio(texto_bloque)

    if fragmentos_audio_por_bloque:
        archivo_final = os.path.join("output", "NoticIA_PRO_Final.mp3")
        print("🎬 Iniciando montaje dinámico y mastering final...")
        ensamblar_podcast_dinamico(fragmentos_audio_por_bloque, archivo_final)
        print(f"\n--- ✨ PODCAST PROFESIONAL FINALIZADO: {archivo_final} ---")
    else:
        print("❌ Error: No se generaron audios para ensamblar.")


def main():
    asyncio.run(producir_episodio())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Escribir el smoke test**

```python
# tests/test_smoke.py
def test_todos_los_modulos_importan():
    import noticia.config  # noqa: F401
    import noticia.ingesta  # noqa: F401
    import noticia.generador  # noqa: F401
    import noticia.locutor  # noqa: F401
    import noticia.editor  # noqa: F401
    import noticia.cli  # noqa: F401
```

- [ ] **Step 5: Ejecutar el smoke test**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS. (Requiere que `.env` con `GROQ_API_KEY` exista, porque `generador.py` aún construye el cliente Groq al importar; se hará lazy en la Task 3. En la máquina del usuario el `.env` existe.)

- [ ] **Step 6: Normalizar formato con ruff**

Run: `uv run ruff format src tests`
Run: `uv run ruff check --fix src tests`
Expected: sin errores pendientes.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: mover el código al paquete noticia y crear cli.py

Reubica config/ingesta/generador/locutor/editor a src/noticia/ y convierte
main.py en cli.py con main(). Sin cambios de comportamiento.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Config tipada con `pydantic-settings`

**Files:**
- Rewrite: `src/noticia/config.py`
- Modify: `src/noticia/generador.py`, `src/noticia/locutor.py`, `src/noticia/editor.py`, `src/noticia/cli.py`
- Create: `.env.example`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `settings` (singleton de `Settings`), `get_prompt_sistema()`, `get_contexto()` en `noticia.config`.
- Consumes (los módulos): los atributos de `settings` y las dos funciones (ver contrato en File Structure).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_config.py
import noticia.config as config


def test_settings_valores_por_defecto():
    assert config.settings.voz_alex == "es-ES-AlvaroNeural"
    assert config.settings.voz_santi == "es-ES-XimenaNeural"
    assert config.settings.carpeta_output == "output"
    assert config.settings.carpeta_temp == "temp"


def test_sintonias_cubre_categorias_y_apunta_a_mp3():
    s = config.settings.sintonias
    assert {"espana", "geopolitica", "ia_y_actualidad", "ciencia", "friki",
            "futbol", "intro", "outro"} <= set(s)
    assert all(v.endswith(".mp3") for v in s.values())


def test_get_prompt_sistema_lee_las_reglas():
    txt = config.get_prompt_sistema()
    assert isinstance(txt, str) and len(txt) > 0
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: module 'noticia.config' has no attribute 'settings'` (aún es la clase `Config`).

- [ ] **Step 3: Reescribir `src/noticia/config.py`**

Reemplaza TODO el contenido por:

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/noticia/config.py -> parents[2] es la raíz del proyecto
ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str | None = None
    gemini_api_key: str | None = None

    voz_alex: str = "es-ES-AlvaroNeural"
    voz_santi: str = "es-ES-XimenaNeural"

    carpeta_output: str = "output"
    carpeta_temp: str = "temp"

    @property
    def ruta_sintonia(self) -> str:
        return str(ROOT / "sintonias" / "sintonia1.mp3")

    @property
    def sintonias(self) -> dict[str, str]:
        base = ROOT / "sintonias"
        return {
            "espana": str(base / "serio.mp3"),
            "geopolitica": str(base / "serio.mp3"),
            "ia_y_actualidad": str(base / "animado.mp3"),
            "ciencia": str(base / "neutro.mp3"),
            "friki": str(base / "animado.mp3"),
            "futbol": str(base / "neutro.mp3"),
            "intro": str(base / "sintonia1.mp3"),
            "outro": str(base / "sintonia1.mp3"),
        }


settings = Settings()


def _leer_regla(nombre: str, fallback: str = "") -> str:
    ruta = ROOT / "reglas" / nombre
    if ruta.exists():
        return ruta.read_text(encoding="utf-8")
    return fallback


def get_prompt_sistema() -> str:
    return _leer_regla("instrucciones.md", "Eres el equipo de producción de NoticIA.")


def get_contexto() -> str:
    return _leer_regla("contexto.md", "")
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Adaptar `generador.py` al nuevo config (con cliente Groq lazy)**

En `src/noticia/generador.py`, reemplazar la cabecera (imports + creación del cliente) por:

```python
from groq import Groq

from noticia.config import get_contexto, get_prompt_sistema, settings

MODELO_GROQ = "llama-3.3-70b-versatile"
_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if settings.groq_api_key is None:
        raise RuntimeError("❌ Falta GROQ_API_KEY en el .env")
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client
```

En la función `llamar_ia`, cambiar `client.chat.completions.create(` por `_get_client().chat.completions.create(`.

En `construir_bloque_con_contexto`, cambiar:
```python
prompt_sistema = f"{Config.get_prompt_sistema()}\n\nCONTEXTO GENERAL:\n{Config.get_contexto()}"
```
por:
```python
prompt_sistema = f"{get_prompt_sistema()}\n\nCONTEXTO GENERAL:\n{get_contexto()}"
```

En `generar_intro` y `generar_outro`, cambiar `Config.get_prompt_sistema()` por `get_prompt_sistema()`.

- [ ] **Step 6: Adaptar `locutor.py` al nuevo config**

En `src/noticia/locutor.py`, cambiar el import `from noticia.config import Config` por `from noticia.config import settings`, y reemplazar:
- `Config.CARPETA_TEMP` → `settings.carpeta_temp`
- `Config.VOZ_ALEX` → `settings.voz_alex`
- `Config.VOZ_SANTI` → `settings.voz_santi`

- [ ] **Step 7: Adaptar `editor.py` al nuevo config**

En `src/noticia/editor.py`, cambiar el import `from noticia.config import Config` por `from noticia.config import settings`, y reemplazar:
- `Config.SINTONIAS.get(categoria, Config.RUTA_SINTONIA)` → `settings.sintonias.get(categoria, settings.ruta_sintonia)`

- [ ] **Step 8: Adaptar `cli.py` al nuevo config**

En `src/noticia/cli.py`, añadir `from noticia.config import settings` y cambiar:
- `os.makedirs("output", exist_ok=True)` → `os.makedirs(settings.carpeta_output, exist_ok=True)`
- `os.makedirs("temp", exist_ok=True)` → `os.makedirs(settings.carpeta_temp, exist_ok=True)`
- `os.path.join("output", "NoticIA_PRO_Final.mp3")` → `os.path.join(settings.carpeta_output, "NoticIA_PRO_Final.mp3")`

- [ ] **Step 9: Crear `.env.example`**

```bash
# .env.example — copia a .env y rellena
GROQ_API_KEY=
GEMINI_API_KEY=
VOZ_ALEX=es-ES-AlvaroNeural
VOZ_SANTI=es-ES-XimenaNeural
```

- [ ] **Step 10: Ejecutar toda la suite + ruff**

Run: `uv run pytest -q`
Expected: PASS (smoke + 3 de config).
Run: `uv run ruff check --fix src tests && uv run ruff format src tests`
Expected: sin errores.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: config tipada con pydantic-settings y cliente Groq lazy

Sustituye la clase Config por Settings (pydantic-settings) con rutas
resueltas desde la raíz del proyecto. El cliente Groq se crea de forma
diferida para no exigir la clave al importar. Añade .env.example.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Logging y manejo de errores

**Files:**
- Create: `src/noticia/logging_setup.py`
- Modify: `src/noticia/cli.py`, `src/noticia/generador.py`, `src/noticia/locutor.py`, `src/noticia/editor.py`
- Test: `tests/test_logging_setup.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_logging_setup.py
import logging

from noticia.logging_setup import configurar_logging


def test_configurar_logging_es_idempotente():
    logging.getLogger().handlers.clear()
    configurar_logging()
    n = len(logging.getLogger().handlers)
    assert n >= 1
    configurar_logging()  # segunda llamada no debe duplicar handlers
    assert len(logging.getLogger().handlers) == n
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_logging_setup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'noticia.logging_setup'`.

- [ ] **Step 3: Crear `src/noticia/logging_setup.py`**

```python
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_LOG_FILE = ROOT / "produccion.log"
_FORMATO = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Configura logging de consola y fichero. Idempotente."""
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(nivel)

    consola = logging.StreamHandler()
    consola.setFormatter(logging.Formatter(_FORMATO))
    root.addHandler(consola)

    fichero = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fichero.setFormatter(logging.Formatter(_FORMATO))
    root.addHandler(fichero)
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_logging_setup.py -v`
Expected: PASS.

- [ ] **Step 5: Conectar el logging en `cli.py` y migrar sus `print`**

En `src/noticia/cli.py`:
- Añadir al principio:
```python
import logging

from noticia.logging_setup import configurar_logging

logger = logging.getLogger("noticia.cli")
```
- Sustituir cada `print(...)` por `logger.info(...)` (o `logger.error(...)` en el caso del mensaje de error final). Ejemplos:
  - `print("📡 Capturando noticias de todas las fuentes...")` → `logger.info("Capturando noticias de todas las fuentes...")`
  - `print(f"🎬 Procesando locución del bloque: {categoria}...")` → `logger.info("Procesando locución del bloque: %s", categoria)`
  - `print("❌ Error: No se generaron audios para ensamblar.")` → `logger.error("No se generaron audios para ensamblar.")`
- En `main()`, llamar a `configurar_logging()` antes de `asyncio.run(...)`:
```python
def main():
    configurar_logging()
    asyncio.run(producir_episodio())
```

- [ ] **Step 6: Migrar `print` de `generador.py` y `locutor.py`**

En `src/noticia/generador.py` y `src/noticia/locutor.py`, añadir al principio de cada uno:
```python
import logging

logger = logging.getLogger("noticia.generador")  # o "noticia.locutor"
```
y sustituir cada `print(...)` por la llamada equivalente a `logger.info(...)` / `logger.warning(...)` / `logger.error(...)` según el emoji original (❌ → error, ⚠️ → warning, resto → info). Usar el estilo `logger.info("texto %s", variable)` para las interpolaciones. En `generador.py`, el `except Exception as e:` de `llamar_ia` pasa a `logger.error("Error llamando a Groq: %s", e)`.

- [ ] **Step 7: Migrar `print` y arreglar `except:` desnudos en `editor.py`**

En `src/noticia/editor.py`, añadir el logger (`logger = logging.getLogger("noticia.editor")`), migrar los `print(...)` a `logger.info(...)`, y sustituir los tres `except:` desnudos:

- En el bucle de fragmentos:
```python
            try:
                segmento = AudioSegment.from_mp3(f)
                ...
            except Exception as exc:
                logger.warning("No se pudo cargar el fragmento %s: %s", f, exc)
                continue
```
- En el bloque de mezcla de música:
```python
        except Exception as exc:
            logger.warning("Fallo al mezclar música del bloque %s: %s", categoria, exc)
            bloque_mezclado = voces_bloque
```
- En el borrado de temporales:
```python
            try:
                os.remove(f)
            except Exception as exc:
                logger.debug("No se pudo borrar el temporal %s: %s", f, exc)
```

- [ ] **Step 8: Verificar suite completa, ruff y ausencia de `print`/`except:` desnudos**

Run: `uv run pytest -q`
Expected: PASS.
Run: `uv run ruff check src tests`
Expected: sin errores (incluye E722 = no bare-except; `select` incluye E).
Run: `grep -rn "print(" src/noticia/generador.py src/noticia/locutor.py src/noticia/editor.py src/noticia/cli.py`
Expected: sin resultados.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat: logging centralizado y manejo de errores en los módulos

Añade logging_setup.configurar_logging() y sustituye print por logger y
los except desnudos de editor.py por except Exception con log.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Limpieza de código muerto y git

**Files:**
- Delete: `test_5min.py`, `documentacion/workflow.md` (y carpeta), función `ensamblar_podcast` en `editor.py`
- Modify: `.gitignore`
- Untrack: `produccion.log`

- [ ] **Step 1: Borrar ficheros muertos**

```bash
git rm test_5min.py
git rm documentacion/workflow.md
rmdir documentacion 2>/dev/null || true
```

- [ ] **Step 2: Eliminar la función puente `ensamblar_podcast` de `editor.py`**

Borrar del final de `src/noticia/editor.py` estas líneas (la función puente muerta; `main`/`cli` usan `ensamblar_podcast_dinamico`, no esta):

```python
def ensamblar_podcast(fragmentos, archivo_salida="noticIA_final.mp3"):
    ensamblar_podcast_dinamico({'espana': fragmentos}, archivo_salida)
```

- [ ] **Step 3: Destrackear `produccion.log` y añadirlo a `.gitignore`**

```bash
git rm --cached produccion.log
```
Añadir al final de `.gitignore`:
```
# Log de ejecución
produccion.log
```

- [ ] **Step 4: Verificar que nada se rompió**

Run: `uv run pytest -q`
Expected: PASS.
Run: `grep -rn "ensamblar_podcast\b" src/noticia/ | grep -v ensamblar_podcast_dinamico`
Expected: sin resultados (la función puente ya no existe ni se usa).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: eliminar código muerto y destrackear produccion.log

Borra test_5min.py (roto), documentacion/workflow.md (se consolida en
CLAUDE.md) y la función puente ensamblar_podcast. Saca produccion.log
del control de versiones.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `CLAUDE.md` y README

**Files:**
- Create: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Crear `CLAUDE.md`**

```markdown
# NoticIA — Instrucciones del proyecto

NoticIA es un **podcast diario automatizado**: transforma la actualidad en una tertulia
entre dos locutores (**Álex** y **Santi**) y produce un MP3 final.

## Pipeline

`ingesta` (RSS por categoría) → `generador` (LLM: briefing + guion por bloques) →
`locutor` (edge-tts) → `editor` (pydub: sintonías + mastering) → `output/*.mp3`

Bloques: España, Geopolítica, IA y Actualidad, Ciencia, Friki, Fútbol (+ intro/outro).

## Estructura

- `src/noticia/config.py` — `Settings` (pydantic-settings) + `get_prompt_sistema`/`get_contexto`.
- `src/noticia/logging_setup.py` — configuración de logging.
- `src/noticia/{ingesta,generador,locutor,editor}.py` — el pipeline.
- `src/noticia/cli.py` — punto de entrada (`producir_episodio`, `main`).
- `reglas/` — prompts de personalidad y contexto.
- `sintonias/` — músicas de fondo por bloque.
- `tests/` — pytest.
- `docs/superpowers/` — specs y planes (hoja de ruta del rework incluida).

## Comandos

- Instalar/sincronizar: `uv sync`
- Ejecutar el pipeline: `uv run noticia`
- Tests: `uv run pytest`
- Lint y formato: `uv run ruff check` · `uv run ruff format`

## Convenciones

- Dominio en **español** (nombres de funciones y variables).
- **`logging`**, nunca `print`. Obtener el logger con `logging.getLogger("noticia.<modulo>")`.
- Nada de `except:` desnudo: `except Exception as exc:` con log.
- Config vía `from noticia.config import settings`, no `os.getenv` suelto.
- Secretos solo en `.env` (gitignored); `.env.example` documenta las claves.

## Estado

Rework por fases; ver `docs/superpowers/specs/2026-07-08-rework-roadmap.md`.
```

- [ ] **Step 2: Actualizar `README.md`**

Actualizar las secciones de instalación, uso y estructura para reflejar el nuevo layout:
- Instalación: sustituir el bloque de `python -m venv` + `pip install -r requirements.txt` por:
  ```bash
  uv sync
  ```
- Uso: sustituir `python main.py` por `uv run noticia`, y eliminar la mención a `test_5min.py`
  (ahora los tests son `uv run pytest`).
- Estructura del proyecto: reflejar `src/noticia/` y `cli.py` en vez de `main.py`/`src/`.

Mantener el resto (personajes, licencia, requisitos de FFmpeg).

- [ ] **Step 3: Verificación**

Run: `uv run ruff check src tests`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
docs: CLAUDE.md del proyecto y README actualizado al nuevo layout

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Verificación integral de la Fase 0

**Files:** (ninguno — solo verificación)

- [ ] **Step 1: Suite completa verde**

Run: `uv run pytest -q`
Expected: PASS (smoke + config + logging).

- [ ] **Step 2: Lint y formato**

Run: `uv run ruff check src tests`
Expected: `All checks passed!`
Run: `uv run ruff format --check src tests`
Expected: sin ficheros por reformatear.

- [ ] **Step 3: El comando arranca (import del entrypoint)**

Run: `uv run python -c "from noticia.cli import main; print('entrypoint ok')"`
Expected: `entrypoint ok`.

- [ ] **Step 4: Criterios de aceptación del spec**

Run: `grep -rn "print(" src/noticia/generador.py src/noticia/locutor.py src/noticia/editor.py src/noticia/cli.py; echo "---"; grep -rn "except:" src/noticia/`
Expected: sin resultados antes del `---`; sin `except:` desnudos después.
Run: `test -f main.py -o -f test_5min.py -o -d documentacion && echo "QUEDA BASURA" || echo "limpio"`
Expected: `limpio`.
Run: `git ls-files | grep produccion.log || echo "produccion.log no trackeado"`
Expected: `produccion.log no trackeado`.

- [ ] **Step 5 (opcional): Prueba funcional end-to-end**

Con `.env` y FFmpeg disponibles, `uv run noticia` debe generar `output/NoticIA_PRO_Final.mp3`
igual que antes del rework. Es una prueba de humo real (consume red y tokens de Groq); ejecutarla
solo si se quiere confirmar la equivalencia funcional completa.

---

## Notas para el ejecutor

- Usa **`uv run`** para todo; no actives el venv manualmente.
- Ninguna tarea cambia la lógica de ingesta/generador/locutor/editor: solo ubicación, acceso a
  config, logging y limpieza. Si un cambio altera el comportamiento, revísalo.
- `ingesta.py` se mueve pero **no** se le migran prints/except: se reescribe en la Fase 1.
- El smoke test necesita que `import noticia.generador` no falle; por eso el cliente Groq es lazy
  (Task 3). Antes de la Task 3, el import exige `GROQ_API_KEY` en el `.env`.
