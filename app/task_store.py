"""Repositório em memória de Task — só busca/adiciona/remove, sem regra de negócio (isso fica em Task e em TaskService)."""
from domain.task import Task


class TaskStore:
    def __init__(self):
        self._tasks: list[Task] = []
        self._next_id = 0

    def all(self) -> list[Task]:
        return self._tasks

    def is_empty(self) -> bool:
        return not self._tasks

    def get(self, task_id: str) -> Task | None:
        return next((t for t in self._tasks if t.task_id == task_id), None)

    def get_by_index(self, idx: int) -> Task | None:
        return next((t for t in self._tasks if t.id == idx), None)

    def add(self, title: str, message: str, task_id: str) -> Task:
        task = Task(id=self._next_id, task_id=task_id, title=title, message=message)
        self._next_id += 1
        self._tasks.append(task)
        return task

    def remove(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.task_id != task_id]
