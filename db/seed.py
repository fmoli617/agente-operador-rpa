"""
Cria/popula db/usuarios.db a partir de schema.sql — idempotente (pode rodar
várias vezes sem duplicar). Dados aqui são massa de teste local: a integração
real com o orquestrador (outra máquina) ainda não existe (ver doc_version.md).

Uso:
    python db/seed.py
"""
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "usuarios.db"
SCHEMA_FILE = Path(__file__).parent / "schema.sql"

SEED = [
    ("automacao-analitico-01", "analitico", "127.0.0.1", 1),
    ("automacao-analitico-02", "analitico", "127.0.0.1", 1),
    ("automacao-outro-sistema-01", "outro_sistema", "127.0.0.1", 1),
    ("automacao-analitico-desativada", "analitico", "127.0.0.1", 0),
]


def seed() -> None:
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        existentes = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if existentes == 0:
            conn.executemany(
                "INSERT INTO usuarios (nome, sistema, maquina_operador, ativo) VALUES (?, ?, ?, ?)",
                SEED,
            )
            conn.commit()
            print(f"{len(SEED)} usuários inseridos em {DB_FILE}")
        else:
            print(f"{DB_FILE} já populado ({existentes} usuários) — nada a fazer")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
