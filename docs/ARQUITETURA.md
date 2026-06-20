# Arquitetura

Visão de onde cada coisa vive hoje. Atualize este arquivo quando a estrutura mudar — é o mapa, não o histórico (isso fica em [EVOLUCAO.md](EVOLUCAO.md)).

## Camadas

```txt
main.py                            # composition root: monta TaskService, conecta sinais, bootstrap Qt
domain/                             # regra de negócio pura — não importa Qt nem websockets
├── task.py                          # entidade Task (status, sessão, log, QR) e suas transições
└── ports.py                         # interfaces que a infraestrutura precisa implementar (TaskResponder)
application/
└── task_service.py                  # casos de uso — única camada que conhece TaskStore E TaskResponder
app/                                 # apresentação (Qt)
├── notification_window.py           # orquestração da UI — chama TaskService, nunca conhece o protocolo
├── task_store.py                     # repositório em memória de Task (busca/adiciona/remove, sem regra)
├── tray.py                           # ícone na system tray
└── widgets/
    └── task_row.py                    # widget de uma linha da lista — não conhece TaskStore nem TaskService
service/                             # infraestrutura — implementa as portas do domínio
├── host.py                           # WebSocket server (wss://) + WebSocketTaskResponder (implementa TaskResponder)
└── security.py                       # token de auth + certificado TLS autoassinado
install/
└── create_shortcut.py                # atalho no Desktop + startup do Windows
tests/                                # suíte de testes (ver tests/README.md)
docs/                                 # este diretório
```

## Regra de dependência

```txt
app/  ──depende de──>  application/  ──depende de──>  domain/
service/  ──implementa──>  domain/ports.py
main.py  ──monta tudo (composition root)
```

`domain/` nunca importa nada de `app/` ou `service/`. `application/task_service.py` não sabe que existe Qt nem WebSocket — só conhece `TaskStore` (repositório) e `TaskResponder` (interface). Quem decide *qual* responder usar é o `main.py`, na hora de montar o `TaskService`.

## Por que essa separação

- **`domain/task.py` é a única fonte de verdade sobre o que uma tarefa pode fazer** (mudar status, registrar sessão, receber QR, encerrar). Testável sem Qt e sem rede — ver `tests/test_task.py`.
- **`application/task_service.py` isola o protocolo da UI.** Antes, `notification_window.py` montava o JSON `{"type": "credentials", ...}` diretamente. Agora a UI chama `task_service.submit_credentials(...)` e não sabe nem precisa saber que isso vira uma mensagem WebSocket.
- **`domain/ports.py` (`TaskResponder`) é o contrato entre `application/` e `service/`.** Hoje só existe uma implementação (`WebSocketTaskResponder` em `service/host.py`), mas o ponto é que `TaskService` poderia receber qualquer outra implementação (ex.: HTTP, fila) sem mudar uma linha de `domain/` ou `application/`.
- **`app/task_store.py` é só repositório agora** — busca, adiciona, remove. Mutação de estado (status, log, sessão) foi para `Task` (métodos do próprio objeto), não fica mais espalhada em `if`s da UI.
- **`widgets/task_row.py` não conhece nada acima dele.** Recebe primitivas (`title`, `message`) e um callback. `notification_window.py` mantém o mapeamento `task_id -> TaskRow` (`self._rows`) porque essa associação é puramente de apresentação — não pertence à entidade de domínio.

## Pontos de extensão conhecidos

- Novo tipo de mensagem do protocolo → `service/host.py` (dispatch) + novo método em `TaskService` (caso de uso) + slot correspondente em `app/notification_window.py` — ver tabela de protocolo no `README.md`.
- Novo estado de tarefa → método em `domain/task.py` + chamada em `TaskService` + cor do badge em `app/widgets/task_row.py`.
- Novo transporte (ex.: HTTP) → nova classe implementando `domain/ports.TaskResponder`, sem tocar em `domain/` nem `application/`.
- Novo dado de segurança (ex.: expiração de token) → `service/security.py`.
