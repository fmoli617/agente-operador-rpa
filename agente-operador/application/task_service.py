"""
Casos de uso — única camada que conhece tanto o estado das tarefas (TaskStore)
quanto a forma de responder ao consumidor (TaskResponder). A UI chama estes
métodos; nunca conhece o formato das mensagens do protocolo.
"""
from ui.task_store import TaskStore
from domain.ports import CredentialStore, TaskResponder
from domain.task import Task
from service.logger import get_logger

_logger = get_logger(__name__)


class TaskService:
    def __init__(self, store: TaskStore, responder: TaskResponder, credential_store: CredentialStore | None = None):
        self._store = store
        self._responder = responder
        self._credential_store = credential_store

    @property
    def store(self) -> TaskStore:
        """Acesso de leitura ao estado das tarefas — escrita sempre passa pelos métodos abaixo."""
        return self._store

    def register_task(self, title: str, message: str, task_id: str, system: str | None = None) -> Task:
        _logger.info("tarefa registrada: task_id=%s title=%r system=%r", task_id, title, system)
        return self._store.add(title, message, task_id, system)

    def saved_credentials(self, system: str | None) -> dict | None:
        """Credencial salva para o sistema, se houver — usada pela UI para pré-preencher o
        formulário. O popup de confirmação humana continua obrigatório mesmo com dado salvo."""
        if not system or not self._credential_store:
            return None
        return self._credential_store.get(system)

    def submit_credentials(self, task_id: str, user: str, password: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.register_session(user)
        self._responder.send_credentials(task_id, user, password)
        if self._credential_store and task.system:
            self._credential_store.save(task.system, user, password)
        task.log_event("Credenciais enviadas")
        task.set_status("Aguardando QR Code")
        _logger.info("credenciais enviadas: task_id=%s user=%s", task_id, user)

    def submit_code(self, task_id: str, code: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        self._responder.send_code(task_id, code)
        task.log_event("Código enviado")
        task.set_status("Em processamento")
        task.pop_qr()
        _logger.info("código de verificação enviado: task_id=%s", task_id)

    def receive_qr_code(self, task_id: str, image_b64: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event("QR Code recebido")
        task.set_status("Aguardando código")
        task.receive_qr(image_b64)
        task.set_proc_text("Aguardando código...")
        _logger.info("QR Code recebido: task_id=%s", task_id)

    def mark_execution_started(self, task_id: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event("Execução iniciada")
        task.set_status("Em execução")
        _logger.info("execução iniciada: task_id=%s", task_id)

    def mark_execution_error(self, task_id: str, message: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event(f"Erro inesperado: {message}")
        task.set_status("Erro inesperado")
        _logger.error("erro inesperado na execução: task_id=%s message=%s", task_id, message)

    def mark_credentials_error(self, task_id: str, message: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        if self._credential_store and task.system:
            self._credential_store.forget(task.system)
        task.log_event(f"Erro de credenciais: {message}")
        task.set_status("Aguardando login")
        task.clear_session()
        task.set_proc_text("Aguardando QR Code...")
        _logger.warning("erro de credenciais: task_id=%s message=%s", task_id, message)

    def mark_login_error(self, task_id: str) -> None:
        task = self._store.get(task_id)
        if not task:
            return
        task.log_event("Erro de sessão — aguardando novo QR Code")
        task.set_status("Aguardando QR Code")
        _logger.warning("erro de sessão: task_id=%s", task_id)

    def mark_session_ended(self, task_id: str) -> Task | None:
        """Conexão do consumidor encerrada. Retorna a tarefa se a transição ocorreu, None se já estava encerrada."""
        task = self._store.get(task_id)
        if not task or not task.mark_finished():
            return None
        task.log_event("Sessão encerrada")
        task.set_status("Encerrado")
        _logger.info("sessão encerrada: task_id=%s", task_id)
        return task

    def dismiss_task(self, task_id: str) -> None:
        _logger.info("tarefa descartada: task_id=%s", task_id)
        self._store.remove(task_id)
