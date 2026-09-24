import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_LOG_FILE = ROOT / "produccion.log"
_FORMATO = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configurar_logging(nivel: int = logging.INFO, ruta_log: Path | None = _LOG_FILE) -> None:
    """Configura logging de consola y, si `ruta_log` no es None, de fichero.

    El fichero rota (5 MB, 5 copias) para no crecer sin límite. Idempotente:
    si el logger raíz ya tiene handlers, no hace nada.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(nivel)

    consola = logging.StreamHandler()
    consola.setFormatter(logging.Formatter(_FORMATO))
    root.addHandler(consola)

    if ruta_log is not None:
        fichero = RotatingFileHandler(ruta_log, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        fichero.setFormatter(logging.Formatter(_FORMATO))
        root.addHandler(fichero)


def anadir_log_fichero(ruta: Path) -> logging.Handler:
    """Añade al logger raíz un handler de fichero (el log de un episodio)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(ruta, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_FORMATO))
    logging.getLogger().addHandler(handler)
    return handler


def quitar_handler(handler: logging.Handler) -> None:
    """Retira del logger raíz un handler añadido antes y lo cierra."""
    logging.getLogger().removeHandler(handler)
    handler.close()
