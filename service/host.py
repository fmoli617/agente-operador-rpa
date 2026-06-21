"""
WebSocket host — torna a maquina um endpoint para receber tarefas.
Porta padrao: 8765 (wss://, TLS autoassinado — ver service/security.py)

Handshake obrigatório, primeira mensagem da conexão:
  { "type": "auth", "token": "..." }
Conexão é encerrada se o token não bater com o esperado (ver README, seção Segurança).

Protocolo consumidor → operador:
  { "task_id": "...", "host": "...", "process": "...", "message": "..." }
  { "task_id": "...", "type": "qr_code", "image": "<base64 PNG>" }

Protocolo operador → consumidor:
  { "task_id": "...", "type": "credentials", "user": "...", "password": "..." }
  { "task_id": "...", "type": "code", "code": "..." }

Retrocompativel com { "title": "...", "message": "..." }.
"""
import asyncio
import json
import websockets

from domain.ports import TaskResponder
from service.logger import get_logger
from service.security import get_auth_token, get_client_ssl_context, get_server_ssl_context

ALREADY_RUNNING = "already_running"
AUTH_TIMEOUT = 10  # segundos para receber o token após conectar

_logger = get_logger(__name__)

_pending: dict = {}   # task_id -> websocket
_loop: asyncio.AbstractEventLoop | None = None


class WebSocketTaskResponder(TaskResponder):
    """Implementação da porta de domínio TaskResponder usando o transporte WebSocket deste módulo."""

    def send_credentials(self, task_id: str, user: str, password: str) -> None:
        send_response(task_id, {"task_id": task_id, "type": "credentials", "user": user, "password": password})

    def send_code(self, task_id: str, code: str) -> None:
        send_response(task_id, {"task_id": task_id, "type": "code", "code": code})


def send_response(task_id: str, payload: dict):
    """Chamado da thread Qt — envia resposta ao consumidor que aguarda."""
    if _loop is None:
        return
    ws = _pending.get(task_id)
    if ws is None:
        return
    asyncio.run_coroutine_threadsafe(_send(ws, payload), _loop)


async def _send(ws, payload: dict):
    try:
        await ws.send(json.dumps(payload))
    except Exception:
        pass


async def start_host(bridge, host: str = "0.0.0.0", port: int = 8765):
    global _loop
    _loop = asyncio.get_event_loop()
    connected = set()
    token = get_auth_token()

    async def _authenticate(websocket) -> bool:
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=AUTH_TIMEOUT)
        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
            return False
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return False
        if data.get("type") != "auth" or data.get("token") != token:
            await _send(websocket, {"type": "auth_error", "message": "Token inválido."})
            _logger.warning("autenticação rejeitada de %s", websocket.remote_address)
            return False
        return True

    async def handler(websocket):
        if not await _authenticate(websocket):
            await websocket.close(code=4001, reason="Unauthorized")
            return
        _logger.info("conexão autenticada: %s", websocket.remote_address)
        connected.add(websocket)
        bridge.session_count_changed.emit(len(connected))
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                    task_id = data.get("task_id", "")
                    msg_type = data.get("type", "")

                    # QR code enviado pelo consumidor para exibir ao operador
                    if msg_type == "qr_code":
                        image_b64 = data.get("image", "")
                        bridge.show_qr_code.emit(task_id, image_b64)
                        continue

                    if msg_type == "login_error":
                        bridge.login_error.emit(task_id, data.get("message", "Erro de login."))
                        continue

                    if msg_type == "credentials_error":
                        bridge.credentials_error.emit(task_id, data.get("message", "Usuário ou senha incorretos."))
                        continue

                    if msg_type == "execution_started":
                        bridge.execution_started.emit(task_id)
                        continue

                    if msg_type == "execution_error":
                        bridge.execution_error.emit(task_id, data.get("message", "Erro não esperado."))
                        continue

                    if msg_type == "show_window":
                        bridge.show_window.emit()
                        continue

                    # Nova tarefa
                    host_name = data.get("host", "")
                    process = data.get("process", "")
                    if host_name and process:
                        title = f"{host_name} - {process}"
                    else:
                        title = data.get("title", "Operação Assistida")

                    message = data.get("message", "")

                    if task_id:
                        _pending[task_id] = websocket

                    _logger.info("nova tarefa recebida: task_id=%s title=%r", task_id, title)
                    bridge.show_notification.emit(title, message, task_id)
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            connected.discard(websocket)
            bridge.session_count_changed.emit(len(connected))
            dead = [k for k, v in _pending.items() if v is websocket]
            for k in dead:
                del _pending[k]
                bridge.task_removed.emit(k)
            _logger.info("conexão encerrada: %s", websocket.remote_address)

    ssl_context = get_server_ssl_context()
    try:
        async with websockets.serve(handler, host, port, ssl=ssl_context):
            _logger.info("host WebSocket iniciado em wss://%s:%s", host, port)
            await asyncio.Future()
    except OSError:
        _logger.info("porta %s já em uso — outra instância está ativa", port)
        await _ping_existing(port)
        return ALREADY_RUNNING


async def _ping_existing(port: int):
    try:
        uri = f"wss://127.0.0.1:{port}"
        async with websockets.connect(uri, ssl=get_client_ssl_context()) as ws:
            await ws.send(json.dumps({"type": "auth", "token": get_auth_token()}))
            await ws.send(json.dumps({"type": "show_window"}))
    except Exception:
        pass
