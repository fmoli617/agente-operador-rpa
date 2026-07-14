# agente-supervisor

CLI de monitoramento para a stack **Operação Assistida**. Inspeciona a máquina local e gera um relatório de estado: session ID, status do WebSocket host, processos ativos e IPs acessíveis.

---

## Uso

```bash
# Relatório único (imprime e salva status.txt)
python -m agente_supervisor.main

# Modo watch — atualiza a cada 10 segundos
python -m agente_supervisor.main --watch

# Intervalo customizado
python -m agente_supervisor.main --watch --interval 30
```

Se instalado via `pip install -e .`:

```bash
agente-supervisor
agente-supervisor --watch
```

---

## Exemplo de saída

```
============================================================
  OPERAÇÃO ASSISTIDA — SUPERVISOR
============================================================
  Sessão ID  : a3f2b1c4d5e6f7a8
  Identidade : fmoli@LAPTOP-M608PGJE
  Usuário    : fmoli
  Máquina    : LAPTOP-M608PGJE
  Gerado em  : 2026-07-13 10:30:00

────────────────────────────────────────────────────────────
  STATUS DO SERVIÇO
────────────────────────────────────────────────────────────
  WebSocket host (porta 8765) : ATIVO
    Acessível em : ws://192.168.3.40:8765

────────────────────────────────────────────────────────────
  PROCESSOS ATIVOS
────────────────────────────────────────────────────────────
  PID   1234 | pythonw.exe -m main

────────────────────────────────────────────────────────────
  RASTREABILIDADE
────────────────────────────────────────────────────────────
  Endpoint WebSocket : ws://LAPTOP-M608PGJE:8765
  Sessao unica por   : usuario + maquina (SHA-256 truncado)
  Chave de sessao    : SHA256('fmoli@LAPTOP-M608PGJE')[:16]
                     = a3f2b1c4d5e6f7a8
```

---

## Session ID

O `session_id` é `SHA256(usuario@maquina)[:16]` — identifica unicamente este host no sistema. Use-o para correlacionar logs e tarefas remotas entre os três módulos da stack.

---

## Estrutura

```txt
agente-supervisor/
├── agente_supervisor/
│   ├── __init__.py
│   └── main.py       # CLI + geração do relatório
├── docs/
│   └── USO.md        # Detalhes de integração com os outros módulos
├── requirements.txt
└── pyproject.toml
```
