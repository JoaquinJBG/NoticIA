# Diseño — Fase 0: Fundamentos, seguridad y estructura

**Fecha:** 2026-07-08
**Estado:** Aprobado (pendiente de plan de implementación)
**Hoja de ruta:** `docs/superpowers/specs/2026-07-08-rework-roadmap.md`

---

## 1. Objetivo

Dejar el proyecto sobre una base profesional y limpia antes de acometer las mejoras
de producto. Fase puramente **estructural y de calidad**: no cambia el comportamiento
funcional del pipeline (mismas noticias → mismo guion → mismo audio), solo la forma.

**No-objetivos:** no se reescribe la lógica de negocio (ingesta, generador, locutor,
editor mantienen su comportamiento); esas mejoras son fases posteriores.

---

## 2. Decisiones de diseño (cerradas)

| Decisión | Elección |
|----------|----------|
| Nivel de tooling | Moderno completo: `pyproject.toml` + `uv` + `ruff` + `pytest` |
| Layout | `src-layout` con paquete `noticia` (`src/noticia/`) |
| Config | `pydantic-settings` (tipada, valida, lee `.env` nativo) |
| Idioma del dominio | Español (se mantiene: `obtener_noticias`, `construir_guion`, etc.) |
| Seguridad | Verificado: `.env`/`credentials.json` NO en git; sin claves que rotar |

---

## 3. Estructura objetivo

```
NoticIA/
├── pyproject.toml          # metadata, deps, config de ruff y pytest
├── uv.lock                 # lockfile reproducible
├── .env.example            # plantilla SIN secretos
├── .gitignore              # + produccion.log
├── README.md               # actualizado a la nueva estructura y arranque
├── CLAUDE.md               # instrucciones del proyecto para Claude Code
├── src/
│   └── noticia/
│       ├── __init__.py
│       ├── config.py       # Settings (pydantic-settings)
│       ├── logging_setup.py# configuración de logging
│       ├── ingesta.py
│       ├── generador.py
│       ├── locutor.py
│       ├── editor.py
│       └── cli.py          # punto de entrada (reemplaza main.py)
├── reglas/                 # prompts (sin cambios)
│   ├── instrucciones.md
│   └── contexto.md
├── sintonias/              # mp3 de fondo (sin cambios)
├── tests/
│   └── __init__.py
└── docs/superpowers/       # specs y planes
```

**Cambio de imports:** `from src.ingesta import ...` → `from noticia.ingesta import ...`.
Afecta a todos los módulos que se importan entre sí y al punto de entrada.

---

## 4. Componentes

### 4.1 `pyproject.toml`
- Metadata del proyecto (nombre `noticia`, versión, Python >= 3.12).
- Dependencias de runtime: `feedparser`, `groq`, `edge-tts`, `pydub`, `pydantic-settings`.
  - **Se eliminan:** `asyncio` (stdlib), `google-generativeai` (no se usa en código),
    `python-dotenv` (lo sustituye `pydantic-settings`).
  - `groq` se mantiene hasta la Fase 2 (donde entra Claude).
- Dependencias de desarrollo: `pytest`, `ruff`.
- Configuración de `ruff` (lint + formato) y `pytest` (testpaths, etc.) en el mismo fichero.
- `uv.lock` generado con `uv`.
- Script de entrada: `noticia = "noticia.cli:main"`.

### 4.2 `src/noticia/config.py`
Reemplaza la clase `Config` con getters estáticos por una clase **`Settings(BaseSettings)`**
de `pydantic-settings`:
- Campos tipados: claves (`groq_api_key`, `gemini_api_key` opcional), voces
  (`voz_alex`, `voz_santi`), rutas (`carpeta_output`, `carpeta_temp`), mapa de `sintonias`,
  ruta de sintonía por defecto.
- Lee `.env` de forma nativa; falla con mensaje claro si falta una clave crítica.
- Mantiene los helpers de carga de reglas (`get_prompt_sistema`, `get_contexto`) leyendo
  `reglas/instrucciones.md` y `reglas/contexto.md`, con las rutas resueltas de forma
  robusta (relativas a la raíz del proyecto, no al *cwd*).
