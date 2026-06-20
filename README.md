# Operação Assistida

App Windows que roda silencioso em background e torna a máquina do operador um **host WebSocket** para receber e autorizar tarefas de automação (RPA). O operador supervisiona, autoriza credenciais e acompanha a execução pelo popup no canto inferior direito da tela.

---

## Visão geral

Processos RPA em servidores remotos precisam de interação humana em momentos específicos — login, MFA, validações. Este app é o ponto de contato: o servidor envia uma tarefa, o operador preenche o que for necessário, e a execução continua automaticamente.

---

## Estrutura do projeto

```txt
c:\projetos\agente-operador-rpa\
├── main.py                          # Composition root — monta TaskService, conecta sinais, bootstrap Qt
├── domain/
│   ├── task.py                       # Entidade Task — regra de negócio pura, sem Qt/WebSocket
│   └── ports.py                      # Interface TaskResponder — contrato com a infraestrutura
├── application/
│   └── task_service.py               # Casos de uso (submit_credentials, submit_code, etc.)
├── app/
│   ├── notification_window.py       # Orquestração da UI — chama TaskService, não conhece o protocolo
│   ├── task_store.py                 # Repositório em memória de Task
│   ├── tray.py                       # Ícone na system tray
│   └── widgets/
│       └── task_row.py                # Widget de uma linha da lista
├── service/
│   ├── host.py                       # WebSocket server (porta 8765, wss://) + WebSocketTaskResponder
│   └── security.py                   # Token de autenticação + certificado TLS
├── install/
│   └── create_shortcut.py            # Cria atalho no Desktop + startup do Windows
├── tests/                            # Suíte de testes (ver tests/README.md)
├── docs/
│   ├── ARQUITETURA.md                # Mapa da estrutura, camadas e regra de dependência
│   └── EVOLUCAO.md                   # Histórico cronológico de decisões estruturais
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

Para o "porquê" de cada camada e o histórico de decisões, ver [docs/ARQUITETURA.md](docs/ARQUITETURA.md) e [docs/EVOLUCAO.md](docs/EVOLUCAO.md).

---

## Requisitos

- Python 3.14+
- `pip install -r requirements.txt`

```txt
PyQt6>=6.6.0
websockets>=12.0
pywin32>=306
cryptography>=42.0
qrcode>=7.0
pillow>=10.0
```

---

## Instalação

```powershell
cd c:\projetos\agente-operador-rpa
pip install -r requirements.txt
python install/create_shortcut.py
```

Isso cria o atalho **"Operação Assistida"** no Desktop e registra o app no startup do Windows (`HKCU\Run`).

Para desenvolvimento (rodar a suíte de testes), instale também `requirements-dev.txt` — ver [tests/README.md](tests/README.md).

---

## Como rodar

**Via atalho no Desktop** (produção — sem console):
Clique em "Operação Assistida". Usa `pythonw.exe`, não abre janela de terminal.

**Via terminal** (desenvolvimento):

```powershell
cd c:\projetos\agente-operador-rpa
python -m main
```

---

## Protocolo WebSocket (porta 8765, wss://)

### Handshake (obrigatório, primeira mensagem da conexão)

| `type` | Campos  | Descrição                                                                         |
|--------|---------|-----------------------------------------------------------------------------------|
| `auth` | `token` | Deve ser a primeira mensagem enviada pelo consumidor. Ver seção Segurança abaixo. |

Se o token não vier ou estiver errado, o host encerra a conexão (código 4001) sem processar mais nada.

### Consumidor → Operador

| `type`              | Descrição                                               |
|---------------------|---------------------------------------------------------|
| *(sem type)*        | Nova tarefa — exibe na lista do operador                |
| `qr_code`           | Imagem PNG em base64 para exibir ao operador            |
| `login_error`       | Erro de login — QR permanece, campo de código reabilita |
| `credentials_error` | Usuário/senha errados — formulário volta do zero        |
| `execution_started` | Execução iniciada — status atualiza para "Em execução"  |

### Operador → Consumidor

| `type`        | Campos                   |
|---------------|--------------------------|
| `credentials` | `user`, `password`       |
| `code`        | `code` (4 dígitos)       |

---

## Fluxo de uma tarefa

1. Servidor conecta em `wss://operador:8765`, autentica com `{"type": "auth", "token": "..."}` e envia dados da tarefa
2. Popup aparece — tarefa entra na lista com status **"Aguardando login"**
3. Operador clica na tarefa e preenche usuário + senha → **OK**
4. Badge verde confirma sessão registrada; status → **"Aguardando QR Code"**
5. Servidor envia QR Code → operador escaneia e digita o código → **OK**
6. Status → **"Em processamento"** → popup volta à lista automaticamente
7. Servidor responde: sucesso, erro de login (retry com QR), ou erro de credenciais (retry do zero)
8. Ao encerrar a conexão, a tarefa é removida da lista automaticamente

---

## Simulador (desenvolvimento)

