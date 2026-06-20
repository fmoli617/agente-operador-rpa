from app.notification_window import NotificationWindow
from app.task_store import TaskStore
from application.task_service import TaskService
from domain.ports import TaskResponder


class FakeResponder(TaskResponder):
    def __init__(self):
        self.sent = []

    def send_credentials(self, task_id, user, password):
        self.sent.append((task_id, "credentials", user, password))

    def send_code(self, task_id, code):
        self.sent.append((task_id, "code", code))


def _window():
    responder = FakeResponder()
    service = TaskService(TaskStore(), responder)
    window = NotificationWindow("operador", "MAQUINA01", service)
    return window, responder


def test_full_task_flow_through_ui(qapp):
    window, responder = _window()

    window.show_notification("SRV1 - Login", "msg", "task-1")
    assert len(window._store.all()) == 1
    assert window._empty_label.isHidden() is True

    window._open_detail(0)
    assert window._stack.currentIndex() == 1

    window._input_user.setText("joao")
    window._input_pass.setText("senha123")
    window._submit_credentials()

    assert window._store.get("task-1").session_user == "joao"
    assert responder.sent[-1] == ("task-1", "credentials", "joao", "senha123")

    window.show_qr_code("task-1", "AAAA")
    assert window._qr_widget.isVisible() is True

    window._input_code.setText("1234")
    window._submit_code()
    assert responder.sent[-1] == ("task-1", "code", "1234")
    assert window._stack.currentIndex() == 0  # volta pra lista

    window.on_execution_started("task-1")
    assert window._store.get("task-1").status == "Em execução"

    window.remove_task("task-1")
    assert window._store.get("task-1").finished is True


def test_credentials_error_resets_form(qapp):
    window, _ = _window()
    window.show_notification("SRV1 - Login", "msg", "task-1")
    window._open_detail(0)
    window._input_user.setText("joao")
    window._input_pass.setText("errada")
    window._submit_credentials()

    window.on_credentials_error("task-1", "Usuário ou senha incorretos.")

    assert window._store.get("task-1").session_user is None
    assert window._creds_widget.isVisible() is True
    assert window._input_user.text() == ""


def test_dismiss_removes_finished_task_from_store(qapp):
    window, _ = _window()
    window.show_notification("SRV1 - Login", "msg", "task-1")
    window.remove_task("task-1")
    window._dismiss_task("task-1")
    assert window._store.get("task-1") is None
    assert window._empty_label.isVisible() is True
