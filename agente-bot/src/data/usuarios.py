"""
Leitura da base de usuários/contas de automação (../../../db/usuarios.db).
É o elo entre "quem o orquestrador manda rodar" e o sistema alvo (a chave
usada pelo CredentialStore do agente-operador) — ver db/schema.sql.
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DB_FILE = Path(__file__).parent.parent.parent.parent / "db" / "usuarios.db"


@dataclass
class UsuarioAutomacao:
    id: int
    nome: str
    sistema: str
    maquina_operador: str


def carregar_usuarios_ativos() -> list[UsuarioAutomacao]:
    if not DB_FILE.exists():
        return []
    conn = sqlite3.connect(DB_FILE)
    try:
        rows = conn.execute(
            "SELECT id, nome, sistema, maquina_operador FROM usuarios WHERE ativo = 1"
        ).fetchall()
        return [UsuarioAutomacao(*row) for row in rows]
    finally:
        conn.close()
