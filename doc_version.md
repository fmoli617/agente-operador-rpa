# Vamos planejar aqui toda a evolucao desse dia de hoje: 03/08/2026

## 1. Estado atual (não versionado)

Diff pendente na raiz (`git status`):

- **Removido**: `agente-consumidor/` inteiro (SDK antigo — `.gitignore`, `README.md`, `agente_consumidor/__init__.py`, `agente_consumidor/sdk.py`, `docs/EVOLUCAO.md`, `docs/PROTOCOLO.md`, `examples/example.py`, `pyproject.toml`, `requirements*.txt`) e `.claude/CLAUDE.md` (substituído pelo `CLAUDE.md` da raiz).
- **Novo, não trackeado**: `CLAUDE.md` (raiz), `doc_version.md` (este arquivo), `agente-bot/` (projeto novo).

`agente-bot/` é o sucessor do `agente-consumidor`: mesma ideia (SDK/bot que conecta no `agente-operador`), mas reestruturado para caber na forma como o bot real (em outra máquina) já funciona hoje — um orquestrador externo chama `bot.py`, que roda `main.py`, que consome uma fila de tarefas e executa `rpa_pipeline` por tarefa. A cópia antiga do `agente_consumidor` foi preservada em `agente-bot/versao-antiga/` só como referência de protocolo (auth + `wss://`), não como código ativo.

Estrutura atual de `agente-bot/` — só esqueleto, quase tudo vazio:

```text
agente-bot/
  bot.py                          # vazio
  config.yaml                     # app_name: rpa000_teste
  README.md                       # descreve o conceito, ainda não o código
  src/
    main.py                       # vazio
    app/fila.py                   # vazio
    app/rpa_pipeline.py           # vazio
    data/credenciais.py           # stub: CredenciaisAcesso com solicitar_usuario_assistido,
                                   #   solicitar_senha_assistido, solicitar_resolucao_mfa (pass)
    data/analitico.py             # vazio
    services/chrome.py            # vazio
    services/operacao_assistida.py # vazio — vai concentrar a integração com agente-operador
  versao-antiga/                  # cópia do agente-consumidor antigo, só referência
```

`tests/` e `db/` na raiz do monorepo existem mas estão **vazios** — ainda não há testes de integração entre os três módulos, nem base de dados/usuários.

`agente-operador/` está em produção e não muda de arquitetura (ver `CLAUDE.md`) — hoje ele registra `Task` com `session_user` (só o usuário logado, sem expiração) e não guarda histórico de chamadas entre reinícios.

---

## 2. Objetivos de hoje

### 2.1. `agente-bot` — implementar a integração com `agente-operador` (feito hoje)

Implementado: `services/operacao_assistida.py` (`SessaoOperador`), `data/credenciais.py`
(`CredenciaisAcesso`, com thread+loop dedicados para não quebrar o websocket entre chamadas síncronas),
`app/fila.py`, `app/rpa_pipeline.py`, `data/analitico.py` (mock de fila), `services/chrome.py`,
`src/main.py`, `bot.py`, `requirements.txt`, `config.yaml` (seção `operador:`) e `README.md` do módulo.
Falta implementar `_baixar_relatorio` (pipeline levanta `NotImplementedError` de propósito) e testar de
fato contra um `agente-operador` local — ver pendências em `agente-bot/README.md`.

Escopo original planejado:

- `services/operacao_assistida.py`: cliente WebSocket (`wss://`) que fala o protocolo já documentado em `agente-operador/service/host.py` — handshake `{"type":"auth","token":...}`, envia tarefa, `qr_code`, `login_error`, `credentials_error`, `execution_started`/`execution_error`, recebe `credentials`/`code`.
- `data/credenciais.py`: implementar os três métodos stub chamando `operacao_assistida` (solicitar usuário/senha, solicitar resolução de MFA via QR code).
- Modelo de referência para a etapa de MFA por QR code: <https://authenticationtest.com/totpChallenge/> — página pública com QR code + campo de código TOTP, usada como alvo de teste/demonstração do fluxo "escanear QR → digitar código" sem depender do site real da automação (que roda em outra máquina).
- `app/fila.py` + `app/rpa_pipeline.py`: esqueleto de consumo de fila e execução de pipeline por tarefa (meta de hoje é o suficiente para testar 1 tarefa ponta a ponta; múltiplas tarefas simultâneas fica para a seção de testes abaixo).
- Atualizar `agente-bot/README.md` conforme o código for saindo do estágio de esqueleto (ver seção 4).

