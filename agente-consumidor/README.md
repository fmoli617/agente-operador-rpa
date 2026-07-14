# agente-consumidor

SDK Python para conectar automações RPA ao **agente-operador** via WebSocket. Abstrai o protocolo de comunicação: a automação pede credenciais/código ao operador humano e aguarda a resposta em tempo real.

---

## Instalação

```bash
pip install -r requirements.txt
```

Para rodar os exemplos interativos:

```bash
pip install -r requirements-dev.txt
```

---

## Uso básico

O token fica em `%LOCALAPPDATA%\OperacaoAssistida\.secrets\ws_token.txt` na máquina do operador (ou na env var `OPERADOR_WS_TOKEN`). O arquivo `.secrets/` dentro da pasta do projeto é ignorado pelo operador atual.

```python
from agente_consumidor import OperadorSDK

sdk = OperadorSDK(machine="NOME-DA-MAQUINA-DO-OPERADOR", token="SEU_TOKEN")

resultado = sdk.solicitar_login_sync(
    host="PRD-RPA-R00",
    process="RPA000_SISTEMA",
    message="Solicitação de login recebida.",
)

usuario = resultado["user"]
senha = resultado["password"]
codigo = resultado.get("code")  # presente se o operador digitou um código MFA
```

Para pinning de certificado TLS (produção):

```python
sdk = OperadorSDK(machine="NOME-DA-MAQUINA", token="SEU_TOKEN", cafile="host_cert.pem")
```

### Versão assíncrona

```python
import asyncio
from agente_consumidor import OperadorSDK

async def main():
    sdk = OperadorSDK(machine="NOME-DA-MAQUINA", token="SEU_TOKEN")
    resultado = await sdk.solicitar_login(
        host="PRD-RPA-R00",
        process="RPA000_SISTEMA",
    )
    print(resultado)

asyncio.run(main())
```

---

## Simulador interativo

Simula o fluxo completo de uma automação RPA contra o agente-operador:

```bash
python examples/example.py --token SEU_TOKEN
python examples/example.py --token SEU_TOKEN --machine OUTRO-HOST
python examples/example.py --token SEU_TOKEN --cafile host_cert.pem
```

---

## Protocolo

Ver [docs/PROTOCOLO.md](docs/PROTOCOLO.md) para a especificação completa das mensagens WebSocket.

---

## Estrutura

```txt
agente-consumidor/
├── agente_consumidor/
│   ├── __init__.py
│   └── sdk.py           # OperadorSDK — toda a lógica de comunicação
├── examples/
│   └── example.py       # Simulador interativo do fluxo RPA
├── docs/
│   └── PROTOCOLO.md     # Especificação do protocolo WebSocket
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```
