"""
Fixtures dos testes de integração entre agente-bot e agente-operador.

Diferente dos testes internos de cada módulo (`agente-operador/tests/`), aqui
o alvo é o contrato entre os dois: o cliente real do agente-bot
(`SessaoOperador`) conversando com o host real do agente-operador
(`service.host.start_host`), sem mock de protocolo dos dois lados.
"""
import os
import shutil
import socket
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).parent.parent
OPERADOR_SRC = ROOT / "agente-operador"
BOT_SRC = ROOT / "agente-bot" / "src"
for path in (OPERADOR_SRC, BOT_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pytest


@pytest.fixture
def isolated_secrets(tmp_path, monkeypatch):
    """Redireciona service.security (agente-operador) para um diretório .secrets descartável."""
    from service import security
    fake_dir = tmp_path / ".secrets"
    monkeypatch.setattr(security, "SECRETS_DIR", fake_dir)
    monkeypatch.setattr(security, "TOKEN_FILE", fake_dir / "ws_token.txt")
    monkeypatch.setattr(security, "CERT_FILE", fake_dir / "host_cert.pem")
    monkeypatch.setattr(security, "KEY_FILE", fake_dir / "host_key.pem")
    monkeypatch.delenv("OPERADOR_WS_TOKEN", raising=False)
    yield fake_dir
    shutil.rmtree(fake_dir, ignore_errors=True)


@pytest.fixture
def unused_tcp_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class FakeSignal:
    """Substitui um pyqtSignal — registra emissões sem precisar de QApplication."""

    def __init__(self):
        self.received = []

    def emit(self, *args):
        self.received.append(args)


class FakeBridge:
    def __init__(self):
        for name in [
            "show_notification", "show_qr_code", "login_error", "credentials_error",
            "execution_started", "execution_error", "session_count_changed",
            "task_removed", "show_window", "quit_app",
        ]:
            setattr(self, name, FakeSignal())


@pytest.fixture
async def running_host(isolated_secrets, unused_tcp_port):
    """Sobe o host real do agente-operador (WebSocket + TLS + auth) numa porta isolada."""
    import asyncio
    from service import host as host_module

    bridge = FakeBridge()
    task = asyncio.ensure_future(host_module.start_host(bridge, host="127.0.0.1", port=unused_tcp_port))
    await asyncio.sleep(0.3)
    yield bridge, unused_tcp_port
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