### 2.2. `agente-operador` — controle de sessão e credenciais salvas por sistema

Decidido em conversa (03/08/2026), substitui a ideia inicial de "TTL de expiração":

1. **Histórico de sessão**: arquivo simples (não SQLite — sem necessidade de consulta estruturada por ora), guardado junto da pasta de instalação/runtime já existente (`%LOCALAPPDATA%\OperacaoAssistida`), registrando cada tarefa recebida e suas transições. Foco de hoje é a interação bot↔operador, não este histórico — fica como próximo passo, não bloqueia o item 2.1.
2. **Credenciais salvas por sistema** (não é mais "sessão com TTL"): o modelo real é —
   - o `agente-bot` roda tarefas contra **sistemas** nomeados (ex.: `analitico`, mapeado hoje em `agente-bot/src/data/`), usando Selenium para logar no site de cada sistema;
   - uma mesma tarefa pode pedir acesso ao mesmo sistema mais de uma vez, e tarefas diferentes podem chegar simultaneamente pedindo sistemas iguais ou diferentes;
   - o **agente-operador** (não o bot) passa a guardar `user`/`senha` por sistema, reaproveitados entre sessões — evita o operador humano ter que redigitar a credencial toda vez;
   - **mesmo com credencial salva, o popup humano de confirmação continua aparecendo em toda tarefa** (o humano confirma/libera o envio; só não precisa redigitar usuário/senha — o formulário já vem preenchido a partir do que está salvo para aquele sistema);
   - **QR code / MFA nunca é reaproveitado**: é solicitado em toda sessão, sempre um novo QR do consumidor para o operador exibir — não faz parte do que fica salvo.
   - Onde entra: novo componente em `service/` (ex. `service/credential_store.py`) associando `sistema → {user, senha}`, persistido em arquivo local (mesmo padrão de simplicidade do item 1 — decidir JSON criptografado com Fernet, já usado em memória hoje, em vez de texto puro); `TaskService`/`domain` passam a saber pedir "há credencial salva para este sistema?" antes de exigir preenchimento manual no popup; protocolo QR/código continua exatamente como está (por tarefa, nunca persistido).

**Implementado hoje (03/08/2026)**, respeitando `domain/ → application/ → ui/` e `service/` implementando portas:

- `domain/ports.py`: novo `CredentialStore` (ABC) — `get(system)`, `save(system, user, password)`, `forget(system)`.
- `domain/task.py`: `Task` ganhou campo `system: str | None` (vem do `host_name` da tarefa — em `agente-bot` isso é sempre o próprio nome do sistema, ex. `analitico`, já que lá `host == process == sistema`).
- `service/credential_store.py`: `FileCredentialStore` — Fernet, chave em `.secrets/credenciais.key`, dado em `.secrets/credenciais.enc` (JSON `{sistema: {user, password}}` cifrado). Testado: roundtrip, arquivo cifrado no disco (senha/usuário não aparecem em texto puro), `forget` remove só o sistema pedido, persiste entre instâncias.
- `application/task_service.py`: `register_task(..., system)`; novo `saved_credentials(system)` (usado pela UI para pré-preencher, nunca pula o popup); `submit_credentials` agora salva no store; `mark_credentials_error` agora chama `forget` (credencial errada não fica salva).
- `service/host.py`: `bridge.show_notification.emit(title, message, task_id, host_name)` — sistema passa a trafegar até a UI.
- `main.py`: `AppBridge.show_notification` ganhou 4º parâmetro (`system`); `TaskService` agora recebe `FileCredentialStore()`.
- `ui/notification_window.py`: `show_notification`/`_add_task` recebem `system`; `_open_detail` pré-preenche `_input_user`/`_input_pass` com `task_service.saved_credentials(task.system)` quando existe — **popup e clique em OK continuam obrigatórios** mesmo com campo pré-preenchido.
- Testes novos/ajustados em `agente-operador/tests/`: `test_credential_store.py` (5 testes) + 3 novos em `test_task_service.py` (salva ao submeter, prefill disponível antes de submeter, erro de credencial esquece o salvo) + `test_host.py` ajustado para a nova tupla do sinal. **Suíte completa do `agente-operador`: 41 passed.** Suíte de `tests/` (raiz): 3 passed (ajustada para a nova tupla de 4 itens do `show_notification`).

