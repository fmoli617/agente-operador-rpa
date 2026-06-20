"""
WebSocket host — torna a maquina um endpoint para receber tarefas.
Porta padrao: 8765

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

ALREADY_RUNNING = "already_running"

_pending: dict = {}   # task_id -> websocket
_loop: asyncio.AbstractEventLoop | None = None


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

    async def handler(websocket):
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

    try:
        async with websockets.serve(handler, host, port):
            await asyncio.Future()
    except OSError:
        await _ping_existing(port)
        return ALREADY_RUNNING


async def _ping_existing(port: int):
    try:
        uri = f"ws://127.0.0.1:{port}"
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"type": "show_window"}))
    except Exception:
        pass
