# Fase 2 — Cerebro Claude (Max vía CLI headless) — Design

**Fecha:** 2026-07-08
**Estado:** Aprobada
**Roadmap:** `docs/superpowers/specs/2026-07-08-rework-roadmap.md` (Fase 2)

---

## Objetivo

Sustituir el motor del guion (Groq / Llama 3.3) por **Claude vía suscripción Max**,
invocado en modo headless con el CLI `claude -p`. Es una **rebanada fina**: se cambia
solo el backend de generación manteniendo la estructura actual por bloques, y se valida
la calidad en un episodio real mediante una salida "solo guion".

**No** entran en esta fase (siguiente iteración):
- Contraste a ciegas consumiendo los **clusters** de `agrupador.agrupar()`.
- Química / interrupciones avanzadas entre Álex y Santi.
- La **skill** completa de Claude Code "generar episodio de prueba".

## Decisiones cerradas

| Tema | Decisión |
|------|----------|
| Alcance | Rebanada fina: cambiar solo el motor, estructura por bloques intacta |
| Mecanismo | CLI `claude -p` como subproceso (usa el login de Max, sin API key) |
| Modelo | `sonnet`, configurable en `Settings` (`modelo_claude`, default `"sonnet"`) |
| System prompt | `--append-system-prompt` (la persona se añade encima del system de Claude Code) |
| Groq | Se elimina del todo: dependencia `groq`, código muerto y el fail-fast de `GROQ_API_KEY` |
| Validación | Modo `--solo-guion`: ingesta + generador → fichero, sin TTS ni audio |
| `temperature` | Se pierde (el CLI no la expone); aceptable en la rebanada |

## Arquitectura

```
src/noticia/
  motor_claude.py   (NUEVO)  → generar_texto(system, user) -> str vía `claude -p`
  generador.py      (CAMBIA) → llamar_ia() delega en motor_claude; estructura intacta
  config.py         (CAMBIA) → + modelo_claude; groq_api_key deja de ser obligatoria
  cli.py            (CAMBIA) → argparse con modo --solo-guion
```

Cada unidad tiene una responsabilidad clara:
- `motor_claude` solo invoca el CLI y devuelve texto. No sabe de bloques ni personalidades.
  Mockeable en tests.
- `generador` conserva intro / (briefing + tertulia) por bloque / outro, y el post-proceso
  que limpia markdown. Solo cambia el backend de `llamar_ia()`.

## `motor_claude.py`

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

    - Binario ausente o sin sesión de Max -> RuntimeError claro.
    - Fallo transitorio de una llamada -> log + devuelve "" (el generador tolera
      bloques vacíos).
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
            "Claude CLI no disponible: instala/inicia sesión en Claude (Max)."
        ) from exc
    except subprocess.TimeoutExpired:
        logger.warning("Claude agotó el timeout de %ss", TIMEOUT_SEGUNDOS)
        return ""

    if proc.returncode != 0:
        # returncode != 0 típico: no hay sesión de Max iniciada.
        logger.error("claude -p falló (rc=%s): %s", proc.returncode, proc.stderr.strip())
        return ""

    return proc.stdout.strip()
```

Nota de diseño: distinguimos **binario ausente** (error de configuración → `RuntimeError`,
aborta la producción) de **fallo de una llamada** (transitorio → `""`, bloque vacío). Un
`returncode != 0` por falta de sesión se registra pero no aborta; si TODOS los bloques
salen vacíos, el pipeline ya avisa ("No se generaron audios"). En modo `--solo-guion` un
guion vacío es señal clara de que algo va mal.

## `generador.py`

- Se elimina el cliente Groq (`Groq`, `_get_client`, `MODELO_GROQ`) y su import.
- `llamar_ia(system_prompt, user_prompt)` pasa a delegar en
  `motor_claude.generar_texto(system_prompt, user_prompt)`. Se **elimina** el parámetro
  `temperature` (el CLI no lo expone) y se actualizan las 2 llamadas que hoy lo pasan
  (`generar_briefing_contexto` con 0.5 y el default 0.85): código más honesto.
- El resto (`construir_guion`, `generar_briefing_contexto`, `construir_bloque_con_contexto`,
  `generar_intro`, `generar_outro`) no cambia salvo esa llamada.

## `config.py` y `cli.py`

- `config.py`: `modelo_claude: str = "sonnet"`. `groq_api_key` se conserva como opcional
  (evita romper `.env`) pero ya no se usa.
- `cli.py`:
  - Se elimina el guard `if settings.groq_api_key is None: raise ...`.
  - `main()` usa `argparse`: `--solo-guion` y `--salida RUTA` opcional.
  - Sin flag → `producir_episodio()` (episodio completo, igual que hoy).
  - Con `--solo-guion` → `generar_solo_guion(salida)`: `obtener_noticias()` +
    `construir_guion()` y vuelca el guion a fichero (default `output/guion_<fecha>.md`),
    sin locución ni mastering.

### Formato del fichero de guion

Markdown con un encabezado por bloque y el diálogo debajo, en el orden intro → bloques →
outro. Suficiente para leer y juzgar calidad.

## Testing (determinista, sin red ni Claude real)

| Test | Qué verifica |
|------|--------------|
| `test_motor_claude.py` | Mock de `subprocess.run`: args correctos (`--model`, `--append-system-prompt`), prompt por stdin, parseo de stdout; ramas de error (FileNotFoundError→RuntimeError, returncode≠0→"", timeout→"") |
| `test_generador.py` | Mock de `motor_claude.generar_texto`: `construir_guion` mantiene estructura (intro/bloques/outro) y limpia markdown |
| `test_cli.py` (amplía) | Mock de ingesta+generador: `--solo-guion` escribe el fichero y NO invoca audio |

## Verificación de la fase

- Suite verde (`uv run pytest`), `ruff check` y `ruff format --check` limpios.
- Validación manual: `uv run noticia --solo-guion` genera un guion real y se lee para
  juzgar el salto de calidad frente a Groq.

## Riesgos / notas

- ~14 invocaciones de `claude -p` por episodio (una por briefing/bloque + intro/outro).
  Cada una arranca un subproceso; en la práctica es 1 episodio/día por la tarde, dentro
  de los límites de Max. Si Sonnet se queda corto de cuota, `modelo_claude` permite ajustar.
- Latencia mayor que Groq (arranque de subproceso + modelo); irrelevante para un batch diario.
- Pérdida de `temperature` como palanca; si se echa en falta, se revisa en una iteración
  posterior (el CLI no la expone).