**Validado manualmente hoje (03/08/2026)**, com o operador rodando de verdade (`python main.py`, não a porta isolada de `tests/`):

1. Tarefa 1 (`analitico`) enviada pelo `agente-bot` real → popup real preenchido pelo usuário com `teste`/`1234` → log confirma `credencial salva para o sistema: analitico user=teste` e `.secrets/credenciais.enc` criado no disco.
2. Tarefa 2, mesmo sistema (`analitico`), enviada logo em seguida → popup abriu **pré-preenchido** com os mesmos valores (`teste`/`1234`, confirmado pelo usuário visualmente e pelo retorno idêntico ao `agente-bot`) → usuário só confirmou clicando OK, sem redigitar.
3. Processo encerrado (`taskkill /F`) ao final — ver seção 2.3.1 para a conferência de que isso equivale ao fechamento normal pela UI/tray.

Fecha o ciclo desenhado na seção 2.2: credencial reaproveitada entre sessões, popup humano nunca pulado.

### 2.3. `tests/` (raiz) — testes de integração dos 3 módulos (iniciado hoje)

Criado `tests/conftest.py` + `tests/test_integracao_bot_operador.py` (+ `tests/pytest.ini`,
`requirements-dev.txt` na raiz) — sobe o host real do `agente-operador` numa porta isolada e conecta o
cliente real do `agente-bot` (`SessaoOperador`) contra ele, sem mock de protocolo dos dois lados.
Rodado com `pytest`, **3 passed**:

- fluxo completo de uma tarefa (credenciais → QR → código → execução);
- duas tarefas simultâneas (`asyncio.gather`) não misturam `task_id`/credenciais;
- token inválido é recusado.

### 2.3.1. Ficou de fora até aqui — backlog vivo (atualizar a cada rodada)

