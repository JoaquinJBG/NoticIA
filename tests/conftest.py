"""Fixtures compartidas: aíslan el logging entre tests.

Sin esto, cualquier test que llame a `configurar_logging` (o añada un
handler de fichero) deja el logger raíz contaminado para el resto de la
sesión, y puede llegar a escribir en el `produccion.log` real del repo.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def _aislar_logging():
    root = logging.getLogger()
    handlers_originales = list(root.handlers)
    nivel_original = root.level

    yield

    for handler in list(root.handlers):
        if handler not in handlers_originales:
            root.removeHandler(handler)
            handler.close()
    root.handlers = handlers_originales
    root.setLevel(nivel_original)


@pytest.fixture(scope="session", autouse=True)
def _vigilar_produccion_log_real():
    """Falla si la suite completa termina habiendo escrito en el
    `produccion.log` real del repo (en vez de en un `tmp_path`)."""
    from noticia.logging_setup import _LOG_FILE

    mtime_antes = _LOG_FILE.stat().st_mtime if _LOG_FILE.exists() else None

    yield

    mtime_despues = _LOG_FILE.stat().st_mtime if _LOG_FILE.exists() else None
    assert mtime_despues == mtime_antes, (
        "la suite ha escrito en el produccion.log real; usa tmp_path en el test"
    )
