# Histórico de evolução

Log cronológico (mais recente no topo) das decisões estruturais do projeto. Cada entrada: o que mudou, por quê, e o que ficou pendente. Detalhes de "como usar" ficam no `README.md` e em [ARQUITETURA.md](ARQUITETURA.md) — aqui é o porquê e quando.

---

## 2026-06-20 — Configuração da instalação (instalacao.conf) + logger central

**O que mudou:** duas adições relacionadas a observabilidade e identificação da instalação:

1. `installer/setup.iss` ganhou uma página customizada (Pascal Script) entre a escolha de pasta e a de tarefas: mostra o nome da máquina (`{computername}`) e o usuário do Windows (`{username}`), gera uma chave de instalação de 6 dígitos, e exige uma checkbox de consentimento explícito antes de permitir avançar (`NextButtonClick` bloqueia se não marcada). Ao concluir a instalação (`ssPostInstall`), essas três informações + timestamp são gravadas em `{app}\instalacao.conf` (formato `.ini`).
2. Criado `service/logger.py`: logger central com `TimedRotatingFileHandler` (rotação à meia-noite, 30 dias de retenção), gravando em `%LOCALAPPDATA%\OperacaoAssistida\logs\`. Instrumentado em `main.py`, `service/host.py`, `service/security.py`, `application/task_service.py`, `ui/notification_window.py` e `ui/tray.py`. Substituiu o `_log`/`debug_startup.log` ad-hoc que existia em `main.py`.

**Por quê:** a instalação precisa de uma identidade própria (máquina + usuário + chave única) para servir de base de autenticação — capturada uma vez, no momento da instalação, com consentimento explícito do operador, já que essas informações não devem ficar visíveis fora dessa etapa. O logger central existia como necessidade separada: rastrear "toda a movimentação do escopo do projeto" (conexões, casos de uso, ações do operador) em arquivos diários, em vez do log mínimo que só registrava o boot do processo.

**Trade-off aceito:** `get_logger(name)` não liga a gravação em disco por si só — só devolve o `Logger`. A gravação real só começa quando `configure_logging()` é chamado explicitamente em `main()`. Essa indireção (em vez de configurar tudo dentro de `get_logger`) existe porque várias suítes de teste importam módulos como `service.host` e `application.task_service`, e isso criaria a pasta de log real do usuário (`%LOCALAPPDATA%`) só de rodar `pytest`, contaminando a máquina de quem testa. O preço é mais um passo manual (lembrar de chamar `configure_logging()` no bootstrap) se um novo entry point for criado no futuro.

**Pendente:** o Pascal Script do Inno Setup usa `Random()` sem seed explícita (a função `Randomize` da RTL Delphi não existe no scripting engine do Inno) — a entropia da chave de 6 dígitos depende do gerador interno do Inno, suficiente para identificação mas não para uso criptográfico. Se a chave precisar de garantias mais fortes no futuro, gerar no primeiro boot do app (Python, com `secrets`) em vez do instalador.

---

## 2026-06-20 — Renomeação `app/` → `ui/`

**O que mudou:** a pasta `app/` (camada de apresentação Qt) foi renomeada para `ui/`. Atualizados todos os imports (`main.py`, `application/task_service.py`, `tests/*`), `docs/ARQUITETURA.md` e `README.md`.

**Por quê:** `app/` e `application/` eram nomes visualmente quase idênticos para papéis bem diferentes (UI vs. casos de uso) — confundia na leitura da árvore de pastas e nos imports. `ui/` deixa o papel óbvio à primeira vista e elimina a ambiguidade com `application/`.

**Pendente:** nenhum — `docs/EVOLUCAO.md` (este arquivo) mantém entradas antigas que citam `app/...`; isso é esperado, são registro histórico do que era verdade na época, não atualizar retroativamente.

---

## 2026-06-20 — Empacotamento e distribuição: instalador .exe (PyInstaller + Inno Setup)

**O que mudou:** criado `installer/` (`app.spec`, `setup.iss`, `build.ps1`, `assets/app.ico`) para gerar um instalador `.exe` único, sem dependência de Python na máquina do operador. O wizard (Inno Setup) permite escolher pasta de instalação, e oferece checkboxes para "iniciar com o Windows" (em background, só ícone na tray) e "criar atalho na área de trabalho". O desinstalador (gerado automaticamente) remove arquivos do programa, atalhos, entrada de registro e dados de runtime. Como consequência, `service/security.py` (token + certificado TLS) e `main.py` (`debug_startup.log`) deixaram de calcular caminhos via `__file__` (que apontaria para dentro da pasta de instalação, normalmente sem permissão de escrita sem admin) e passaram a usar `%LOCALAPPDATA%\OperacaoAssistida`. Removido `install/create_shortcut.py` (substituído pelo instalador).

**Por quê:** o app vai para a máquina do operador, que não tem Python instalado e cujo acesso é só presencial/pontual (quem instala é a equipe responsável pelo projeto) — não dá pra depender de `pip install` + script manual. Separar "arquivos do programa" (pasta de instalação, pode ser somente leitura) de "dados de runtime" (sempre gravável, por usuário) é o que torna a instalação possível em `Program Files` sem exigir elevação para o uso do dia a dia.

**Trade-off aceito:** a entrada de startup (`HKCU\Run`) é gravada na conta do usuário que executa o instalador — se a instalação for feita com um usuário diferente do operador (ex.: conta de admin de TI), a tarefa de startup não vale para a conta do operador. Por ora aceitável porque quem instala faz isso logado como/para o próprio operador.

**Pendente:** não há assinatura de código (code signing) no `.exe` gerado — SmartScreen do Windows pode alertar na primeira execução. Avaliar certificado de assinatura se isso virar fricção na distribuição.

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