- [x] **Teste do instalador — parte "modo dev" feita hoje (03/08/2026)**: escopo decidido com o
  usuário foi rodar em modo dev primeiro (sem empacotar), deixando a geração real do `.exe`
  (`installer/build.ps1`) para depois — **checado nesta sessão que não há Inno Setup nem PyInstaller
  instalados nesta máquina** (`iscc.exe` não encontrado, `pyinstaller` não instalado, sem `env/` em
  `agente-operador/`); fica pendente instalar essas ferramentas quando o teste do `.exe` empacotado for
  feito de fato. O que foi executado e validado, todo com o processo real (não a porta isolada de
  `tests/`):
  1. `python main.py` rodado de verdade — subiu Qt, tray, host WebSocket em `wss://0.0.0.0:8765`
     (log: `%LOCALAPPDATA%\OperacaoAssistida\logs\operacao_assistida.log`).
  2. Script usando o `SessaoOperador` real do `agente-bot` conectou nessa instância (token lido de
     `.secrets/ws_token.txt`) e registrou uma tarefa `analitico` — popup apareceu na tela do usuário de
     verdade.
  3. **Usuário preencheu credenciais no popup real** (`totp@authenticationtest.com` / `pa$$w0rd`) — o
     `agente-bot` recebeu via `solicitar_credenciais()`, fechando o ciclo ponta a ponta com interação
     humana real (não simulada via `WebSocketTaskResponder` como nos testes de `tests/`).
  4. Processo encerrado (`taskkill /F`) — log confirma `sessão encerrada`; porta de lock `8764`
     verificada livre logo em seguida; `%LOCALAPPDATA%\OperacaoAssistida\.secrets\` permanece intacto
     após o encerramento (esperado — só o desinstalador do Inno Setup remove essa pasta, via
     `[UninstallDelete]` em `installer/setup.iss`; encerrar o processo não deve nem deveria apagar
     `.secrets/`, senão o token/certificado seriam regerados a cada reinício).
  **Encerramento normal pela UI/tray — fechado por inspeção de código, não por clique ao vivo (03/08/2026,
  não dá pra automatizar clique no ícone da bandeja por aqui):** `ui/tray.py:_quit()` só chama
  `QApplication.quit()`; o outro caminho de saída (`bridge.quit_app.connect(app.quit)` em `main.py:105`,
  disparado quando uma segunda instância detecta que já há uma ativa) também só chama `app.quit()`. Não
  existe `atexit`, `aboutToQuit` nem `closeEvent` registrado em nenhum lugar do projeto (busca em todo o
  código) — ou seja, o fechamento normal pela bandeja e o `taskkill /F` usado acima produzem exatamente o
  mesmo resultado observável (nenhuma limpeza explícita roda em nenhum dos dois casos). Item fechado.

- [x] **`.exe` empacotado gerado e testado de verdade (03/08/2026)**: instalado Inno Setup (já estava
  presente, só fora do `PATH`/locais padrão — localizado em
  `C:\Users\fmoli\AppData\Local\Programs\Inno Setup 6\ISCC.exe`) e criado `agente-operador/env/` (venv,
  `pip install -r requirements.txt -r requirements-dev.txt`, inclui PyInstaller). Rodado
  `installer/build.ps1` de fato — gerou `dist_installer/OperacaoAssistida-Setup-1.0.0.exe` (32 MB).
  **Achado real, comportamento correto por design**: o instalador **não roda em modo silencioso**
  (`/VERYSILENT`) — o log mostra `Failed to proceed to next wizard page; aborting.` porque o checkbox de
  consentimento (`ConsentCheck`, `installer/setup.iss`) é validado em `NextButtonClick` mesmo sem UI
  visível, e não há flag de linha de comando pra pré-marcá-lo. Isso é o gate de consentimento humano
  funcionando como projetado, não um bug — instalação automatizada/silenciosa fica de fato bloqueada até
  alguém concordar manualmente.
  Testado então de forma interativa (usuário clicou o wizard):
  1. Instalado em `C:\Program Files\OperacaoAssistida\` — `instalacao.conf` gravado (`maquina`,
     `usuario`, `chave_instalacao`, `data_instalacao`).
  2. App abriu sozinho ao final da instalação (flag `postinstall` do `[Run]`) — host WebSocket real na
     porta 8765, `.secrets/` (incl. `credenciais.enc`/`credenciais.key`, já com a feature da seção 2.2)
     criados em `%LOCALAPPDATA%\OperacaoAssistida\`.
  3. Tarefa real enviada pelo `agente-bot` contra essa instância empacotada → popup real preenchido
     (`teste`/`1234`) → `agente-bot` recebeu de volta corretamente — confirma que o `.exe` fala o
     protocolo igual ao modo dev.
  4. Desinstalador rodado **com o app ainda em execução de propósito** (`unins000.exe /VERYSILENT`) —
     `InitializeUninstall()` do `setup.iss` mata o processo via `taskkill /IM ... /F` antes de apagar
     arquivos; log confirma `Uninstallation process succeeded. Removed all? Yes`. Conferido no disco:
     processo encerrado, `C:\Program Files\OperacaoAssistida\` removido,
     `%LOCALAPPDATA%\OperacaoAssistida\` removido por inteiro (secrets + credenciais salvas + logs juntos
     — `[UninstallDelete]` cobre tudo), sem entrada em `HKCU\...\Run` (não foi marcada a opção de
     startup neste teste).

  **Fecha, com isso, o item "limpeza de `%LOCALAPPDATA%`" do backlog abaixo** — testado via
  desinstalação real, não só por inspeção.
- [x] Limpeza de `%LOCALAPPDATA%\OperacaoAssistida` após desinstalação — **testado de verdade** (ver
  item do `.exe` acima): `[UninstallDelete]` remove `.secrets/` (token, TLS, credenciais salvas) e
  `logs/` por inteiro. Encerrar o processo sem desinstalar não limpa nada de propósito — correto,
  credencial por sistema é pra durar entre sessões (seção 2.2).
- [x] Base de usuários real em `db/` — feito em rodada anterior (seção 2.4): SQLite + seed, consumido
  por `agente-bot/src/app/fila.py` e pelo teste de múltiplas tarefas em `tests/`.
- [ ] Pipeline completo do `agente-bot` com Selenium/Chrome real — os testes de integração de hoje só
  cobrem o nível de protocolo WebSocket, não sobem navegador.
- [ ] `_baixar_relatorio` em `agente-bot/src/app/rpa_pipeline.py` — ainda `NotImplementedError`.
- [x] **Startup automático (`HKCU\...\Run`, task `startupicon`) — testado e corrigido (03/08/2026)**:
  reinstalado marcando "Iniciar automaticamente com o Windows". Registro confirmado:
  `HKCU\...\Run\OperacaoAssistida = "...\OperacaoAssistida.exe"`. **Bug real encontrado**: a descrição
  da tarefa em `installer/setup.iss:35` promete "em segundo plano, sem abrir janela — apenas o ícone na
  bandeja", mas `main.py` nunca implementava essa distinção — `window.show()` era chamado
  incondicionalmente, então a janela abria de qualquer forma. Confirmado ao vivo: matei o processo e
  rodei o comando exato do registro (`OperacaoAssistida.exe`, sem args) — **a janela abriu**, contrariando
  a promessa da UI de instalação.
  **Corrigido**: `main.py` agora só chama `window.show()` se `"--minimized" not in sys.argv`;
  `installer/setup.iss` passa `--minimized` só na entrada de registro do `startupicon` (o atalho normal
  do menu/desktop continua sem a flag, abre normal). Rebuild do `.exe` e reteste ao vivo: comando do
  registro com `--minimized` → **só o ícone na bandeja**, sem janela; clique no ícone → janela abre
  normalmente (sem regressão). Suíte completa do `agente-operador` reconfirmada: 41 passed. Desinstalado
  ao final — registro, `Program Files` e `%LOCALAPPDATA%` confirmados limpos.

Escopo original planejado:

Objetivo: exercitar o conjunto `agente-operador` + `agente-bot` (+ futuramente `agente-supervisor`) em conjunto, não cada módulo isolado (isso já existe dentro de `agente-operador/tests/`). Cobrir:

- **Instalação**: validar que o instalador `.exe` do `agente-operador` (`installer/build.ps1`) gera um artefato executável e que a primeira execução cria `.secrets/` e `instalacao.conf` corretamente.
- **Execução**: subir `agente-operador` local (dev, via `python main.py`) + `agente-bot` como cliente, e validar handshake + fluxo completo de uma tarefa (credenciais → QR → código → execução).
- **Limpeza**: validar que encerrar o `agente-operador` limpa credenciais ativas (depende do item 2.2) e que reinstalação/desinstalação não deixa resíduo em `%LOCALAPPDATA%`.
- **Base de usuários vinculados à automação via orquestrador**: massa de teste representando usuários/contas que o orquestrador (externo, na outra máquina) associaria a cada execução do `agente-bot` — provavelmente uma tabela/arquivo em `db/` na raiz (ainda vazio) que os testes de integração consultam para simular múltiplos operadores/contas.
- **Múltiplas tarefas simultâneas**: um `agente-bot` (ou vários) abrindo N conexões/tarefas concorrentes contra o mesmo `agente-operador` e validando que a UI/host não perde nem mistura `task_id`s — hoje isso é uma pendência conhecida do `agente-operador` (ver `docs/EVOLUCAO.md`: "Suporte a múltiplas tarefas simultâneas na UI" nunca foi validado de fato).

### 2.4. `db/` (raiz) — base de usuários (feito hoje, 03/08/2026)

SQLite (`db/schema.sql` + `db/seed.py`, `usuarios.db` gerado e ignorado pelo git) — tabela `usuarios`
(nome da conta de automação, sistema alvo, máquina do operador, ativo). Seed: 3 contas ativas (2 no
sistema `analitico`, 1 em `outro_sistema`) + 1 desativada (para provar que o filtro `ativo=1` funciona).

Consumido por:

- `agente-bot/src/app/fila.py` (`Fila`) — monta a fila real a partir das contas ativas; cai no mock de
  `data/analitico.py` só se `usuarios.db` não existir.
- `tests/test_integracao_bot_operador.py::test_multiplas_contas_da_base_db_nao_se_misturam` (novo) — abre
  uma sessão WebSocket por conta ativa da base (concorrente, via `asyncio.gather`) e confere que nenhuma
  credencial vaza entre `task_id`s. **Suíte de `tests/` completa: 4 passed.** Suíte do `agente-operador`
  (não tocada nesta rodada, só reconferida): 41 passed.

Pendente (ver `db/README.md`): ainda é massa de teste local, sem integração real com o orquestrador; sem
relação com o `session_id` do `agente-supervisor` (`SHA256(usuario@maquina)[:16]`).

---

## 3. Fora de escopo hoje (mantido do `CLAUDE.md`)

- Não remover `v1-com-estrutura-tripartida/` nem `v2-local-usuario/` sem confirmação do usuário.
- `agente-operador` mantém a arquitetura em camadas — as duas features novas (sessão + credenciais) entram respeitando `domain/ → application/ → ui/`, sem atalho.

---

## 4. `agente-bot/README.md`

Hoje descreve só o conceito (orquestrador chama `bot.py` → `main.py` → consome fila → `rpa_pipeline`). Conforme os itens da seção 2.1 forem implementados, atualizar para descrever:

- o protocolo real de comunicação com `agente-operador` (herdado de `agente-consumidor/docs/PROTOCOLO.md`, hoje só em `versao-antiga/docs/PROTOCOLO.md`);
- como rodar localmente para teste manual (equivalente ao "operador em dev" do `CLAUDE.md`);
- o papel de cada arquivo em `src/` conforme deixarem de ser stubs.

---

## 5. Decisões tomadas (03/08/2026)

1. Ordem de trabalho: **`agente-bot` primeiro** — fechar o fluxo ponta a ponta (services/operacao_assistida.py, credenciais.py) contra o `agente-operador` já existente, usando authenticationtest.com/totpChallenge/ como alvo de teste do MFA.
2. Histórico de sessão: arquivo simples, junto da pasta de instalação/runtime — sem SQLite. Não é prioridade de hoje.
3. Credenciais por sistema: guardadas no `agente-operador` (não no bot), reaproveitadas entre sessões; popup humano de confirmação continua obrigatório em toda tarefa; QR/MFA nunca é salvo — sempre solicitado por sessão. Ver seção 2.2 revisada.

## 5.1. Remoção de `agente-bot/versao-antiga/` (03/08/2026)

Antes de apagar, revisado item a item o que ainda não estava consolidado na estrutura nova:

- `agente_consumidor/sdk.py` (`OperadorSDK`) — já consolidado em `services/operacao_assistida.py:SessaoOperador` desde a primeira rodada de hoje.
- `examples/example.py` (simulador interativo, dirige manualmente `login_error`/`credentials_error`/`execution_error`/QR de validação) — **não estava consolidado**; portado para `agente-bot/scripts/simulador_manual.py`, adaptado ao vocabulário de "sistema" e à `SessaoOperador` atual. Testado (`--help` funciona, `py_compile` ok).
- `docs/PROTOCOLO.md` — conteúdo já resumido na seção "Protocolo com o agente-operador" do `agente-bot/README.md`.
- `docs/EVOLUCAO.md`, `pyproject.toml`, `requirements*.txt`, `.markdownlint.json` — histórico/empacotamento do pacote pip standalone antigo; sem valor de código para consolidar (o `agente-bot` novo não é distribuído como pacote pip).
- `.gitignore` — `agente-bot/` não tinha um próprio; criado agora (`agente-bot/.gitignore`), reaproveitando o conteúdo do antigo.
- `requirements-dev.txt` do `agente-bot` criado (antes só existia `requirements.txt`), com `qrcode`+`pillow` (usados só pelo `scripts/simulador_manual.py`).

Pasta `agente-bot/versao-antiga/` removida depois dessa revisão.

## 5.2. Pipeline Selenium — sessão pai + sessões filhas (03/08/2026)

Construído `agente-bot/src/services/multi_sessao.py`: sessão pai (headless) faz login completo em
`https://authenticationtest.com/totpChallenge/` (usuário/senha + QR/MFA assistidos pelo
`agente-operador`, nunca reaproveitados) e, autenticada, expõe os cookies pra abrir N sessões filhas
(visíveis, sem repetir login) tileadas em partes iguais no monitor principal. `app/rpa_pipeline.py`
foi reescrito pra delegar o login pra cá em vez de duplicar seletores (os que tinha antes —
`#username`, `img#qrcode` — nunca tinham sido validados contra a página real e estavam errados).

