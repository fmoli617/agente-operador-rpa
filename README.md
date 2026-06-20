# Operação Assistida

App Windows que roda silencioso em background e torna a máquina do operador um **host WebSocket** para receber e autorizar tarefas de automação (RPA). O operador supervisiona, autoriza credenciais e acompanha a execução pelo popup no canto inferior direito da tela.

---

## Visão geral

Processos RPA em servidores remotos precisam de interação humana em momentos específicos — login, MFA, validações. Este app é o ponto de contato: o servidor envia uma tarefa, o operador preenche o que for necessário, e a execução continua automaticamente.

---

## Estrutura do projeto

```txt
c:\projetos\agente-operador-rpa\
├── agente_operador/                     # App do operador (esta máquina)
│   ├── main.py                          # Entry point — bridge Qt ↔ WebSocket
│   ├── app/
│   │   ├── notification_window.py       # UI principal (popup, lista de tarefas, detalhe)
│   │   └── tray.py                      # Ícone na system tray
│   ├── service/
│   │   └── host.py                      # WebSocket server (porta 8765)
│   └── install/
│       └── create_shortcut.py           # Cria atalho no Desktop + startup do Windows
├── requirements.txt
├── README.md
└── CONTEXTO_CHAT.md
```

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
cd c:\projetos\operacao_assistida
pip install -r requirements.txt
python agente_operador/install/create_shortcut.py
```

Isso cria o atalho **"Operação Assistida"** no Desktop e registra o app no startup do Windows (`HKCU\Run`).

---

## Como rodar

**Via atalho no Desktop** (produção — sem console):
Clique em "Operação Assistida". Usa `pythonw.exe`, não abre janela de terminal.

**Via terminal** (desenvolvimento):

```powershell
cd c:\projetos\operacao_assistida python -m agente_operador.main
```

---

## Protocolo WebSocket (porta 8765)

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

1. Servidor conecta em `ws://operador:8765` e envia dados da tarefa
2. Popup aparece — tarefa entra na lista com status **"Aguardando login"**
3. Operador clica na tarefa e preenche usuário + senha → **OK**
4. Badge verde confirma sessão registrada; status → **"Aguardando QR Code"**
5. Servidor envia QR Code → operador escaneia e digita o código → **OK**
6. Status → **"Em processamento"** → popup volta à lista automaticamente
7. Servidor responde: sucesso, erro de login (retry com QR), ou erro de credenciais (retry do zero)
8. Ao encerrar a conexão, a tarefa é removida da lista automaticamente

---

## Simulador (desenvolvimento)

```powershell
cd c:\projetos\operacao_assistida
python agente_consumidor/example.py
# ou em outra máquina:
python agente_consumidor/example.py --machine NOME-DO-HOST
```

---

## Supervisor

```powershell
cd c:\projetos\operacao_assistida
$env:PYTHONUTF8=1
python agente_supervisor/main.py           # snapshot
python agente_supervisor/main.py --watch   # atualiza a cada 10s
```

---

## Instância única

Se o atalho for clicado com o app já rodando, a segunda instância detecta a porta 8765 em uso, exibe o popup na instância ativa e encerra.

---

## Esteira de Desenvlvimento e Operação

- [x] WebSocket host na porta 8765
- [x] Instância única (segunda chamada via atalho reabre o popup, não duplica)
- [x] Ícone na system tray + atalho no Desktop sem console
- [x] Auto-start no Windows (HKCU Run)
- [x] Lista de tarefas com status em tempo real (badges coloridos)
- [x] Botão minimizar (`—`) no header — reabre pelo atalho ou pelo ícone na tray
- [x] Botão "Encerrar tudo" no rodapé
- [x] Fluxo completo: credenciais → QR Code → código → execução
- [x] Criptografia Fernet das credenciais em memória durante a sessão
- [x] Badge de sessão registrada por tarefa
- [x] Remoção automática de tarefa ao desconectar
- [x] SDK do consumidor (`agente_consumidor/sdk.py`)
- [ ] Autenticação no WebSocket host
- [ ] Painel de acompanhamento em execução (área reservada na UI)
- [ ] Suporte a múltiplas tarefas simultâneas abertas
- [ ] Empacotamento corporativo (PyInstaller + NSIS/MSI)
- [x] WebSocket host porta 8765, instância única — segunda chamada via atalho envia `show_window` e reabre popup sem duplicar
- [x] Botão `—` no header minimiza o popup (`.hide()`); reabre pelo atalho ou pelo ícone na tray
- [x] Botão "Encerrar tudo" chama `QApplication.quit()` diretamente
- [x] Ícone na system tray, atalho no Desktop sem console, auto-start Windows
- [x] Lista de tarefas com badge de status colorido por estado:
  - Amarelo: "Aguardando login", "Aguardando QR Code", "Aguardando código"
  - Azul: "Em processamento"
  - Verde: "Em execução"
- [x] Detalhe da tarefa com fluxo completo:
  - Formulário usuário/senha → OK → some, badge verde "✓ Sessão: [usuario]" aparece
  - QR Code exibido 130×130 ao chegar do consumidor
  - Campo de código 4 dígitos → OK → volta à lista automaticamente
  - Caixa cinza placeholder "Em processamento..." (reservada para uso futuro)
- [x] Criptografia Fernet das credenciais em memória durante a sessão
- [x] Comportamento por tipo de retorno:
  - `login_error` (opção 2): QR permanece carregado, badge permanece, código reabilita
  - `credentials_error` (opção 3): tudo limpo, formulário volta do zero
  - `execution_started` (opção 4): status "Em execução", credenciais limpas
- [x] Tarefa removida automaticamente quando consumidor desconecta
- [x] `agente_supervisor` gera `status.txt` a cada 60s
- [ ] Autenticação no WebSocket host
- [ ] Suporte a múltiplas tarefas abertas simultaneamente
- [ ] Empacotamento corporativo (PyInstaller + NSIS/MSI)
