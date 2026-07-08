# Cerebro Claude (Fase 2 — rebanada fina) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sustituir el motor del guion (Groq/Llama) por Claude vía el CLI headless `claude -p`, manteniendo la estructura por bloques, y añadir un modo `--solo-guion` para validar la calidad.

**Architecture:** Un módulo nuevo `motor_claude.py` aísla la invocación del CLI (`claude -p`, prompt de usuario por stdin, system por `--append-system-prompt`). `generador.py` deja de usar Groq y delega en ese módulo sin tocar su estructura (intro / briefing+tertulia por bloque / outro). `cli.py` añade `--solo-guion`, que corre ingesta+generador y vuelca el guion a fichero sin audio.

**Tech Stack:** Python 3.12, `subprocess` (stdlib), `argparse` (stdlib), `pytest`, `uv`, `ruff`. El CLI `claude` (v2.x) debe estar instalado y con sesión de Max.

## Global Constraints

- Dominio en **español** (nombres de funciones y variables).
- **`logging`**, nunca `print`; logger vía `logging.getLogger("noticia.<modulo>")`.
- Nada de `except:` desnudo: `except Exception as exc:` (o excepción concreta) con log.
- Config vía `from noticia.config import settings`, no `os.getenv` suelto.
- `uv` para todo: `uv run pytest`, `uv run ruff check`, `uv add/remove`.
- Cada tarea termina con `uv run ruff check` y `uv run ruff format` limpios antes del commit.
- Commits: Conventional Commits en **español**, **sin** trailer `Co-Authored-By`.
- Todos los tests deterministas y sin red ni Claude real (mock de `subprocess` / `motor_claude` / ingesta).

---

## Task 1: `motor_claude.py` — wrapper del CLI `claude -p`

**Files:**
- Create: `src/noticia/motor_claude.py`
- Modify: `src/noticia/config.py` (añadir `modelo_claude`)
- Test: `tests/test_motor_claude.py`

**Interfaces:**
- Consumes: `settings.modelo_claude` (str) de `noticia.config`.
- Produces: `generar_texto(system_prompt: str, user_prompt: str) -> str`.

- [ ] **Step 1: Añadir `modelo_claude` a `Settings`**

En `src/noticia/config.py`, dentro de `class Settings`, después de la línea `gemini_api_key: str | None = None`, añadir:

```python
    modelo_claude: str = "sonnet"
```

- [ ] **Step 2: Escribir los tests que fallan**

Crear `tests/test_motor_claude.py`:

```python
import subprocess

import pytest

from noticia import motor_claude


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_generar_texto_construye_cmd_y_pasa_stdin(monkeypatch):
    capturado = {}

    def fake_run(cmd, **kw):
        capturado["cmd"] = cmd
        capturado["input"] = kw["input"]
        return _Proc(returncode=0, stdout="  respuesta  \n")

    monkeypatch.setattr(motor_claude.subprocess, "run", fake_run)
    out = motor_claude.generar_texto("SYS", "USER")

    assert out == "respuesta"  # stdout .strip()
    assert capturado["input"] == "USER"  # user por stdin
    cmd = capturado["cmd"]
    assert cmd[0] == "claude" and "-p" in cmd
    i = cmd.index("--append-system-prompt")
    assert cmd[i + 1] == "SYS"
    j = cmd.index("--model")
    assert cmd[j + 1] == "sonnet"  # default de settings


def test_generar_texto_returncode_no_cero_devuelve_vacio(monkeypatch):
    monkeypatch.setattr(
        motor_claude.subprocess, "run",
        lambda cmd, **kw: _Proc(returncode=1, stderr="Invalid API key / no session"),
    )
    assert motor_claude.generar_texto("s", "u") == ""


def test_generar_texto_sin_binario_lanza_runtimeerror(monkeypatch):
    def boom(cmd, **kw):
        raise FileNotFoundError()

    monkeypatch.setattr(motor_claude.subprocess, "run", boom)
    with pytest.raises(RuntimeError):
        motor_claude.generar_texto("s", "u")


def test_generar_texto_timeout_devuelve_vacio(monkeypatch):
    def boom(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr(motor_claude.subprocess, "run", boom)
    assert motor_claude.generar_texto("s", "u") == ""
```