Seletores confirmados contra a página real (`curl` direto): `#email`, `#password`, `#totpmfa`,
`img[alt="TOTP Seed QR Code"]`, `input[value="Log In"]`, `div.alert-success` (só existe na resposta
do POST). **Achado**: depois do login o site vai pra `/loginSuccess/` — única URL que reflete a
sessão autenticada; `/totpChallenge/` sempre volta a mostrar o formulário do zero mesmo com cookie
válido.

**Validado com sucesso, duas vezes, de ponta a ponta**, com um stub de credenciais instantâneo (sem
humano): login real + QR real (screenshot do elemento) + código MFA real (computado do seed
publicado no nome do arquivo do QR, via `pyotp`) + POST de login bem-sucedido + cookie propagado
corretamente pras 4 filhas, tileadas 2x2 (960x540 cada, confirmado por screenshot de cada janela).

**Correção (mesmo dia, a pedido do usuário — "deve ter algo errado")**: a alegação de que as 4
filhas ficaram "autenticadas" (`div.alert-success` presente em `/loginSuccess/`) era um
falso-positivo. Confirmado depois: `/loginSuccess/` mostra "Success!" **mesmo sem cookie
nenhum**; `/totpChallenge/` sempre volta ao formulário em branco mesmo com cookie válido
pós-login; `PHPSESSID` é emitido só de visitar a página, antes de qualquer login, e não muda com
autenticação. **Este site de demo não implementa sessão real por cookie nessas rotas** — não é um
bug do código, é uma limitação do site escolhido como alvo de teste. O que fica provado de fato é
só o mecanismo (cópia de cookies + tiling funcionam tecnicamente, valor do `PHPSESSID` replicado
fielmente), não que isso representa autenticação real neste site específico. Decisão do usuário
(pergunta feita, resposta registrada): manter como prova de mecanismo apenas — reuso de sessão
autenticada de verdade só será validável contra um sistema real com sessão de fato gated por
cookie (ex.: o sistema `analitico` real, quando/se disponível). Documentado direto no docstring de
`multi_sessao.py` pra não repetir esse engano em sessões futuras.

