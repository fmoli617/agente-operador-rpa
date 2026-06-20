# Histórico de evolução

Log cronológico (mais recente no topo) das decisões estruturais do projeto. Cada entrada: o que mudou, por quê, e o que ficou pendente. Detalhes de "como usar" ficam no `README.md` e em [ARQUITETURA.md](ARQUITETURA.md) — aqui é o porquê e quando.

---

## 2026-06-20 — Clean Architecture: domain/ + application/ isolando regra de negócio e protocolo

**O que mudou:** o estado de tarefa deixou de ser um `dict` solto e virou uma entidade real (`domain/task.py:Task`), com seus próprios métodos de transição (`set_status`, `register_session`, `mark_finished`, etc.). Foi criada uma porta de domínio `domain/ports.py:TaskResponder` (interface abstrata) e um caso de uso `application/task_service.py:TaskService`, que é a única camada que conhece tanto o `TaskStore` (agora um repositório puro) quanto o `TaskResponder`. `service/host.py` passou a implementar essa porta via `WebSocketTaskResponder`. `app/notification_window.py` não monta mais o JSON do protocolo (`{"type": "credentials", ...}`) — chama `task_service.submit_credentials(...)` e pronto.

**Por quê:** a UI conhecia o formato exato das mensagens do protocolo operador→consumidor (`_bridge.respond(task_id, {"type": "credentials", ...})`), uma violação de camada — se o protocolo mudasse, era a UI que ia quebrar. Formalizando uma porta (`TaskResponder`), a regra "como responder a uma tarefa" fica isolada da UI e do transporte; trocar WebSocket por outra coisa no futuro não tocaria em `domain/` nem `application/`.

**Trade-off aceito:** mais arquivos e mais indireção (`UI -> TaskService -> TaskResponder -> WebSocket` em vez de uma chamada direta) para um app deste tamanho. Optamos pela versão completa com interfaces porque a expectativa é o projeto crescer (mais tipos de tarefa, possivelmente outro transporte) — ver discussão em [ARQUITETURA.md](ARQUITETURA.md).

**Pendente:** `domain/task.py` ainda guarda `qr_image_b64` como string base64 — é dado de domínio (a entidade "sabe" que recebeu um QR), mas o parsing/render do PNG continua só na UI, que é o lugar certo. Se surgir um segundo `TaskResponder` (ex.: HTTP), validar que a interface atual (`send_credentials`/`send_code`) é suficiente ou se precisa crescer.

---

## 2026-06-20 — Separação da camada de UX (estado vs. widget vs. orquestração)

**O que mudou:** `app/notification_window.py` (um único arquivo de ~800 linhas misturando estado de tarefas, lógica de transição de status e construção de widgets Qt) foi dividido em:

- `app/task_store.py` — estado das tarefas, sem dependência de Qt.
- `app/widgets/task_row.py` — o widget de linha da lista, isolado.
- `app/notification_window.py` — ficou só com a orquestração (UI + conexão dos sinais do bridge ao store).

**Por quê:** cada novo tipo de retorno do consumidor (`login_error`, `credentials_error`, etc.) estava virando mais um `if` espalhado pelo mesmo arquivo gigante, misturando "o que é verdade sobre a tarefa" com "como isso aparece na tela". Separar facilita testar o estado sem precisar de `QT_QPA_PLATFORM=offscreen` e deixa claro onde adicionar um novo status.

**Pendente:** se a página de detalhe continuar crescendo, o próximo corte é separar `_build_list_page` / `_build_detail_page` em arquivos próprios dentro de `app/widgets/`.

## 2026-06-20 — Suíte de testes formal (`tests/`)

**O que mudou:** testes manuais ad-hoc (scripts `_test_*.py` descartáveis, rodados uma vez e apagados) foram substituídos por uma suíte real em `tests/` (pytest + pytest-asyncio), cobrindo: geração de token/certificado (`service/security.py`), handshake de autenticação e fluxo completo do protocolo no host WebSocket (`service/host.py`), transições de estado (`app/task_store.py`), e a UI em modo offscreen (`app/notification_window.py`). Ver `tests/README.md` para o mapa completo.

**Por quê:** sem suíte, toda mudança em `host.py` ou na UI exigia recriar manualmente um cliente WebSocket de teste para validar — como aconteceu na sessão anterior (token errado, sem token, fluxo completo). Formalizar isso significa que qualquer regressão futura (ex.: mudar o protocolo de auth) é pega automaticamente.

**Bug real encontrado pelo teste:** `_add_task` em `notification_window.py` só escondia o label "Nenhuma tarefa recebida" se `self._empty_label.isVisible()` já fosse `True` — e isso depende da janela-pai já ter sido mostrada por fora (em produção, `main.py` chama `window.show()` no startup antes de qualquer tarefa chegar, então sempre funcionava). Era uma dependência de ordem frágil, sem nenhum sintoma visível até o teste isolar a chamada. Corrigido para escon­der incondicionalmente.

**Pendente:** os testes de UI usam `QT_QPA_PLATFORM=offscreen` e não cobrem renderização visual (cores, posicionamento) — só lógica e transições de estado. Testes de fila/concorrência com múltiplas tarefas simultâneas ainda não existem (a UI também não suporta isso de verdade — ver checklist no README).

## 2026-06-20 — Token de autenticação + TLS no host WebSocket

**O que mudou:** `service/security.py` foi criado para gerar/gerenciar um token de autenticação (handshake obrigatório `{"type": "auth", "token": "..."}`) e um certificado TLS autoassinado para servir via `wss://` em vez de `ws://`.

**Por quê:** o host WebSocket aceitava qualquer conexão na rede sem nenhuma verificação, e credenciais (`user`/`password`) trafegavam em texto puro. Ver seção "Segurança" do `README.md` para detalhes e limitações conhecidas (certificado autoassinado, escopo de auth por conexão).

**Pendente:** sem rotação automática de token, sem expiração de sessão, sem autenticação por `task_id`.

## 2026-06-20 — Correção de imports quebrados e bug de caminho de log

**O que mudou:** `main.py` e `install/create_shortcut.py` referenciavam módulos (`agente_operador.*`, `agente_supervisor.*`) que não existem neste repo — corrigido para os caminhos reais (`app.*`, `service.*`). Removido o status loop dependente do `agente_supervisor` ausente. Corrigido `_LOG` em `main.py`, que escrevia o log um nível **acima** da raiz do projeto por assumir a estrutura antiga.

**Por quê:** o app não rodava como estava committado — `ModuleNotFoundError` na primeira importação. O README descrevia uma estrutura mais ambiciosa (`agente_consumidor/`, `agente_supervisor/`) que nunca foi criada; os imports ficaram desalinhados com o código real.

**Pendente:** decidir se `agente_consumidor` (SDK) e `agente_supervisor` (status.txt) ainda fazem parte do roadmap ou devem ser removidos do README.