- Se añade `.env.example` con todas las claves y valores por defecto, sin secretos.

### 4.3 `src/noticia/logging_setup.py`
- Función `configurar_logging(nivel=INFO)` que instala handlers de **consola** y de
  **fichero** (`produccion.log`, gitignored) con formato con timestamp y nivel.
- Se llama una vez desde `cli.py`.
- Los módulos obtienen su logger con `logging.getLogger("noticia.<modulo>")`.

### 4.4 Migración de `print` → `logging` y errores
- `generador.py`, `locutor.py`, `editor.py`, `cli.py`: sustituir `print(...)` por
  `logger.info/warning/error(...)`.
- Sustituir los `except:` desnudos por `except Exception as exc:` con `logger.warning/error`.
- **`ingesta.py` queda fuera** de esta migración: se reescribe entera en la Fase 1;
  tocarla ahora sería trabajo tirado.

### 4.5 `src/noticia/cli.py`
- Reemplaza `main.py`. La función del pipeline se renombra de `produccion_completa_pro()`
  a `producir_episodio()`, y una función `main()` llama a `configurar_logging()` y ejecuta
  el pipeline con `asyncio.run(...)`.
- Expuesto como comando `noticia` vía el script de entrada de `pyproject`.

### 4.6 `tests/`
- `pytest` configurado en `pyproject`.
- Smoke test: importar `noticia.config`, `noticia.ingesta`, `noticia.generador`,
  `noticia.locutor`, `noticia.editor`, `noticia.cli` sin error.
- Al menos un test de función pura como semilla (p. ej. verificar que `Settings` carga
  valores por defecto correctos con un `.env` simulado). Las suites TDD grandes vienen
  en cada fase de producto.

---

## 5. Limpieza (borrados)

| Elemento | Motivo |
|----------|--------|
| `test_5min.py` | Roto (no ejecuta nada); lo sustituye la carpeta `tests/` |
| `ROADMAP_PRO.md` | Sustituido por la hoja de ruta en `docs/superpowers/specs/` |
| `ensamblar_podcast` (en `editor.py`) | Función puente muerta; nadie la llama |
| `documentacion/workflow.md` + carpeta | Su contenido se consolida en `CLAUDE.md` |
| `main.py` | Sustituido por `src/noticia/cli.py` |
| `produccion.log` (trackeado) | Se destrackea (`git rm --cached`) y se añade a `.gitignore` |

---

## 6. `CLAUDE.md` del proyecto

Documento de instrucciones para trabajar el proyecto con Claude Code. Contenido mínimo:
- Qué es NoticIA y el flujo del pipeline (ingesta → guion → locución → edición → audio),
  absorbiendo el diagrama de `documentacion/workflow.md`.
- Estructura del paquete y dónde vive cada cosa.
- Cómo se ejecuta (`uv run noticia`) y cómo se corren los tests (`uv run pytest`).
- Convenciones: dominio en español, `logging` en vez de `print`, `except Exception`
  con log en vez de `except:` desnudo, `ruff` para formato/lint.
- Referencia a la hoja de ruta y al estado de las fases.

Las **skills** de Claude Code no se crean en esta fase; la primera con necesidad real
llegará en la Fase 2 ("generar episodio de prueba").

---

## 7. Criterio de aceptación

- `uv run noticia` arranca el pipeline igual que hoy hacía `python main.py`
  (mismo comportamiento funcional).
- `uv run pytest` pasa en verde (smoke tests + semilla).
- `uv run ruff check` y `uv run ruff format --check` pasan.
- No queda ningún `print` ni `except:` desnudo en `generador/locutor/editor/cli`.
- Los ficheros y carpetas de la sección 5 han desaparecido; `produccion.log` no está
  trackeado.

---

## 8. Fuera de alcance

- Cualquier cambio de comportamiento en ingesta, generador, locutor o editor.
- La reescritura de la ingesta (Fase 1) y el cambio a Claude (Fase 2).
- Crear skills de Claude Code (transversal, cuando haya necesidad).
- Empaquetado/publicación y orquestación (Fases 4 y 5).