> **Ainda não implementado neste repo.** `agente_consumidor/` (SDK do consumidor) não existe — ver checklist em [Esteira de Desenvolvimento e Operação](#esteira-de-desenvolvimento-e-operação). Por enquanto, use `tests/test_host.py` como referência de como um consumidor real deve se conectar (handshake `auth` + mensagens do protocolo).

---

## Supervisor

> **Ainda não implementado neste repo.** `agente_supervisor/` (geração de `status.txt`) não existe — foi removido de `main.py` na limpeza de imports quebrados (ver [docs/EVOLUCAO.md](docs/EVOLUCAO.md)). Fica como item de roadmap em [Esteira de Desenvolvimento e Operação](#esteira-de-desenvolvimento-e-operação).

---

## Instância única

Se o atalho for clicado com o app já rodando, a segunda instância detecta a porta 8765 em uso, exibe o popup na instância ativa e encerra.

---

## Segurança

O host WebSocket roda em `0.0.0.0:8765`, ou seja, qualquer máquina que alcance essa porta na rede consegue tentar se conectar. Duas proteções cobrem isso:

### Token de autenticação

A primeira mensagem de toda conexão precisa ser `{"type": "auth", "token": "..."}`. Se o token não vier ou estiver errado, o host fecha a conexão (código 4001) sem processar mais nada — nem tarefas, nem credenciais.

- O token é resolvido por `service/security.get_auth_token()`:
  1. Se a env var `OPERADOR_WS_TOKEN` estiver definida, ela tem prioridade (útil para fixar o mesmo token em todos os consumidores via configuração centralizada).
  2. Senão, é lido de `.secrets/ws_token.txt`; se o arquivo não existir, um token aleatório (`secrets.token_urlsafe(32)`) é gerado e salvo ali na primeira execução.
- `.secrets/` está no `.gitignore` — o token nunca deve ser commitado. Para rotacionar, apague o arquivo e reinicie o host (consumidores precisam ser atualizados com o novo valor).

### TLS (wss://)

O host serve via `wss://` usando um certificado autoassinado, gerado automaticamente por `service/security.get_server_ssl_context()` na primeira execução e reaproveitado depois (`.secrets/host_cert.pem` + `.secrets/host_key.pem`, válido por 10 anos, CN/SAN para `localhost` e `127.0.0.1`). Isso impede que credenciais e tokens sejam lidos por sniffing passivo na rede.

- Por ser autoassinado, qualquer consumidor (que não seja o próprio processo do operador) precisa desabilitar a verificação da CA ao conectar (`ssl.CERT_NONE` / equivalente no cliente) ou, idealmente, fixar (pin) o certificado de `.secrets/host_cert.pem`.
- Esse certificado **não tem validade fora da rede local** — não é assinado por uma CA pública. Não exponha esse host à internet.

### Limites conhecidos

- Não há rotação automática de token nem expiração de sessão — a confiança ainda é binária (token certo = acesso completo).
- O certificado autoassinado exige que cada consumidor desligue a verificação de CA, o que abre uma janela teórica para um atacante já posicionado na rede fazer *man-in-the-middle* se também souber o token. Para um ambiente com requisitos mais altos, o próximo passo seria distribuir/fixar o certificado real em vez de desabilitar a verificação.
- O escopo de autenticação é por conexão, não por tarefa — qualquer consumidor autenticado pode, em tese, responder por qualquer `task_id` que o host tenha em `_pending`.

---

## Esteira de Desenvolvimento e Operação

- [x] WebSocket host na porta 8765, instância única — segunda chamada via atalho envia `show_window` e reabre popup sem duplicar
- [x] Ícone na system tray + atalho no Desktop sem console, auto-start no Windows (HKCU Run)
- [x] Botão minimizar (`—`) no header (`.hide()`) — reabre pelo atalho ou pelo ícone na tray
- [x] Botão "Encerrar tudo" no rodapé (`QApplication.quit()`)
- [x] Lista de tarefas com badge de status colorido por estado:
  - Amarelo: "Aguardando login", "Aguardando QR Code", "Aguardando código"
  - Azul: "Em processamento"
  - Verde: "Em execução"
- [x] Detalhe da tarefa com fluxo completo:
  - Formulário usuário/senha → OK → some, badge verde "✓ Sessão: [usuario]" aparece
  - QR Code exibido 130×130 ao chegar do consumidor
  - Campo de código 4 dígitos → OK → volta à lista automaticamente
  - Caixa cinza placeholder "Em processamento..." (reservada para uso futuro)
- [x] Comportamento por tipo de retorno do consumidor:
  - `login_error`: QR permanece carregado, badge permanece, código reabilita
  - `credentials_error`: tudo limpo, formulário volta do zero
  - `execution_started`: status "Em execução", credenciais limpas
- [x] Tarefa removida automaticamente quando consumidor desconecta
- [x] Criptografia Fernet das credenciais em memória durante a sessão
- [x] Autenticação por token no WebSocket host
- [x] TLS (wss://) com certificado autoassinado
- [ ] Painel de acompanhamento em execução (área reservada na UI)
- [ ] Suporte a múltiplas tarefas simultâneas abertas
- [ ] Empacotamento corporativo (PyInstaller + NSIS/MSI)
- [ ] SDK do consumidor e `agente_supervisor` (mencionados em seções anteriores, ainda não existem neste repo)
