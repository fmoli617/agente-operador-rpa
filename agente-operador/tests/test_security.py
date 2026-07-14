import ssl

from service import security


def test_token_is_generated_and_persisted(isolated_secrets):
    token1 = security.get_auth_token()
    token2 = security.get_auth_token()
    assert token1 == token2
    assert (isolated_secrets / "ws_token.txt").exists()


def test_token_env_var_takes_priority(isolated_secrets, monkeypatch):
    monkeypatch.setenv("OPERADOR_WS_TOKEN", "token-fixo-via-env")
    assert security.get_auth_token() == "token-fixo-via-env"
    assert not (isolated_secrets / "ws_token.txt").exists()


def test_server_ssl_context_generates_cert_and_key(isolated_secrets):
    ctx = security.get_server_ssl_context()
    assert isinstance(ctx, ssl.SSLContext)
    assert (isolated_secrets / "host_cert.pem").exists()
    assert (isolated_secrets / "host_key.pem").exists()


def test_server_ssl_context_reuses_existing_cert(isolated_secrets):
    security.get_server_ssl_context()
    cert_before = (isolated_secrets / "host_cert.pem").read_bytes()
    security.get_server_ssl_context()
    cert_after = (isolated_secrets / "host_cert.pem").read_bytes()
    assert cert_before == cert_after


def test_client_ssl_context_disables_verification():
    ctx = security.get_client_ssl_context()
    assert ctx.verify_mode == ssl.CERT_NONE
    assert ctx.check_hostname is False
