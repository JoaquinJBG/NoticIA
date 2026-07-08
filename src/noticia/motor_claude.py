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
        "claude",
        "-p",
        "--model",
        settings.modelo_claude,
        "--append-system-prompt",
        system_prompt,
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
