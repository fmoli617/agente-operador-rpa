import sys
import socket
import getpass
import asyncio
import threading
import json

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from ui.notification_window import NotificationWindow
from ui.task_store import TaskStore
from ui.tray import TrayIcon
from application.task_service import TaskService
from service.host import WebSocketTaskResponder, start_host
from service.security import get_auth_token, get_client_ssl_context
from service.logger import configure_logging, get_logger

HOST_PORT = 8765
LOCK_PORT = 8764  # porta exclusiva de lock de instância única

_lock_sock = None  # referência global — nunca pode ser garbage collected
_logger = get_logger(__name__)


def _acquire_lock() -> bool:
    """Faz bind exclusivo em LOCK_PORT. Retorna True se esta é a primeira instância."""
    global _lock_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
        _lock_sock = s  # mantém aberto para sempre
        return True
    except OSError:
        s.close()
        return False


def _ping_show_window(port: int):
    """Pinga a instância ativa para reabrir o popup, sem iniciar Qt."""
    async def _send():
        import websockets
        try:
            uri = f"wss://127.0.0.1:{port}"
            async with websockets.connect(uri, ssl=get_client_ssl_context()) as ws:
                await ws.send(json.dumps({"type": "auth", "token": get_auth_token()}))
                await ws.send(json.dumps({"type": "show_window"}))
        except Exception:
            pass
    asyncio.run(_send())


class AppBridge(QObject):
    """Ponte thread-safe entre o WebSocket host e a UI Qt."""
    show_notification = pyqtSignal(str, str, str)   # title, message, task_id
    show_qr_code = pyqtSignal(str, str)             # task_id, image_b64
    login_error = pyqtSignal(str, str)              # task_id, message
    credentials_error = pyqtSignal(str, str)        # task_id, message
    execution_started = pyqtSignal(str)             # task_id
    execution_error = pyqtSignal(str, str)          # task_id, message
    session_count_changed = pyqtSignal(int)
    task_removed = pyqtSignal(str)                  # task_id
    show_window = pyqtSignal()
    quit_app = pyqtSignal()


def _run_host(bridge: AppBridge, app: QApplication):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(start_host(bridge))
    if result == "already_running":
        bridge.quit_app.emit()


def main():
    configure_logging()
    _logger.info("main() iniciado")
    if not _acquire_lock():
        _logger.info("saindo — instância já ativa (lock port ocupada)")
        _ping_show_window(HOST_PORT)
        sys.exit(0)
    _logger.info("lock adquirido, prosseguindo para Qt")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    username = getpass.getuser()
    hostname = socket.gethostname()
    _logger.info("sessão de operador: usuário=%s host=%s", username, hostname)

    bridge = AppBridge()
    task_service = TaskService(TaskStore(), WebSocketTaskResponder())
    window = NotificationWindow(username, hostname, task_service)
    bridge.show_notification.connect(window.show_notification)
    bridge.show_qr_code.connect(window.show_qr_code)
    bridge.login_error.connect(window.on_login_error)
    bridge.credentials_error.connect(window.on_credentials_error)
    bridge.execution_started.connect(window.on_execution_started)
    bridge.execution_error.connect(window.on_execution_error)
    bridge.session_count_changed.connect(window.update_session_count)
    bridge.task_removed.connect(window.remove_task)
    bridge.show_window.connect(window._show_and_raise)
    bridge.quit_app.connect(app.quit)

    tray = TrayIcon(window)
    tray.show()

    window.show()

    host_thread = threading.Thread(target=_run_host, args=(bridge, app), daemon=True)
    host_thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
