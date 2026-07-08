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