- [ ] **Step 3: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_motor_claude.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'noticia.motor_claude'`.

- [ ] **Step 4: Implementar `src/noticia/motor_claude.py`**

```python
import logging
import subprocess

from noticia.config import settings

logger = logging.getLogger("noticia.motor_claude")

TIMEOUT_SEGUNDOS = 180


def generar_texto(system_prompt: str, user_prompt: str) -> str:
    """Genera texto con Claude vía el CLI headless (`claude -p`).

    El prompt de usuario va por stdin; el de sistema por --append-system-prompt.
    Sin shell (lista de args) -> sin inyección.

    - Binario ausente -> RuntimeError (error de configuración; aborta).
    - returncode != 0 (p. ej. sin sesión de Max) o timeout -> log + "".
      El generador tolera bloques vacíos.
    """
    cmd = [
        "claude", "-p",
        "--model", settings.modelo_claude,
        "--append-system-prompt", system_prompt,
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=user_prompt,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEGUNDOS,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Claude CLI no disponible: instala e inicia sesión en Claude (Max)."
        ) from exc
    except subprocess.TimeoutExpired:
        logger.warning("Claude agotó el timeout de %ss", TIMEOUT_SEGUNDOS)
        return ""

    if proc.returncode != 0:
        logger.error("claude -p falló (rc=%s): %s", proc.returncode, proc.stderr.strip())
        return ""

    return proc.stdout.strip()
```

- [ ] **Step 5: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_motor_claude.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Lint y formato**

Run: `uv run ruff check src/noticia/motor_claude.py src/noticia/config.py tests/test_motor_claude.py && uv run ruff format src/noticia/motor_claude.py tests/test_motor_claude.py`
Expected: `All checks passed!` y sin reformateos pendientes (re-ejecuta `ruff format --check` si hace falta).

- [ ] **Step 7: Commit**

```bash
git add src/noticia/motor_claude.py src/noticia/config.py tests/test_motor_claude.py
git commit -m "feat: motor de guion con Claude vía CLI headless"
```

---

## Task 2: `generador.py` — cambiar el motor a Claude y quitar Groq

**Files:**
- Modify: `src/noticia/generador.py`
- Modify: `pyproject.toml` (quitar `groq` con `uv remove`)
- Test: `tests/test_generador.py`

**Interfaces:**
- Consumes: `motor_claude.generar_texto(system, user) -> str` (Task 1).
- Produces: `llamar_ia(system_prompt: str, user_prompt: str) -> str` y
  `construir_guion(datos_noticias: dict) -> dict[str, list[str]]` (sin cambios de firma
  salvo que `llamar_ia` pierde `temperature`).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_generador.py`:

```python
from noticia import generador


def test_llamar_ia_delega_en_motor(monkeypatch):
    llamado = {}

    def fake(system, user):
        llamado["args"] = (system, user)
        return "ok"

    monkeypatch.setattr(generador, "generar_texto", fake)
    assert generador.llamar_ia("SYS", "USER") == "ok"
    assert llamado["args"] == ("SYS", "USER")


def test_construir_guion_mantiene_estructura_y_limpia_markdown(monkeypatch):
    monkeypatch.setattr(generador, "llamar_ia", lambda s, u: "Álex: hola **fuerte**")
    datos = {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]}

    guion = generador.construir_guion(datos)

    assert "intro" in guion and "outro" in guion
    assert "espana" in guion
    assert guion["espana"] and "**" not in guion["espana"][0]
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_generador.py -v`
Expected: FAIL — `AttributeError: module 'noticia.generador' has no attribute 'generar_texto'` (Groq aún importado, `generar_texto` no).

- [ ] **Step 3a: Reescribir la cabecera de `src/noticia/generador.py`**

Ojo: en el fichero actual, `construir_guion` está ENTRE `_get_client` y `llamar_ia`, así que hay que hacer dos edits separados sin tocar `construir_guion`.

Primer edit — reemplazar TODO el bloque superior, desde `import logging` (línea 1) hasta el final de `_get_client` (justo antes de `def construir_guion`), por:

```python
import logging

from noticia.config import get_contexto, get_prompt_sistema
from noticia.motor_claude import generar_texto

logger = logging.getLogger("noticia.generador")
```

Esto elimina `from groq import Groq`, el `settings` del import de config, `MODELO_GROQ`, `_client` y `_get_client`.

- [ ] **Step 3b: Reescribir `llamar_ia`**

Segundo edit — reemplazar la función `llamar_ia` completa (el `def llamar_ia(...)` con su `try/except` que llama a Groq) por:

```python
def llamar_ia(system_prompt, user_prompt):
    return generar_texto(system_prompt, user_prompt)
```

**No** se tocan `construir_guion`, `generar_briefing_contexto`, `construir_bloque_con_contexto`, `generar_intro` ni `generar_outro`.

- [ ] **Step 4: Quitar la `temperature` de la única llamada que la pasa**

En `src/noticia/generador.py`, dentro de `generar_briefing_contexto`, cambiar:

```python
    return llamar_ia(prompt_sistema, prompt_usuario, temperature=0.5)
```

por:

```python
    return llamar_ia(prompt_sistema, prompt_usuario)
```

(Las llamadas de `construir_bloque_con_contexto`, `generar_intro` y `generar_outro` ya no pasan `temperature`, así que no cambian.)

- [ ] **Step 5: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_generador.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Quitar la dependencia `groq`**

Run: `uv remove groq`
Expected: `groq` desaparece de `pyproject.toml` y de `uv.lock`.

- [ ] **Step 7: Verificar que no queda ningún uso de groq en el generador**

Run: `grep -rn "groq\|Groq" src/noticia/generador.py`
Expected: sin resultados. (En `config.py` sí permanece `groq_api_key` como campo opcional; eso es intencionado y no se toca.)

- [ ] **Step 8: Lint, formato y suite completa**

Run: `uv run ruff check && uv run ruff format --check && uv run pytest -q`
Expected: `All checks passed!`, sin reformateos, y todos los tests verdes.

- [ ] **Step 9: Commit**

```bash
git add src/noticia/generador.py tests/test_generador.py pyproject.toml uv.lock
git commit -m "feat: generar el guion con Claude y eliminar Groq del generador"
```

---

## Task 3: `cli.py` — modo `--solo-guion` y quitar el fail-fast de Groq

**Files:**
- Modify: `src/noticia/cli.py`
- Test: `tests/test_cli.py` (reemplaza el test obsoleto de la clave Groq)

**Interfaces:**
- Consumes: `obtener_noticias()`, `construir_guion()`, `settings.carpeta_output`.
- Produces: `generar_solo_guion(salida: str | None = None) -> str` y un `main()` con
  `argparse` que enruta a `producir_episodio()` o a `generar_solo_guion()`.

- [ ] **Step 1: Escribir el test que falla y borrar el obsoleto**

Reemplazar TODO el contenido de `tests/test_cli.py` por:

```python
from noticia import cli


def test_solo_guion_escribe_fichero_y_no_toca_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cli, "obtener_noticias",
        lambda: {"espana": [{"titular": "T", "resumen": "", "fuente": "f"}]},
    )
    monkeypatch.setattr(
        cli, "construir_guion",
        lambda noticias: {
            "intro": ["Álex: hola"],
            "espana": ["Álex: bla bla"],
            "outro": ["Santi: chao"],
        },
    )
    salida = tmp_path / "guion.md"

    ruta = cli.generar_solo_guion(str(salida))

    assert ruta == str(salida)
    contenido = salida.read_text(encoding="utf-8")
    assert "## intro" in contenido
    assert "## espana" in contenido
    assert "Álex: bla bla" in contenido


def test_formatear_guion_respeta_orden_y_omite_vacios():
    guion = {"outro": ["fin"], "intro": ["ini"], "espana": []}
    texto = cli._formatear_guion(guion)
    # intro antes que outro; espana vacío se omite
    assert texto.index("## intro") < texto.index("## outro")
    assert "## espana" not in texto
```

(Se elimina `test_producir_episodio_falla_sin_clave`: el guard de Groq desaparece en esta tarea.)

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `AttributeError: module 'noticia.cli' has no attribute 'generar_solo_guion'`.

