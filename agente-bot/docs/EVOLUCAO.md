# Histórico de evolução — agente-bot

Log cronológico (mais recente no topo) das decisões estruturais do módulo. Cada entrada: o que mudou, por quê, e o que ficou pendente. Detalhes de uso ficam no `README.md` — aqui é o porquê e quando.

---

## 2026-08-03 — Pipeline Selenium (sessão pai + sessões filhas) e correção de seletores em rpa_pipeline.py

**O que mudou:** criado `services/multi_sessao.py` — sessão pai (Chrome headless) faz login completo contra `https://authenticationtest.com/totpChallenge/` (usuário/senha + QR/MFA assistidos pelo `agente-operador`) e, autenticada, expõe cookies pra abrir N sessões filhas (Chrome visível, sem repetir login), tileadas em partes iguais no monitor principal. `app/rpa_pipeline.py` foi reescrito pra delegar login a este módulo em vez de duplicar seletores — os que tinha antes (`#username`, `img#qrcode`) nunca haviam sido validados contra a página real e estavam errados.

**Por quê:** pedido do usuário para provar o conceito de sessão pai/filhas contra um site real com QR code, usando `agente-operador` como intermediário assistido.

**Trade-off aceito:** nenhum de propósito — mas ver bug conhecido abaixo.

**Bug conhecido, não resolvido**: a captura do QR (`_capturar_qr_base64`) falha 100% das vezes (6/6) quando testada de ponta a ponta contra o `agente-operador` real (WebSocket real via `SessaoOperador`/`websockets`), mas nunca falhou (0/8+) em nenhuma reprodução isolada — incluindo com a função de produção real e `CredenciaisAcesso` real com atraso simulado de 40s via `asyncio.sleep`. Descartado: instabilidade do site (não reproduzida isolada), duração do atraso humano (as falhas reais foram as mais rápidas, 3-90s, mais rápidas que as reproduções de 35-45s que sempre funcionaram), e `ProactorEventLoop`/IOCP do Windows (forçar `SelectorEventLoop` não mudou nada — testado e revertido). A única variável que correlaciona 100% com a falha: usar I/O de rede assíncrona real (`websockets`) numa thread em background concorrente com o Chrome headless no mesmo processo Python. Causa exata não confirmada — exigiria isolar o Selenium num processo separado do cliente WebSocket. Decisão do usuário: parar a investigação por ora. Detalhe completo em `../doc_version.md`, seção 5.2.1.

**Correção de validação (mesma sessão)**: a alegação inicial de que as 4 sessões filhas ficavam "autenticadas" (checando `div.alert-success` em `/loginSuccess/`) era falso-positivo — essa página mostra "Success!" mesmo sem cookie nenhum. `authenticationtest.com` não implementa sessão real por cookie nessas rotas (confirmado via `requests` puro). O que fica provado é só o mecanismo (cópia de cookie + tiling funcionam tecnicamente), não autenticação real neste site específico.

**Pendente:** bug do QR acima; `_baixar_relatorio` ainda não implementado.

---

## 2026-08-03 — Fluxo completo do bot: WebSocket, credenciais, fila, pipeline

**O que mudou:** implementado o esqueleto vazio de `agente-bot` que existia até então:
- `services/operacao_assistida.py` (`SessaoOperador`) — cliente WebSocket real do protocolo do `agente-operador`, adaptado do SDK antigo (`agente_consumidor`) para o conceito de "sistema" (host=process=sistema).
- `data/credenciais.py` (`CredenciaisAcesso`) — ponte síncrona (Selenium) ↔ assíncrona (WebSocket), com thread+loop dedicados (necessário porque a conexão fica presa ao loop em que foi criada).
- `data/analitico.py`, `app/fila.py` — fila de tarefas, hoje carregada de `db/usuarios.db` (com fallback pro mock local).
- `services/chrome.py` — fábrica do WebDriver.
- `src/main.py`, `bot.py`, `requirements.txt`, `config.yaml` (seção `operador:`).
- `scripts/simulador_manual.py` — portado de `versao-antiga/examples/example.py`, dirige manualmente todos os retornos do protocolo contra um operador real.

Validado de ponta a ponta contra o `agente-operador` real rodando em modo dev e como `.exe` empacotado (ver `../doc_version.md`).

**Por quê:** consolidar o conceito de `agente-consumidor` (SDK antigo) na estrutura real do bot (orquestrador → `bot.py` → fila → pipeline), fechando o fluxo ponta a ponta com o `agente-operador`.

**Pendente:** `_baixar_relatorio` não implementado; sem suporte a múltiplas tarefas simultâneas num único processo `bot.py` (fila roda sequencial).

---

## 2026-08-03 — Remoção de `versao-antiga/` (SDK `agente_consumidor`)

**O que mudou:** removida a pasta `versao-antiga/` (cópia do `agente-consumidor` antigo) depois de revisão item a item confirmando que tudo de valor já estava consolidado: `OperadorSDK` → `services/operacao_assistida.py`; simulador interativo → `scripts/simulador_manual.py` (não estava consolidado, portado nesta revisão); `docs/PROTOCOLO.md` → resumido no `README.md`; `.gitignore` → criado um próprio para `agente-bot/` (não existia).

**Por quê:** pedido do usuário, com a ressalva de garantir que nada ficasse pra trás sem ser revisto.

**Pendente:** nenhum.
