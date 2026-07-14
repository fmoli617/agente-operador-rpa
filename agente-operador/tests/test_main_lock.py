import socket

import main


def test_acquire_lock_fails_when_port_already_bound():
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", main.LOCK_PORT))
    blocker.listen(1)
    try:
        assert main._acquire_lock() is False
    finally:
        blocker.close()
