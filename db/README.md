# db/ — base de usuários/contas de automação

SQLite (`usuarios.db`, gerado por `seed.py` — não versionado, só `schema.sql` e `seed.py` vão pro git).
Liga "qual conta o orquestrador manda rodar" a "qual sistema e qual máquina do `agente-operador`" —
ver `schema.sql` para a definição completa.

```powershell
python db/seed.py
```

Idempotente — roda de novo sem duplicar se `usuarios.db` já existir populado.

## Quem consome isso hoje

- `agente-bot/src/app/fila.py` (`Fila`) — monta a fila de tarefas a partir das contas `ativo = 1`
  desta base; se `usuarios.db` não existir, cai no mock local de `agente-bot/src/data/analitico.py`.
- `tests/test_integracao_bot_operador.py::test_multiplas_contas_da_base_db_nao_se_misturam` — abre uma
  sessão WebSocket por conta ativa (simulando execuções concorrentes do orquestrador) e confere que
  nenhuma credencial vaza entre `task_id`s.

## Pendente

- Ainda é massa de teste local — a integração real com o orquestrador (que roda em outra máquina) não
  existe; quando existir, decidir se ele escreve diretamente nesta base, chama uma API, ou se `db/`
  vira só o schema de referência para uma base que mora em outro lugar.
- Sem relação formal com o `session_id` do `agente-supervisor` (`SHA256(usuario@maquina)[:16]`, ver
  `CLAUDE.md`) — hoje `maquina_operador` é só um host/IP solto. Se o supervisor for reintegrado, avaliar
  trocar por esse `session_id`.
