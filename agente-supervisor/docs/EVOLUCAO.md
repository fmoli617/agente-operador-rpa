# Histórico de evolução — agente-supervisor

Log cronológico das decisões estruturais. Mais recente no topo. Cada entrada: o que mudou, por quê, o que ficou pendente.
Detalhes de uso ficam no `README.md` e em `docs/USO.md` — aqui é o porquê e quando.

---

## 2026-07-13 — Separação em projeto independente + estrutura de pacote Python

**O que mudou:** o código que vivia em `v1-com-estrutura-tripartida/agente_supervisor/` foi movido para este projeto independente. Criada estrutura de pacote Python (`agente_supervisor/__init__.py` exporta `get_identity`, `build_report`, `run_once`), `docs/` com `USO.md` e `EVOLUCAO.md`. Adicionados `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `.markdownlint.json`. Entry point `agente-supervisor` configurado no `pyproject.toml`.

**Por quê:** o supervisor estava misturado com os outros dois módulos e era referenciado por imports diretos em `agente-operador/main.py` da v1 (acoplamento de código entre projetos). Separar permite instalar o supervisor isoladamente e referenciar como pacote via `pip install`.

**Pendente:**
- O `agente-operador` atual (v2) não usa mais o supervisor internamente — o loop de `status.txt` foi removido na limpeza de imports. Reacoplar via instalação do pacote ou via chamada HTTP/CLI é decisão de roadmap.
- O `check_processes()` usa PowerShell e só funciona em Windows — sem abstração de plataforma.
- `STATUS_FILE` ainda usa `os.path.dirname(__file__)` como base, o que pode apontar para dentro de um `.egg` se instalado via pip. Melhorar para `platformdirs` ou `%LOCALAPPDATA%`.
