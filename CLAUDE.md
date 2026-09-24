# NoticIA — Instrucciones del proyecto

NoticIA es un **podcast diario automatizado**: transforma la actualidad en una tertulia
entre dos locutores (**Álex** y **María**) y produce un MP3 final.

## Pipeline

`ingesta` (RSS por categoría) → `seleccion` → `generador` (LLM: briefing + guion por bloques) →
`locutor` (motores de `voz/`: edge-tts, Kokoro, Chatterbox) → `editor` (pydub: sintonías) +
`masterizado` (ffmpeg loudnorm) → `publicador` (feed RSS local) → `output/*.mp3`.
`orquestador` coordina todo el episodio diario (idempotencia, lock, resumen).

Bloques: España, Geopolítica, IA y Actualidad, Ciencia, Friki, Fútbol (+ intro/outro),
definidos en `bloques.py`. `fechas.py` resuelve "hoy en Madrid" y el parseo de fechas de la CLI.

## Estructura

- `src/noticia/config.py` — `Settings` (pydantic-settings) + `get_prompt_sistema`/`get_contexto`.
- `src/noticia/logging_setup.py` — configuración de logging.
- `src/noticia/orquestador.py` — orquesta el episodio: guion → locución → montaje →
  publicación, con lock (`fcntl.flock`) e idempotencia por fecha.
- `src/noticia/{ingesta,seleccion,generador,locutor,editor,masterizado,publicador}.py` — el pipeline.
- `src/noticia/bloques.py` — orden de emisión y categorías de noticias.
- `src/noticia/fechas.py` — fecha de "hoy" en Madrid y parseo de fechas.
- `src/noticia/voz/` — motores de voz (`motor_edge`, `motor_kokoro`, `motor_chatterbox`),
  `selector.py` (cadena de motores por preferencia/GPU), `gpu.py`, `texto.py` (limpieza y
  pronunciación) y `modelos.py`/`muestras.py` (descarga de pesos y muestras de audio).
- `src/noticia/cli.py` — punto de entrada (`main`, modos `--solo-guion`/`--solo-audio`).
- `reglas/` — prompts de personalidad y contexto.
- `sintonias/` — músicas de fondo por bloque.
- `tests/` — pytest.
- `docs/superpowers/` — specs y planes (hoja de ruta del rework incluida).

## Comandos

- Instalar/sincronizar: `uv sync`
- Ejecutar el pipeline: `uv run noticia` (o `make episodio`)
- Publicar (pipeline + feed local): `make publicar`
- Descargar pesos de Kokoro: `make modelos-voz`
- Comparar motores de voz de oído: `make muestras-voz`
- Servir el feed/publicación local: `make servir`
- Tests: `uv run pytest` (o `make test`)
- Lint y formato: `uv run ruff check` · `uv run ruff format` (o `make lint` / `make formato`)

## Convenciones

- Dominio en **español** (nombres de funciones y variables).
- **`logging`**, nunca `print`. Obtener el logger con `logging.getLogger("noticia.<modulo>")`.
- Nada de `except:` desnudo: `except Exception as exc:` con log.
- Config vía `from noticia.config import settings`, no `os.getenv` suelto.
- Secretos solo en `.env` (gitignored); `.env.example` documenta las claves.

## Estado

Rework por fases; ver `docs/superpowers/specs/2026-07-08-rework-roadmap.md`.
