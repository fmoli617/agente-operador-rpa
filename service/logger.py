"""
Logger central do app — grava logs diários em %LOCALAPPDATA%\\OperacaoAssistida\\logs\\,
com rotação automática à meia-noite (mesmo padrão de diretório usado por service/security.py).

Uso: logger = get_logger(__name__); logger.info("...")
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "OperacaoAssistida"
LOG_DIR = DATA_DIR / "logs"

_ROOT_NAME = "operacao_assistida"
_configured = False


def configure_logging() -> None:
    """Liga a gravação em disco — chamar uma única vez, no bootstrap do app (main.py).

    Deliberadamente separado de get_logger(): módulos pedem seu logger no import
    (custo zero, sem tocar em disco); só o composition root decide quando o
    arquivo de log passa a existir, para não criar a pasta durante os testes.
    """
    global _configured
    if _configured:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        LOG_DIR / "operacao_assistida.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger(_ROOT_NAME)
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Logger filho de 'operacao_assistida' — name costuma ser o __name__ do módulo chamador."""
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
