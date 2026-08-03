# RPA001 - Automação para efetuar o uma atividade de webscrapy

Nesse momento, trouxe a estrutura atual que temos de um bot, para implementar o que haviamos feito para o consumidor.

Como esse bot funciona hoje, um orquestrador de tarefas realiza a simples funcao de executar o bot.py na raiz, que por sua vez executa a main, que centraliza o processamento
principal do app, que é consumir uma fila de solicitacoes de baixa de relatorios de um site, e executa para cada relatorio a definicao realizada no rpa_pipeline, que por sua
vez tem mapeado cada etapa.

Vamos trabalhar aqui na implementacao dentro da estrutura atual que utilizamos no bot, a interacao para o conceito do projeto do agente-operador que é o app desktop
que vai trabalhar em conjunto.

Em service, toda a logica protegida para realizar as chamadas necessarias. gerenciar e aguardar o retorno, aplicar regras de timeout, gerencia a sessao inicial de contato
da tarefa em execucao, seguindo a ideia de tarefa ja utilizado, a tarefa que vai ser mantida ativa no app, é em execucao na nossa estrutura atual.

---

## Estrutura (03/08/2026)

```text
bot.py                           # entrypoint chamado pelo orquestrador
config.yaml                      # app_name + conexão com o agente-operador (machine/port/cafile)
src/
  main.py                        # composition root: lê config.yaml + OPERADOR_WS_TOKEN, consome a fila
  app/
    fila.py                      # Fila — hoje carrega de data/analitico.py (mock local)
    rpa_pipeline.py               # orquestra 1 solicitação: Selenium + credenciais assistidas + MFA
  data/
    analitico.py                  # SolicitacaoRelatorio + carregar_fila() (mock — sem orquestrador real ainda)
    credenciais.py                # CredenciaisAcesso — ponte síncrona (Selenium) <-> assíncrona (WebSocket)
  services/
    chrome.py                     # fábrica do WebDriver
    operacao_assistida.py         # SessaoOperador — cliente WebSocket do protocolo do agente-operador
    multi_sessao.py               # sessão pai (login+MFA assistido) + N sessões filhas (cookie reuso, tiling)
scripts/
  simulador_manual.py             # dirige manualmente todos os retornos do protocolo (login_error,
                                   #   credentials_error, execution_error, etc.) contra um operador real
```

`versao-antiga/` (SDK antigo `agente-consumidor`) foi removida em 03/08/2026 — tudo de valor foi
consolidado antes: a lógica do `OperadorSDK` virou `services/operacao_assistida.py:SessaoOperador`, e o
simulador interativo (`examples/example.py`) virou `scripts/simulador_manual.py` (mesma ideia, adaptada
ao vocabulário de "sistema" e à `SessaoOperador` atual). `docs/PROTOCOLO.md` da versão antiga está
resumido na seção "Protocolo com o agente-operador" abaixo.

## Protocolo com o agente-operador

Herdado de `versao-antiga/docs/PROTOCOLO.md` (mesmo handshake, mesmos tipos de mensagem), com uma
mudança de vocabulário: onde o SDK antigo falava em `host`/`process` genéricos, aqui cada tarefa é
sempre escopada a um **sistema** (ex.: `analitico`) — é o que `SessaoOperador.conectar(sistema, ...)`
envia como `host`/`process`.

Fluxo de uma tarefa (`rpa_pipeline.executar_pipeline`):

1. `SessaoOperador` conecta e registra a tarefa (`task_id` novo por tarefa).
2. `CredenciaisAcesso` pede usuário/senha ao operador — hoje o formulário é sempre preenchido do zero
   pelo humano; a ideia de credencial salva por sistema no `agente-operador` (reaproveitada entre
   sessões, mas ainda com popup de confirmação humana) está desenhada em `../doc_version.md` (seção 2.2)
   e ainda não implementada nesse módulo.
3. Selenium loga no sistema, captura o QR Code da tela e envia via `enviar_qr` — QR **nunca** é salvo,
   é sempre pedido de novo em toda sessão.
4. Operador humano escaneia e digita o código; `aguardar_codigo()` devolve ao pipeline, que confirma o MFA.
5. `execution_started` / `execution_error` avisam o operador do resultado.

## Rodando localmente para teste

Alvo de teste do MFA (no lugar do site real, que roda em outra máquina):
<https://authenticationtest.com/totpChallenge/> — página pública com QR Code + campo de código, usada
para validar o fluxo "escanear QR → digitar código" ponta a ponta contra um `agente-operador` local.

```powershell
# na pasta agente-operador/, com o operador rodando (python main.py)
$env:OPERADOR_WS_TOKEN = (Get-Content .secrets/ws_token.txt)

# na pasta agente-bot/
$env:OPERADOR_WS_TOKEN = "<mesmo token acima>"
python bot.py
```

