import os
import shutil
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest


@pytest.fixture(scope="session")
def qapp():
    """QApplication único por sessão de testes — Qt não permite mais de uma instância por processo."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def isolated_secrets(tmp_path, monkeypatch):
    """Redireciona service.security para um diretório .secrets descartável, sem tocar no real do projeto."""
    from service import security
    fake_dir = tmp_path / ".secrets"
    monkeypatch.setattr(security, "SECRETS_DIR", fake_dir)
    monkeypatch.setattr(security, "TOKEN_FILE", fake_dir / "ws_token.txt")
    monkeypatch.setattr(security, "CERT_FILE", fake_dir / "host_cert.pem")
    monkeypatch.setattr(security, "KEY_FILE", fake_dir / "host_key.pem")
    monkeypatch.delenv("OPERADOR_WS_TOKEN", raising=False)
    yield fake_dir
    shutil.rmtree(fake_dir, ignore_errors=True)
