# Testes de integração (raiz do monorepo)

Diferente dos testes internos de cada módulo (`agente-operador/tests/`), aqui o alvo é o **contrato
entre `agente-bot` e `agente-operador`**: o cliente real do bot (`SessaoOperador`, em
`agente-bot/src/services/operacao_assistida.py`) conversando com o host real do operador
(`agente-operador/service/host.py`), sem mock de protocolo dos dois lados.

```powershell
pip install -r requirements-dev.txt
cd tests
pytest
```

| Arquivo                            | O que cobre                                                                 |
|-------------------------------------|-------------------------------------------------------------------------------|
| `test_integracao_bot_operador.py`   | Fluxo completo de uma tarefa (credenciais → QR → código → execução), múltiplas tarefas simultâneas sem misturar `task_id`, rejeição de token inválido |

A resposta do "operador humano" (preencher credenciais / digitar código) é simulada chamando
diretamente `host_module.WebSocketTaskResponder` — é a mesma implementação que a UI usa por trás do
popup, então o teste valida o transporte real sem precisar de `QApplication`/PyQt6.

`conftest.py` insere `agente-operador/` e `agente-bot/src/` no `sys.path` e sobe o host numa porta TCP
livre e isolada, com `.secrets/` redirecionado para um diretório temporário (nunca toca no `.secrets/`
real do projeto).

## Pendente

- **Instalação / execução via `.exe`** e **limpeza** (item 2.3 do `../doc_version.md`): ainda não há
  teste automatizado do instalador (`agente-operador/installer/build.ps1`) nem da limpeza de
  `%LOCALAPPDATA%\OperacaoAssistida` — exige rodar o instalador de verdade, não cabe no nível de
  protocolo coberto aqui.
- **Base de usuários vinculados à automação via orquestrador** (`../db/`, ainda vazio): quando existir,
  os testes de múltiplas tarefas devem passar a usar essa base como massa de teste em vez de valores
  fixos (`"analitico"`, `"outro_sistema"`).
- Testes aqui cobrem só o nível de protocolo (WebSocket) — não sobem Selenium/Chrome nem o pipeline
  completo do `agente-bot` (`rpa_pipeline.executar_pipeline`), que depende de um site alvo real.
