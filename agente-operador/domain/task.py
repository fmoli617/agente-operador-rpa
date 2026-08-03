"""Entidade de domínio Task — não conhece Qt nem WebSocket."""
from dataclasses import dataclass, field
from datetime import datetime


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


@dataclass
class Task:
    id: int
    task_id: str
    title: str
    message: str
    system: str | None = None
    status: str = "Aguardando login"
    proc_text: str = "Aguardando QR Code..."
    session_user: str | None = None
    qr_image_b64: str | None = None
    finished: bool = False
    log: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.log:
            self.log.append(f"{_now()}  Tarefa recebida")

    def set_status(self, status: str) -> None:
        self.status = status

    def log_event(self, event: str) -> None:
        self.log.append(f"{_now()}  {event}")

    def set_proc_text(self, text: str) -> None:
        self.proc_text = text

    def register_session(self, user: str) -> None:
        self.session_user = user

    def clear_session(self) -> None:
        self.session_user = None

    def receive_qr(self, image_b64: str) -> None:
        self.qr_image_b64 = image_b64

    def pop_qr(self) -> str | None:
        qr = self.qr_image_b64
        self.qr_image_b64 = None
        return qr

    def mark_finished(self) -> bool:
        """Marca a tarefa como encerrada. Retorna True só se a transição de fato ocorreu."""
        if self.finished:
            return False
        self.finished = True
        return True
