import logging
import subprocess
import tempfile

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

    Se ejecuta con `cwd` en un directorio temporal vacío para que `claude -p`
    no descubra el CLAUDE.md ni la configuración del propio proyecto NoticIA
    como contexto ambiental.

    `--tools ""` desactiva todas las herramientas: sin ellas Claude no puede
    actuar como agente (escribir el guion a un fichero y devolver un resumen)
    y se limita a generar el texto pedido.
    """
    cmd = [
        "claude",
        "-p",
        "--model",
        settings.modelo_claude,
        "--tools",
        "",
        "--append-system-prompt",
        system_prompt,
    ]
    try:
        with tempfile.TemporaryDirectory() as directorio_aislado:
            proc = subprocess.run(
                cmd,
                input=user_prompt,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SEGUNDOS,
                cwd=directorio_aislado,
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
