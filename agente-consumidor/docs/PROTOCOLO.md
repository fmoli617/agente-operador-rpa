# Protocolo WebSocket — agente-consumidor ↔ agente-operador

Porta padrão: **8765**. Transporte: `wss://` (TLS autoassinado — desabilitar verificação de CA no cliente ou fixar o certificado de `.secrets/host_cert.pem`).

---

## Handshake (obrigatório)

A **primeira mensagem** de toda conexão deve ser a autenticação:

```json
{ "type": "auth", "token": "<token>" }
```

O token fica em `.secrets/ws_token.txt` na máquina do operador (ou na env var `OPERADOR_WS_TOKEN`). Se o token estiver errado ou ausente, o host encerra a conexão com código 4001.

---

## Consumidor → Operador

| Campo / `type`      | Quando enviar                                      | Campos obrigatórios                              |
|---------------------|----------------------------------------------------|--------------------------------------------------|
| *(sem type)*        | Registrar uma nova tarefa                          | `task_id`, `host`, `process`, `message`          |
| `qr_code`           | Enviar imagem QR para o operador escanear          | `task_id`, `type`, `image` (PNG em base64)       |
| `login_error`       | Código inválido — operador redigita (QR permanece) | `task_id`, `type`, `message`                     |
| `credentials_error` | Usuário/senha errados — formulário volta do zero   | `task_id`, `type`, `message`                     |
| `execution_started` | Execução iniciada com sucesso                      | `task_id`, `type`                                |
| `execution_error`   | Erro inesperado — encerra a tarefa                 | `task_id`, `type`, `message`                     |

### Exemplo — nova tarefa

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "host": "PRD-RPA-R00",
  "process": "RPA000_SISTEMA",
  "message": "Solicitação de login recebida."
}
```

---

## Operador → Consumidor

| `type`        | Quando chega                              | Campos retornados        |
|---------------|-------------------------------------------|--------------------------|
| `credentials` | Operador preencheu usuário e senha        | `task_id`, `user`, `password` |
| `code`        | Operador digitou o código MFA/QR          | `task_id`, `code`        |

---

## Fluxo típico

```
Consumidor                        Operador (host)
    |                                  |
    |--- auth (token) ---------------->|
    |--- nova tarefa ----------------->|  popup aparece
    |                                  |  operador preenche usuário/senha
    |<-- credentials ------------------|
    |--- qr_code ---------------------->|  QR exibido
    |                                  |  operador escaneia e digita código
    |<-- code --------------------------|
    |--- execution_started ----------->|  status atualiza
    |                                  |
    |  (fecha conexão)                 |  tarefa removida da lista
```
