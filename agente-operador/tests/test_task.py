from domain.task import Task


def _make_task(**overrides) -> Task:
    defaults = dict(id=0, task_id="task-1", title="T", message="m")
    defaults.update(overrides)
    return Task(**defaults)


def test_new_task_logs_received_event():
    task = _make_task()
    assert any("Tarefa recebida" in line for line in task.log)


def test_set_status_and_log_event():
    task = _make_task()
    task.set_status("Aguardando QR Code")
    task.log_event("Credenciais enviadas")
    assert task.status == "Aguardando QR Code"
    assert any("Credenciais enviadas" in line for line in task.log)


def test_session_lifecycle():
    task = _make_task()
    task.register_session("joao")
    assert task.session_user == "joao"
    task.clear_session()
    assert task.session_user is None


def test_qr_receive_and_pop():
    task = _make_task()
    task.receive_qr("base64img")
    assert task.qr_image_b64 == "base64img"
    popped = task.pop_qr()
    assert popped == "base64img"
    assert task.qr_image_b64 is None


def test_mark_finished_is_idempotent():
    task = _make_task()
    assert task.mark_finished() is True
    assert task.finished is True
    assert task.mark_finished() is False  # já estava encerrada — sem transição