Para testar manualmente todos os retornos do protocolo (erro de login, credenciais erradas, execução
com erro, QR de validação) sem escrever uma automação de verdade:

```powershell
pip install -r requirements-dev.txt
python scripts/simulador_manual.py --token SEU_TOKEN
```

## Sessão pai + sessões filhas (`services/multi_sessao.py`)

Modelo: uma sessão "pai" (Chrome headless) faz o login completo contra
`https://authenticationtest.com/totpChallenge/` — usuário/senha e QR/MFA assistidos pelo
`agente-operador`, como já descrito acima. Depois de autenticada, os cookies dela são
reaproveitados para abrir N sessões "filhas" (Chrome visível, sem login/MFA de novo),
posicionadas lado a lado em partes iguais no monitor principal.

Seletores confirmados contra a página real (03/08/2026): `#email`, `#password`, `#totpmfa`,
`img[alt="TOTP Seed QR Code"]`, `input[value="Log In"]`. Achado importante: depois do POST de
login, o site navega para `/loginSuccess/` — é a **única** URL que reflete a sessão autenticada;
recarregar `/totpChallenge/` sempre volta a mostrar o formulário do zero, mesmo com cookie válido
(por isso `abrir_sessoes_filhas` navega as filhas para `/loginSuccess/`, não para `/totpChallenge/`).

**Validado com sucesso, duas vezes, de ponta a ponta** (login pai real + captura de QR real +
código MFA real computado do seed publicado na página + POST de login bem-sucedido + cookie
propagado corretamente para as 4 filhas, tileadas 2x2 na tela) — sempre com um stub de
credenciais instantâneo (sem esperar humano).

**Correção importante**: a alegação inicial de que as 4 filhas ficaram "autenticadas" era um
falso-positivo — a checagem usada (`div.alert-success` presente em `/loginSuccess/`) aparece
nessa página **mesmo sem cookie nenhum** (confirmado depois, via `requests` puro, a pedido do
usuário). Este site de demo não implementa sessão real por cookie nessas rotas: `/loginSuccess/`
sempre mostra "Success!", `/totpChallenge/` sempre volta ao formulário em branco mesmo com cookie
válido, e o `PHPSESSID` é emitido só de visitar a página, antes de qualquer login. O que fica
realmente provado é só o mecanismo — o cookie é replicado fielmente para as 4 filhas — não que
isso representa autenticação de verdade nesse site específico. Reuso de sessão autenticada de
verdade só será validável contra um sistema real com sessão de fato gated por cookie.

**Bug conhecido, não resolvido — captura do QR falha 100% das vezes no fluxo assistido real** (6/6
tentativas com `agente-operador` + WebSocket real; 0/8+ em qualquer reprodução isolada, incluindo
com a função de produção `abrir_sessao_pai` e `CredenciaisAcesso` real com atraso simulado de 40s).
Investigação extensa descartou: instabilidade do site (não reproduzida isolada), duração do atraso
humano (as falhas reais foram as *mais rápidas*, 3-90s; reproduções de 35-45s sempre funcionaram) e
`ProactorEventLoop`/IOCP do Windows (forçar `SelectorEventLoop` não mudou nada). A única variável
que correlaciona 100% com a falha: usar o `SessaoOperador` real (I/O de rede assíncrona de verdade
via `websockets`, numa thread em background) concorrente com o Chrome headless no mesmo processo.
Causa exata não confirmada — exigiria isolar o Selenium num processo separado do cliente WebSocket.
Decisão registrada: parar a investigação por ora (ver `doc_version.md`, seção 5.2.1, para o passo a
passo completo). Mitigações aplicadas mesmo sem causa raiz confirmada: `WebDriverWait` explícito em
toda leitura de elemento e retry na captura do QR (relocalizando o elemento) antes de desistir.

## Pendências

- **Bug conhecido**: captura do QR falha 100% das vezes no fluxo assistido real (ver seção acima e
  `doc_version.md` 5.2.1) — investigação parada por decisão do usuário, não resolvida.
- `_baixar_relatorio` em `app/rpa_pipeline.py` não está implementado (`NotImplementedError`) — falta a
  navegação/download real, que depende do sistema alvo verdadeiro (ainda só temos o mock `analitico`).
- `data/analitico.py:carregar_fila()` é mock local — sem integração real com o orquestrador.
- Sem suporte a múltiplas tarefas simultâneas neste processo (cada `bot.py` roda a fila sequencialmente,
  uma solicitação por vez); testar várias instâncias/conexões concorrentes contra o mesmo
  `agente-operador` é objetivo dos testes de integração em `../tests/` (ver `../doc_version.md`).
- `app/rpa_pipeline.py` delega o login para `services/multi_sessao.py:abrir_sessao_pai` (seletores já
  validados contra a página real) — não duplica mais seletores próprios.
