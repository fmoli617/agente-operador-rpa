from service import logger


def test_get_logger_does_not_touch_disk_before_configure(isolated_logs):
    logger.get_logger("algum_modulo")
    assert not isolated_logs.exists()


def test_configure_logging_creates_daily_log_file(isolated_logs):
    logger.configure_logging()
    log = logger.get_logger("algum_modulo")
    log.info("evento de teste")

    assert isolated_logs.exists()
    log_file = isolated_logs / "operacao_assistida.log"
    assert log_file.exists()
    assert "evento de teste" in log_file.read_text(encoding="utf-8")


def test_configure_logging_is_idempotent(isolated_logs):
    logger.configure_logging()
    logger.configure_logging()
    root = __import__("logging").getLogger(logger._ROOT_NAME)
    assert len(root.handlers) == 1
