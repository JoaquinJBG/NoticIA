import logging
from logging.handlers import RotatingFileHandler

from noticia import logging_setup


def test_configurar_logging_es_idempotente(tmp_path):
    ruta = tmp_path / "produccion.log"
    root = logging.getLogger()
    root.handlers.clear()  # el propio caplog de pytest ya deja handlers puestos

    logging_setup.configurar_logging(ruta_log=ruta)
    n = len(root.handlers)
    assert n >= 1

    logging_setup.configurar_logging(ruta_log=ruta)  # no debe duplicar handlers
    assert len(root.handlers) == n


def test_configurar_logging_usa_rotating_file_handler_con_limites(tmp_path):
    ruta = tmp_path / "produccion.log"
    root = logging.getLogger()
    root.handlers.clear()

    logging_setup.configurar_logging(ruta_log=ruta)

    ficheros = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    assert len(ficheros) == 1
    assert ficheros[0].maxBytes == 5_000_000
    assert ficheros[0].backupCount == 5


def test_configurar_logging_sin_ruta_log_no_anade_handler_de_fichero(tmp_path):
    root = logging.getLogger()
    root.handlers.clear()

    logging_setup.configurar_logging(ruta_log=None)
    assert not any(isinstance(h, logging.FileHandler) for h in root.handlers)


def test_anadir_log_fichero_escribe_y_quitar_handler_lo_detiene(tmp_path):
    ruta = tmp_path / "episodio.log"
    handler = logging_setup.anadir_log_fichero(ruta)
    logger = logging.getLogger("noticia.test_logging_setup")
    logger.warning("primero")

    logging_setup.quitar_handler(handler)
    logger.warning("segundo, no debería aparecer")

    contenido = ruta.read_text(encoding="utf-8")
    assert "primero" in contenido
    assert "segundo" not in contenido


def test_anadir_log_fichero_crea_las_carpetas_intermedias(tmp_path):
    ruta = tmp_path / "episodios" / "2026-09-24" / "produccion.log"
    handler = logging_setup.anadir_log_fichero(ruta)

    logging_setup.quitar_handler(handler)
    assert ruta.parent.exists()


def test_quitar_handler_lo_retira_del_logger_raiz(tmp_path):
    ruta = tmp_path / "episodio.log"
    handler = logging_setup.anadir_log_fichero(ruta)
    assert handler in logging.getLogger().handlers

    logging_setup.quitar_handler(handler)
    assert handler not in logging.getLogger().handlers
