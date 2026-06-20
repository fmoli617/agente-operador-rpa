"""
TaskService é a única camada que conhece tanto o estado (TaskStore) quanto o
protocolo de resposta (TaskResponder). Testado aqui com um responder fake —
nunca precisa de WebSocket real para validar a regra de negócio.
"""
from app.task_store import TaskStore
from application.task_service import TaskService
from domain.ports import TaskResponder


class FakeResponder(TaskResponder):
    def __init__(self):
        self.credentials_sent = []
        self.codes_sent = []

    def send_credentials(self, task_id, user, password):
        self.credentials_sent.append((task_id, user, password))

    def send_code(self, task_id, code):
        self.codes_sent.append((task_id, code))


def _service():
    responder = FakeResponder()
    service = TaskService(TaskStore(), responder)
    return service, responder


def test_submit_credentials_registers_session_and_responds():
    service, responder = _service()
    service.register_task("Host - Proc", "msg", "task-1")

    service.submit_credentials("task-1", "joao", "senha123")

    task = service.store.get("task-1")
    assert task.session_user == "joao"
    assert task.status == "Aguardando QR Code"
    assert responder.credentials_sent == [("task-1", "joao", "senha123")]


def test_submit_code_responds_and_clears_qr():
    service, responder = _service()
    service.register_task("Host - Proc", "msg", "task-1")
    service.receive_qr_code("task-1", "AAAA")

    service.submit_code("task-1", "1234")

    task = service.store.get("task-1")
    assert task.qr_image_b64 is None
    assert task.status == "Em processamento"
    assert responder.codes_sent == [("task-1", "1234")]


def test_receive_qr_code_updates_status_and_stores_image():
    service, _ = _service()
    service.register_task("Host - Proc", "msg", "task-1")
    service.receive_qr_code("task-1", "AAAA")
    task = service.store.get("task-1")
    assert task.qr_image_b64 == "AAAA"
    assert task.status == "Aguardando código"


def test_mark_execution_started_clears_nothing_in_store_but_updates_status():
    service, _ = _service()
    service.register_task("Host - Proc", "msg", "task-1")
    service.mark_execution_started("task-1")
    assert service.store.get("task-1").status == "Em execução"


def test_mark_credentials_error_resets_session():
    service, _ = _service()
    service.register_task("Host - Proc", "msg", "task-1")
    service.submit_credentials("task-1", "joao", "senha123")

    service.mark_credentials_error("task-1", "Usuário ou senha incorretos.")

    task = service.store.get("task-1")
    assert task.session_user is None
    assert task.status == "Aguardando login"


def test_mark_session_ended_is_idempotent():
    service, _ = _service()
    service.register_task("Host - Proc", "msg", "task-1")

    first = service.mark_session_ended("task-1")
    second = service.mark_session_ended("task-1")

    assert first is not None
    assert first.finished is True
    assert second is None


def test_dismiss_task_removes_from_store():
    service, _ = _service()
    service.register_task("Host - Proc", "msg", "task-1")
    service.dismiss_task("task-1")
    assert service.store.get("task-1") is None


def test_operations_on_unknown_task_id_are_safe_noops():
    service, responder = _service()
    service.submit_credentials("nope", "joao", "senha123")
    service.submit_code("nope", "1234")
    service.receive_qr_code("nope", "AAAA")
    service.mark_execution_started("nope")
    service.mark_execution_error("nope", "erro")
    service.mark_credentials_error("nope", "erro")
    service.mark_login_error("nope")
    assert service.mark_session_ended("nope") is None
    assert responder.credentials_sent == []
    assert responder.codes_sent == []
