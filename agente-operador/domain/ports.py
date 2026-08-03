"""Portas (interfaces) que o domínio espera da infraestrutura — implementadas em service/."""
from abc import ABC, abstractmethod


class TaskResponder(ABC):
    """Como o operador responde a um consumidor que aguarda uma tarefa. Implementada via WebSocket em service/host.py."""

    @abstractmethod
    def send_credentials(self, task_id: str, user: str, password: str) -> None:
        ...

    @abstractmethod
    def send_code(self, task_id: str, code: str) -> None:
        ...


class CredentialStore(ABC):
    """Persistência de user/senha por sistema, reaproveitada entre sessões — implementada via
    arquivo criptografado em service/credential_store.py. QR/MFA nunca passa por aqui: é sempre
    solicitado de novo em toda sessão (ver CLAUDE.md / doc_version.md, seção 2.2)."""

    @abstractmethod
    def get(self, system: str) -> dict | None:
        ...

    @abstractmethod
    def save(self, system: str, user: str, password: str) -> None:
        ...

    @abstractmethod
    def forget(self, system: str) -> None:
        ...
