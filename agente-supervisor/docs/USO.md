# Uso e integração — agente-supervisor

## O que o supervisor faz

O supervisor é uma ferramenta de observabilidade **sem estado próprio** — ele lê o estado da máquina em tempo real e gera um relatório. Não persiste nada além do `status.txt` gerado a cada execução.

---

## Integração com o agente-operador

O `agente-operador` chama o supervisor internamente a cada 60 segundos para manter um `status.txt` atualizado na pasta de runtime (`%LOCALAPPDATA%\OperacaoAssistida\`). Isso é feito em uma thread separada (`_run_status_loop`) para não bloquear a UI.

Para rodar o supervisor manualmente enquanto o operador está ativo:

```bash
python -m agente_supervisor.main --watch --interval 10
```

---

## Session ID como chave de correlação

O `session_id` gerado pelo supervisor (`SHA256(usuario@maquina)[:16]`) serve como chave de correlação entre:

- Logs do `agente-operador` (`%LOCALAPPDATA%\OperacaoAssistida\logs\`)
- Relatórios do supervisor (`status.txt`)
- Registros de tarefas no `agente-consumidor` (via `task_id`)

---

## status.txt

O arquivo `status.txt` é gerado na pasta do script por padrão. Em produção (quando chamado pelo `agente-operador`), o caminho é definido pelo `main.py` do operador.

O arquivo é sobrescrito a cada execução — não é um log cumulativo. Para histórico, redirecione a saída ou implemente rotação no ponto de chamada.
