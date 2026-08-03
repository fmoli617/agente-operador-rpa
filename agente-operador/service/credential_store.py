"""
Armazenamento de user/senha por sistema (ex.: "analitico"), criptografado com
Fernet, reaproveitado entre sessões — implementa domain/ports.py:CredentialStore.

QR/MFA nunca passa por aqui: é sempre solicitado de novo em toda sessão
(ver CLAUDE.md e doc_version.md, seção 2.2). O popup humano de confirmação
continua obrigatório em toda tarefa mesmo quando há credencial salva — este
store só evita o operador ter que redigitar usuário/senha.
"""
import json

from cryptography.fernet import Fernet

from domain.ports import CredentialStore
from service import security
from service.logger import get_logger

_logger = get_logger(__name__)


def _key_file():
    return security.SECRETS_DIR / "credenciais.key"


def _data_file():
    return security.SECRETS_DIR / "credenciais.enc"


def _get_or_create_key() -> bytes:
    security.SECRETS_DIR.mkdir(exist_ok=True)
    key_file = _key_file()
    if key_file.exists():
        return key_file.read_bytes()
    key = Fernet.generate_key()
    key_file.write_bytes(key)
    return key


class FileCredentialStore(CredentialStore):
    def __init__(self):
        self._cipher = Fernet(_get_or_create_key())

    def _load_all(self) -> dict:
        data_file = _data_file()
        if not data_file.exists():
            return {}
        try:
            raw = self._cipher.decrypt(data_file.read_bytes())
            return json.loads(raw)
        except Exception:
            _logger.warning("credenciais.enc corrompido ou ilegível — tratando como vazio")
            return {}

    def _save_all(self, data: dict) -> None:
        security.SECRETS_DIR.mkdir(exist_ok=True)
        raw = json.dumps(data).encode("utf-8")
        _data_file().write_bytes(self._cipher.encrypt(raw))

    def get(self, system: str) -> dict | None:
        return self._load_all().get(system)

    def save(self, system: str, user: str, password: str) -> None:
        data = self._load_all()
        data[system] = {"user": user, "password": password}
        self._save_all(data)
        _logger.info("credencial salva para o sistema: %s user=%s", system, user)

    def forget(self, system: str) -> None:
        data = self._load_all()
        if data.pop(system, None) is not None:
            self._save_all(data)
            _logger.info("credencial removida para o sistema: %s", system)
