"""TaskStore agora é só repositório: busca/adiciona/remove. Regra de negócio mora em domain/task.py e application/task_service.py."""
from app.task_store import TaskStore


def test_add_creates_task_with_defaults():
    store = TaskStore()
    task = store.add("Host - Processo", "msg", "task-1")
    assert task.task_id == "task-1"
    assert task.status == "Aguardando login"
    assert task.finished is False
    assert store.get("task-1") is task
    assert store.get_by_index(task.id) is task


def test_remove_and_is_empty():
    store = TaskStore()
    store.add("T", "m", "task-1")
    assert not store.is_empty()
    store.remove("task-1")
    assert store.is_empty()
    assert store.get("task-1") is None


def test_get_unknown_task_id_returns_none():
    store = TaskStore()
    assert store.get("nope") is None
    assert store.get_by_index(999) is None


def test_ids_are_sequential_and_independent_of_removal():
    store = TaskStore()
    t1 = store.add("T1", "m", "task-1")
    store.remove("task-1")
    t2 = store.add("T2", "m", "task-2")
    assert t2.id == t1.id + 1
