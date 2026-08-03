from service.credential_store import FileCredentialStore


def test_get_returns_none_when_nothing_saved(isolated_secrets):
    store = FileCredentialStore()
    assert store.get("analitico") is None


def test_save_then_get_roundtrip(isolated_secrets):
    store = FileCredentialStore()
    store.save("analitico", "joao", "senha123")
    assert store.get("analitico") == {"user": "joao", "password": "senha123"}


def test_data_file_is_encrypted_on_disk(isolated_secrets):
    store = FileCredentialStore()
    store.save("analitico", "joao", "senha123")
    raw = (isolated_secrets / "credenciais.enc").read_bytes()
    assert b"senha123" not in raw
    assert b"joao" not in raw


def test_forget_removes_only_the_given_system(isolated_secrets):
    store = FileCredentialStore()
    store.save("analitico", "joao", "senha123")
    store.save("outro_sistema", "maria", "senha456")

    store.forget("analitico")

    assert store.get("analitico") is None
    assert store.get("outro_sistema") == {"user": "maria", "password": "senha456"}


def test_persists_across_instances(isolated_secrets):
    FileCredentialStore().save("analitico", "joao", "senha123")
    novo = FileCredentialStore()
    assert novo.get("analitico") == {"user": "joao", "password": "senha123"}
