"""
Casos de uso — única camada que conhece tanto o estado das tarefas (TaskStore)
quanto a forma de responder ao consumidor (TaskResponder). A UI chama estes
métodos; nunca conhece o formato das mensagens do protocolo.
"""
from app.task_store import TaskStore
from domain.ports import TaskResponder
from domain.task import Task


class TaskService:
    def __init__(self, store: TaskStore, responder: TaskResponder):
        self._store = store
        self._responder = responder

    @property
    def store(self) -> TaskStore:
        """Acesso de leitura ao estado das tarefas — escrita sempre passa pelos métodos abaixo."""
        return self._store

    def register_task(self, title: str, message: str, task_id: str) -> Task:
        return self._store.add(title, message, task_id)

    def submit_credentials(self, task_id: str, user: str, password: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.register_session(user)
        self._responder.send_credentials(task_id, user, password)
        task.log_event("Credenciais enviadas")
        task.set_status("Aguardando QR Code")

    def submit_code(self, task_id: str, code: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        self._responder.send_code(task_id, code)
        task.log_event("Código enviado")
        task.set_status("Em processamento")
        task.pop_qr()

    def receive_qr_code(self, task_id: str, image_b64: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event("QR Code recebido")
        task.set_status("Aguardando código")
        task.receive_qr(image_b64)
        task.set_proc_text("Aguardando código...")

    def mark_execution_started(self, task_id: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event("Execução iniciada")
        task.set_status("Em execução")

    def mark_execution_error(self, task_id: str, message: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event(f"Erro inesperado: {message}")
        task.set_status("Erro inesperado")

    def mark_credentials_error(self, task_id: str, message: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event(f"Erro de credenciais: {message}")
        task.set_status("Aguardando login")
        task.clear_session()
        task.set_proc_text("Aguardando QR Code...")

    def mark_login_error(self, task_id: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event("Erro de sessão — aguardando novo QR Code")
        task.set_status("Aguardando QR Code")

    def mark_session_ended(self, task_id: str) -> Task | None:
        """Conexão do consumidor encerrada. Retorna a tarefa se a transição ocorreu, None se já estava encerrada."""
        task = self._store.get(task_id)
        if not task or not task.mark_finished():
            return None
        task.log_event("Sessão encerrada")
        task.set_status("Encerrado")
        return task

    def dismiss_task(self, task_id: str) -> None:
        self._store.remove(task_id)
