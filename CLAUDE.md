# NoticIA — Instrucciones del proyecto

NoticIA es un **podcast diario automatizado**: transforma la actualidad en una tertulia
entre dos locutores (**Álex** y **María**) y produce un MP3 final.

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
