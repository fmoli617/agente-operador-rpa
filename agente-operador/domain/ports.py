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