### 5.2.1. Bug conhecido, não resolvido: captura do QR falha 100% das vezes no fluxo assistido real

**Passando pelo `agente-operador` real (WebSocket real + popup humano), a captura do QR falhou
6 de 6 vezes** — sempre em `_capturar_qr_base64`, ora `StaleElementReferenceException`, ora
`TimeoutException` puro (elemento nem aparece mais). **0 de 8+ tentativas isoladas falharam.**
Investigação extensa, feita a pedido explícito do usuário ("deve ter algo errado"):

1. **Hipótese "site/CDN instável" (descartada)** — reproduzida a sequência exata
   (`driver.get()` → esperar 35-45s → preencher campos → checar QR) isoladamente: sempre
   encontrou o elemento. Não é volume de tráfego nem rate-limit percebido no navegador.
2. **Hipótese "duração do atraso humano" (descartada, e invertida)** — as 6 falhas reais tiveram
   latência humana de **3 a 90s** (a mais rápida, 3s, ainda assim falhou); as reproduções
   isoladas bem-sucedidas usaram 35-45s de espera — ou seja, esperas **mais longas** que várias
   das falhas reais, e mesmo assim funcionaram. Duração não é a variável.
3. **Falha de metodologia encontrada e corrigida**: as primeiras "validações isoladas" bem-sucedidas
   (seção 5.2) não chamavam a função de produção `abrir_sessao_pai` — um script de teste separado
   duplicava a lógica com `find_element` direto. Corrigido: passou a testar a função real
   (`teste_funcao_real.py`, `teste_funcao_real_delay.py`) — **ainda assim, sempre funcionou**,
   inclusive com `CredenciaisAcesso` real (thread + event loop de produção) e 40s de atraso
   simulado via `asyncio.sleep` (sem WebSocket real).
