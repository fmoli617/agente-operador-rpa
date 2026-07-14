# Operação Assistida

Sistema que transforma a máquina de um operador humano em um **ponto de autorização para automações RPA corporativas**.

Processos RPA rodando em servidores remotos precisam, em momentos específicos, de interação humana: login em sistemas, leitura de QR Code, digitação de código MFA. Este projeto resolve isso sem expor credenciais em variáveis de ambiente ou arquivos — o operador preenche em tempo real, a automação continua.

---

## Como funciona

```
Servidor RPA                    Máquina do Operador
(agente-consumidor)  ─── wss ──► (agente-operador)
                                       │
                               popup aparece na tela
                               operador preenche credenciais
                                       │
(agente-consumidor)  ◄─── wss ─── resposta em tempo real
automação continua
```

1. A máquina do operador roda o **agente-operador** em segundo plano — aparece só como ícone na bandeja do sistema
2. Quando uma automação precisa de interação humana, ela conecta via WebSocket seguro (`wss://`) e envia uma tarefa
3. Um popup aparece para o operador preencher o que for necessário (usuário/senha, QR Code, código MFA)
4. A automação recebe a resposta e continua — tudo sem o operador precisar acessar nenhum sistema diretamente

---

## Módulos

| Pasta | Papel | Para quem |
|---|---|---|
| [`agente-operador/`](agente-operador/) | App Windows que roda na máquina do operador. Expõe o host WebSocket e exibe o popup de autorização. | Equipe que mantém a infraestrutura do operador |
| [`agente-consumidor/`](agente-consumidor/) | SDK Python para incluir nas automações RPA. Abstrai toda a comunicação com o operador. | Desenvolvedor de automações |
| [`agente-supervisor/`](agente-supervisor/) | CLI de monitoramento. Mostra o status do host, processos ativos e IPs acessíveis na rede. | Qualquer pessoa que precise inspecionar o estado |

---

## Pré-requisitos

- Python 3.14+ — `C:\Program Files\python-global\python.exe` (ou equivalente)
- Windows (o `agente-operador` usa PyQt6 + pywin32)
- Os três módulos têm `requirements.txt` próprios — sem dependências compartilhadas entre eles

---

## Após o clone

### 1. Configurar o agente-operador (máquina do operador)

```powershell
cd agente-operador
python -m venv env
.\env\Scripts\pip install -r requirements-dev.txt
```

**Rodar em desenvolvimento:**

```powershell
.\env\Scripts\python main.py
```

O ícone aparece na bandeja do sistema. Na primeira execução, o app gera automaticamente:
- Token de autenticação → `%LOCALAPPDATA%\OperacaoAssistida\.secrets\ws_token.txt`
- Certificado TLS autoassinado → `%LOCALAPPDATA%\OperacaoAssistida\.secrets\host_cert.pem`

**Pegar o token** (necessário para o consumidor conectar):

```powershell
Get-Content "$env:LOCALAPPDATA\OperacaoAssistida\.secrets\ws_token.txt"
```

**Gerar o instalador .exe** (para distribuir para a máquina do operador sem Python):

```powershell
# Requer Inno Setup 6: winget install -e --id JRSoftware.InnoSetup
powershell -ExecutionPolicy Bypass -File installer\build.ps1 -Version 1.0.0
# Resultado: dist_installer\OperacaoAssistida-Setup-1.0.0.exe
```

**Rodar os testes:**

```powershell
.\env\Scripts\pytest
```

---

### 2. Configurar o agente-consumidor (nas automações)

```powershell
cd agente-consumidor
python -m venv env
.\env\Scripts\pip install -r requirements.txt
```

**Uso básico dentro de uma automação:**

```python
from agente_consumidor import OperadorSDK

sdk = OperadorSDK(
    machine="NOME-DA-MAQUINA-DO-OPERADOR",
    token="TOKEN_DO_ARQUIVO_WS_TOKEN_TXT",
)

resultado = sdk.solicitar_login_sync(
    host="PRD-RPA-R00",
    process="RPA000_SISTEMA",
    message="Solicitação de login recebida.",
)

usuario = resultado["user"]
senha   = resultado["password"]
codigo  = resultado.get("code")  # presente se o operador digitou um código MFA
```

**Simular o fluxo completo** (para testar sem uma automação real):

```powershell
.\env\Scripts\pip install -r requirements-dev.txt
.\env\Scripts\python examples\example.py --token SEU_TOKEN
```

---

### 3. Configurar o agente-supervisor

```powershell
cd agente-supervisor
python -m venv env
.\env\Scripts\pip install -r requirements.txt   # sem dependências externas
```

**Rodar:**

```powershell
.\env\Scripts\python -m agente_supervisor.main           # relatório único
.\env\Scripts\python -m agente_supervisor.main --watch   # atualiza a cada 10s
```

---

## Segurança

O host aceita conexões de qualquer máquina que alcance a porta 8765 na rede. Duas proteções:

- **Token de autenticação** — primeira mensagem de toda conexão deve ser `{"type": "auth", "token": "..."}`. Conexões sem token ou com token errado são encerradas com código 4001.
- **TLS (wss://)** — certificado autoassinado gerado na primeira execução. Impede sniffing de credenciais na rede local.

O certificado é autoassinado — consumidores precisam desabilitar a verificação de CA (`ssl.CERT_NONE`) ou fixar o certificado (`--cafile host_cert.pem`). Não expor a porta 8765 para fora da rede local.

---

## Documentação por módulo

Cada módulo tem sua documentação interna:

| Arquivo | Conteúdo |
|---|---|
| `agente-operador/README.md` | Instalação, protocolo WebSocket completo, fluxo de uma tarefa, segurança |
| `agente-operador/docs/ARQUITETURA.md` | Camadas, regra de dependência, pontos de extensão |
| `agente-operador/docs/EVOLUCAO.md` | Histórico cronológico de decisões estruturais |
| `agente-consumidor/README.md` | Uso do SDK, exemplos, referência de API |
| `agente-consumidor/docs/PROTOCOLO.md` | Especificação completa das mensagens WebSocket |
| `agente-consumidor/docs/EVOLUCAO.md` | Histórico do SDK |
| `agente-supervisor/README.md` | Uso da CLI, exemplo de saída, session ID |
| `agente-supervisor/docs/USO.md` | Integração com os outros módulos |
| `agente-supervisor/docs/EVOLUCAO.md` | Histórico do supervisor |
| `.claude/CLAUDE.md` | Contexto completo do monorepo (arquitetura, protocolo, convenções, pendências) |
