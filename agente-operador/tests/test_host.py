import asyncio
import json

import pytest
import websockets

from service import host as host_module
from service import security


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

    def respond(self, task_id, payload):
        pass


@pytest.fixture
async def running_host(isolated_secrets, unused_tcp_port):
    bridge = FakeBridge()
    task = asyncio.ensure_future(host_module.start_host(bridge, host="127.0.0.1", port=unused_tcp_port))
    await asyncio.sleep(0.3)  # tempo do servidor subir
    yield bridge, unused_tcp_port
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.fixture
def unused_tcp_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def _connect(port):
    return websockets.connect(f"wss://127.0.0.1:{port}", ssl=security.get_client_ssl_context())


async def test_connection_without_auth_is_rejected(running_host):
    bridge, port = running_host
    async with await _connect(port) as ws:
        await ws.send(json.dumps({"task_id": "t1", "host": "X", "process": "Y"}))
        with pytest.raises(websockets.exceptions.ConnectionClosed):
            while True:
                await asyncio.wait_for(ws.recv(), timeout=3)


async def test_connection_with_wrong_token_is_rejected(running_host):
    bridge, port = running_host
    async with await _connect(port) as ws:
        await ws.send(json.dumps({"type": "auth", "token": "token-invalido"}))
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
        assert msg["type"] == "auth_error"
        with pytest.raises(websockets.exceptions.ConnectionClosed):
            await asyncio.wait_for(ws.recv(), timeout=3)


async def test_full_task_flow_with_valid_token(running_host):
    bridge, port = running_host
    token = security.get_auth_token()
    async with await _connect(port) as ws:
        await ws.send(json.dumps({"type": "auth", "token": token}))
        await ws.send(json.dumps({"task_id": "task-abc", "host": "SRV1", "process": "Login"}))
        await ws.send(json.dumps({"task_id": "task-abc", "type": "qr_code", "image": "AAAA"}))
        await ws.send(json.dumps({"task_id": "task-abc", "type": "execution_started"}))
        await asyncio.sleep(0.3)

    await asyncio.sleep(0.2)  # tempo do handler processar a desconexão

    assert bridge.show_notification.received == [("SRV1 - Login", "", "task-abc", "SRV1")]
    assert bridge.show_qr_code.received == [("task-abc", "AAAA")]
    assert bridge.execution_started.received == [("task-abc",)]
    assert bridge.task_removed.received == [("task-abc",)]


async def test_session_count_tracks_connections(running_host):
    bridge, port = running_host
    async with await _connect(port) as ws:
        await ws.send(json.dumps({"type": "auth", "token": security.get_auth_token()}))
        await asyncio.sleep(0.2)
        assert bridge.session_count_changed.received[-1] == (1,)

    await asyncio.sleep(0.2)
    assert bridge.session_count_changed.received[-1] == (0,)