4. **Isolada a variável real**: testado `abrir_sessao_pai` com `SessaoOperador` **real** (biblioteca
   `websockets`, I/O de rede assíncrona de verdade) contra o `agente-operador` rodando de verdade —
   **falhou**, mesmo com resposta em 3s. Essa é a única variável que, quando presente, correlaciona
   100% com a falha (6/6) e, quando ausente, correlaciona 100% com sucesso (8+/8+).
5. **Hipótese "ProactorEventLoop/IOCP do Windows" (testada e descartada)**: `CredenciaisAcesso`
   passou a forçar `asyncio.SelectorEventLoop` em vez do padrão do Windows — não mudou nada,
   7ª falha idêntica. Revertido (não vale a complexidade sem benefício comprovado).

**Diagnóstico no ponto em que a investigação parou**: I/O de rede assíncrona real (via
`websockets`, dentro de `SessaoOperador`/`CredenciaisAcesso`, rodando numa thread em background)
concorrente com o Chrome/chromedriver headless no processo principal causa a falha — mas a causa
exata (por que, e por que só afeta a busca do QR e não usuário/senha, que é buscado logo depois do
mesmo tipo de espera) não foi encontrada. Confirmar isso a fundo exigiria isolar o Selenium num
processo separado do cliente WebSocket — mudança estrutural, não um ajuste pontual.

**Decisão do usuário (pergunta feita, resposta registrada)**: parar a investigação por aqui.
Mecanismo (login, captura de QR, MFA, cookies, tiling) já está provado correto isoladamente —
ver seção 5.2. A integração ponta a ponta com o WebSocket real do `agente-operador` fica como
**bug conhecido, não resolvido**, documentado aqui em detalhe pra retomar quando fizer sentido
(ex.: ao integrar com um sistema real, que não vai depender de um navegador headless disputando
recursos com um cliente WebSocket no mesmo processo Python do jeito que este teste fez).

Mitigações já aplicadas mesmo sem confirmar a causa raiz (corretas de qualquer forma):
`WebDriverWait` explícito em toda leitura de elemento (antes usava `find_element` direto) e retry
na captura do QR (relocalizando o elemento, sem recarregar a página).

## 6. Pergunta em aberto

- `db/` (2.4): base de usuários é só para os testes de integração (mock) ou vai virar dependência real do orquestrador em produção?
