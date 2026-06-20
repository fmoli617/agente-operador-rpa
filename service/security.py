"""
Segurança do host WebSocket: token de autenticação e TLS (wss://).

- Token: prioridade para a env var OPERADOR_WS_TOKEN; senão lê/gera um
  token persistido em .secrets/ws_token.txt.
- TLS: certificado autoassinado gerado em .secrets/ na primeira execução
  e reaproveitado depois. Válido apenas para a rede local — consumidores
  precisam desabilitar a verificação da CA ou fixar (pin) este certificado.
"""
import datetime
import ipaddress
import os
import secrets
import ssl
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

BASE_DIR = Path(__file__).resolve().parent.parent
SECRETS_DIR = BASE_DIR / ".secrets"
TOKEN_FILE = SECRETS_DIR / "ws_token.txt"
CERT_FILE = SECRETS_DIR / "host_cert.pem"
KEY_FILE = SECRETS_DIR / "host_key.pem"


def get_auth_token() -> str:
    env_token = os.environ.get("OPERADOR_WS_TOKEN")
    if env_token:
        return env_token

    SECRETS_DIR.mkdir(exist_ok=True)
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()

    token = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    return token


def get_server_ssl_context() -> ssl.SSLContext:
    SECRETS_DIR.mkdir(exist_ok=True)
    if not (CERT_FILE.exists() and KEY_FILE.exists()):
        _generate_self_signed_cert()

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))
    return context


def get_client_ssl_context() -> ssl.SSLContext:
    """Contexto para conexões internas (ex.: ping de instância única) ao próprio host autoassinado."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _generate_self_signed_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "operacao-assistida-host")])
    now = datetime.datetime.now(datetime.timezone.utc)

    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    KEY_FILE.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
