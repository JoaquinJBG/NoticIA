import logging

from noticia.logging_setup import configurar_logging


def test_configurar_logging_es_idempotente():
    logging.getLogger().handlers.clear()
    configurar_logging()
    n = len(logging.getLogger().handlers)
    assert n >= 1
    configurar_logging()  # segunda llamada no debe duplicar handlers
    assert len(logging.getLogger().handlers) == n