- [ ] **Step 3: Añadir imports, `_formatear_guion` y `generar_solo_guion` a `src/noticia/cli.py`**

En la cabecera de `src/noticia/cli.py`, añadir a los imports existentes:

```python
import argparse
from datetime import datetime, timezone
from pathlib import Path
```

Y añadir estas dos funciones (por ejemplo, justo antes de `def main():`):

```python
_ORDEN_BLOQUES = [
    "intro", "espana", "geopolitica", "ia_y_actualidad",
    "ciencia", "friki", "futbol", "outro",
]


def _formatear_guion(guion: dict) -> str:
    """Renderiza el guion a Markdown: un encabezado por bloque, en orden."""
    partes = []
    for bloque in _ORDEN_BLOQUES:
        lineas = guion.get(bloque)
        if not lineas:
            continue
        partes.append(f"## {bloque}\n\n" + "\n".join(lineas))
    return "\n\n".join(partes) + "\n"


def generar_solo_guion(salida: str | None = None) -> str:
    """Corre ingesta + generación y vuelca el guion a fichero, sin audio."""
    logger.info("Modo solo-guion: ingesta + generación, sin locución ni mastering.")
    os.makedirs(settings.carpeta_output, exist_ok=True)
    noticias = obtener_noticias()
    guion = construir_guion(noticias)

    if salida is None:
        fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        salida = os.path.join(settings.carpeta_output, f"guion_{fecha}.md")

    Path(salida).write_text(_formatear_guion(guion), encoding="utf-8")
    logger.info("Guion escrito en %s", salida)
    return salida
```

- [ ] **Step 4: Quitar el guard de Groq de `producir_episodio`**

En `src/noticia/cli.py`, eliminar estas líneas de `producir_episodio`:

```python
    if settings.groq_api_key is None:
        raise RuntimeError("Falta GROQ_API_KEY en el .env: configúrala antes de ejecutar.")
```

- [ ] **Step 5: Enrutar `main()` con `argparse`**

Reemplazar la función `main()` por:

```python
def main():
    configurar_logging()
    parser = argparse.ArgumentParser(
        prog="noticia", description="Podcast diario automatizado con IA"
    )
    parser.add_argument(
        "--solo-guion", action="store_true",
        help="Genera solo el guion (sin audio) y lo vuelca a un fichero.",
    )
    parser.add_argument(
        "--salida", help="Ruta del fichero de guion (solo con --solo-guion).",
    )
    args = parser.parse_args()

    if args.solo_guion:
        generar_solo_guion(args.salida)
    else:
        asyncio.run(producir_episodio())
```

- [ ] **Step 6: Ejecutar y verificar que pasa**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Lint, formato y suite completa**

Run: `uv run ruff check && uv run ruff format --check && uv run pytest -q`
Expected: `All checks passed!`, sin reformateos, todos los tests verdes.

- [ ] **Step 8: Verificación de import (sin ejecutar el pipeline real)**

Run: `uv run python -c "from noticia import cli, generador, motor_claude; print('imports OK')"`
Expected: `imports OK`.

- [ ] **Step 9: Commit**

```bash
git add src/noticia/cli.py tests/test_cli.py
git commit -m "feat: modo --solo-guion y fin del fail-fast de Groq"
```

---

## Verificación final de la fase (manual, tras las 3 tareas)

- [ ] `uv run noticia --solo-guion` genera un guion real con Claude y lo escribe en `output/guion_<fecha>.md`.
- [ ] Leer el guion y juzgar el salto de calidad frente a Groq.

> Requiere sesión de Max activa en la máquina. Si `claude` no está logueado, los bloques
> saldrán vacíos (returncode ≠ 0 registrado en el log); iniciar sesión y reintentar.

---

## Notas para el ejecutor

- No se tocan `locutor.py` ni `editor.py`.
- `config.py` conserva `groq_api_key` como opcional (no romper `.env` existentes); simplemente deja de usarse.
- El parámetro `temperature` desaparece a propósito: `claude -p` no lo expone.
- Fuera de alcance (siguiente iteración): consumir los **clusters** de `agrupador.agrupar()` para el contraste a ciegas, química avanzada y la **skill** "generar episodio de prueba".
