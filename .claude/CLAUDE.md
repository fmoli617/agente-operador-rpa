# Operação Assistida — Contexto do Monorepo

Stack de três módulos Python que transforma a máquina de um operador humano em um ponto de autorização para automações RPA corporativas.

---

## REGRA OBRIGATÓRIA — Documentação de evolução

**Toda alteração de código em qualquer módulo deve ser registrada no `docs/EVOLUCAO.md` do respectivo projeto antes de encerrar a sessão.** Formato obrigatório:

```markdown
## YYYY-MM-DD — Título curto da mudança

**O que mudou:** descrição objetiva do que foi alterado (arquivos, funções, comportamento).

**Por quê:** motivação — constraint, bug, requisito, decisão de design.

**Trade-off aceito:** (se houver) o que foi sacrificado e por quê foi aceitável.

**Pendente:** itens que ficaram abertos ou que dependem desta mudança.
```

Esse arquivo é a fonte de verdade do histórico de cada módulo. Sem ele, sessões futuras não têm contexto para entender decisões passadas.

---

## PLANO DE LIMPEZA DA RAIZ

As pastas abaixo são **referência histórica** e devem ser removidas quando todos os três módulos estiverem funcionando de ponta a ponta (consumidor conectando no operador com TLS + auth):

| Pasta / Arquivo            | Remover quando                                              |
|----------------------------|-------------------------------------------------------------|
| `v1-com-estrutura-tripartida/` | agente-consumidor e agente-supervisor forem validados   |
| `v2-local-usuario/`        | agente-operador for validado em produção                    |
| `me-ajuda-pfv.txt`         | Pode remover agora — contexto foi absorvido neste CLAUDE.md |

**Não remover sem confirmação do usuário.** Registrar a remoção no `EVOLUCAO.md` correspondente.

---

## Módulos

| Pasta                | Papel                                                                                                                                                          | Status                                                  |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------|
| `agente-operador/`   | App Windows (PyQt6 + WebSocket host). A máquina do operador vira um host que recebe tarefas RPA e exibe popup para autorização humana (credenciais, QR code). | Produção — arquitetura limpa completa, instalador .exe  |
| `agente-consumidor/` | SDK Python para automações RPA. Conecta no host do operador e solicita credenciais/código em tempo real.                                                       | Funcional — wss:// + auth implementados em 2026-07-13  |
| `agente-supervisor/` | CLI de monitoramento. Gera relatório de estado: session ID, porta WebSocket, processos ativos, IPs.                                                            | Funcional — v1, sem integração ativa com o operador     |

---

## Ambiente de desenvolvimento

- **Python**: `C:\Program Files\python-global\python.exe` (3.14.2)
- **Virtualenv**: criar dentro de cada pasta (`python -m venv env`)
- **Operador em dev**: `python main.py` dentro de `agente-operador/`
- **Operador em produção**: instalador `.exe` gerado por `agente-operador/installer/build.ps1`

---

## Arquitetura do agente-operador (módulo principal)

```txt
main.py                    # composition root
domain/task.py             # entidade Task — regra de negócio pura, sem Qt/WebSocket
domain/ports.py            # interface TaskResponder
application/task_service.py # casos de uso
ui/notification_window.py  # orquestração da UI
ui/task_store.py           # repositório em memória
ui/tray.py                 # system tray
ui/widgets/task_row.py     # widget de linha da lista
service/host.py            # WebSocket server (wss://8765) + WebSocketTaskResponder
service/security.py        # token de auth + certificado TLS autoassinado
service/logger.py          # logger central (TimedRotatingFileHandler)
installer/                 # PyInstaller + Inno Setup
tests/                     # pytest + pytest-asyncio
docs/ARQUITETURA.md        # mapa de camadas e regra de dependência
docs/EVOLUCAO.md           # histórico cronológico de decisões (MANTER ATUALIZADO)
```

**Regra de dependência:** `ui/ → application/ → domain/`. `service/` implementa `domain/ports.py`. `main.py` monta tudo.

---

## Protocolo WebSocket (porta 8765, wss://)

**Handshake obrigatório:** primeira mensagem deve ser `{"type": "auth", "token": "..."}`. Token em `.secrets/ws_token.txt` ou env var `OPERADOR_WS_TOKEN`.

| Direção               | `type`              | Efeito                                          |
|-----------------------|---------------------|-------------------------------------------------|
| Consumidor → Operador | *(sem type)*        | Nova tarefa na lista                            |
| Consumidor → Operador | `qr_code`           | Exibe QR Code (PNG base64) no popup             |
| Consumidor → Operador | `login_error`       | QR permanece, código reabilita                  |
| Consumidor → Operador | `credentials_error` | Formulário volta do zero                        |
| Consumidor → Operador | `execution_started` | Status → "Em execução", creds limpas            |
| Operador → Consumidor | `credentials`       | `user`, `password`                              |
| Operador → Consumidor | `code`              | `code` (4 dígitos)                              |

Especificação completa: `agente-consumidor/docs/PROTOCOLO.md`.

---

## Session ID

`SHA256(usuario@maquina)[:16]` — gerado pelo `agente-supervisor`. Identifica unicamente cada host na rede. Usar para correlacionar logs entre os três módulos.

---

## Segurança

- TLS autoassinado: `.secrets/host_cert.pem` + `.secrets/host_key.pem` (gerados na 1ª execução do operador)
- Token: `%LOCALAPPDATA%\OperacaoAssistida\.secrets\ws_token.txt` (gerado na 1ª execução) — nunca commitar. O `.secrets/` dentro da pasta do projeto é resquício da v1 e ignorado.
- `.secrets/` está no `.gitignore` de todos os módulos
- Credenciais criptografadas em memória com Fernet durante a sessão
- Consumidor usa `ssl.CERT_NONE` por padrão (dev) ou pinning via `cafile` (prod)

---

## Pendências conhecidas

- [x] `agente-consumidor` atualizado para wss:// + handshake de auth (2026-07-13)
- [ ] Painel de acompanhamento em execução (caixa cinza na UI do operador)
- [ ] Suporte a múltiplas tarefas simultâneas na UI
- [ ] Code signing no instalador (SmartScreen alerta na primeira execução)
- [ ] Rotação automática de token / expiração de sessão no host
- [ ] `agente-supervisor` não está integrado ao `agente-operador` atual (foi removido da v2 na limpeza de imports)
- [ ] `STATUS_FILE` no supervisor usa `__file__` como base — quebra se instalado via pip

---

## Convenções de trabalho

- Ao terminar código novo no operador: **executar o atalho no Desktop**, não rodar pelo terminal
- Nunca commitar `.secrets/`, `*.log`, `dist/`, `dist_installer/`, `env/`
- Novos tipos de mensagem do protocolo: `service/host.py` (dispatch) → `TaskService` (caso de uso) → `ui/notification_window.py` (slot)
- Novo estado de tarefa: `domain/task.py` → `TaskService` → `ui/widgets/task_row.py` (cor do badge)
- **Toda sessão encerra com entrada em `docs/EVOLUCAO.md`** do módulo trabalhado
