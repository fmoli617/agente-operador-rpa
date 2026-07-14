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
ui/                                 # apresentação (Qt)
├── notification_window.py           # orquestração da UI — chama TaskService, nunca conhece o protocolo
├── task_store.py                     # repositório em memória de Task (busca/adiciona/remove, sem regra)
├── tray.py                           # ícone na system tray
└── widgets/
    └── task_row.py                    # widget de uma linha da lista — não conhece TaskStore nem TaskService
service/                             # infraestrutura — implementa as portas do domínio
├── host.py                           # WebSocket server (wss://) + WebSocketTaskResponder (implementa TaskResponder)
├── security.py                       # token de auth + certificado TLS autoassinado
└── logger.py                         # logger central — configure_logging() liga a gravação em disco (chamada só por main.py)
installer/                            # empacotamento e distribuição (PyInstaller + Inno Setup)
├── app.spec                           # empacota o app em .exe standalone
├── setup.iss                          # gera o instalador (.exe) final — wizard, captura de identificação (instalacao.conf), atalhos, desinstalador
└── build.ps1                          # script único: PyInstaller + Inno Setup
tests/                                # suíte de testes (ver tests/README.md)
docs/                                 # este diretório
```

## Regra de dependência

```txt
ui/  ──depende de──>  application/  ──depende de──>  domain/
service/  ──implementa──>  domain/ports.py
main.py  ──monta tudo (composition root)
```

`domain/` nunca importa nada de `ui/` ou `service/`. `application/task_service.py` não sabe que existe Qt nem WebSocket — só conhece `TaskStore` (repositório) e `TaskResponder` (interface). Quem decide *qual* responder usar é o `main.py`, na hora de montar o `TaskService`.

## Por que essa separação

- **`domain/task.py` é a única fonte de verdade sobre o que uma tarefa pode fazer** (mudar status, registrar sessão, receber QR, encerrar). Testável sem Qt e sem rede — ver `tests/test_task.py`.
- **`application/task_service.py` isola o protocolo da UI.** Antes, `notification_window.py` montava o JSON `{"type": "credentials", ...}` diretamente. Agora a UI chama `task_service.submit_credentials(...)` e não sabe nem precisa saber que isso vira uma mensagem WebSocket.
- **`domain/ports.py` (`TaskResponder`) é o contrato entre `application/` e `service/`.** Hoje só existe uma implementação (`WebSocketTaskResponder` em `service/host.py`), mas o ponto é que `TaskService` poderia receber qualquer outra implementação (ex.: HTTP, fila) sem mudar uma linha de `domain/` ou `application/`.
- **`ui/task_store.py` é só repositório agora** — busca, adiciona, remove. Mutação de estado (status, log, sessão) foi para `Task` (métodos do próprio objeto), não fica mais espalhada em `if`s da UI.
- **`widgets/task_row.py` não conhece nada acima dele.** Recebe primitivas (`title`, `message`) e um callback. `notification_window.py` mantém o mapeamento `task_id -> TaskRow` (`self._rows`) porque essa associação é puramente de apresentação — não pertence à entidade de domínio.

## Pontos de extensão conhecidos

- Novo tipo de mensagem do protocolo → `service/host.py` (dispatch) + novo método em `TaskService` (caso de uso) + slot correspondente em `ui/notification_window.py` — ver tabela de protocolo no `README.md`.
- Novo estado de tarefa → método em `domain/task.py` + chamada em `TaskService` + cor do badge em `ui/widgets/task_row.py`.
- Novo transporte (ex.: HTTP) → nova classe implementando `domain/ports.TaskResponder`, sem tocar em `domain/` nem `application/`.
- Novo dado de segurança (ex.: expiração de token) → `service/security.py`.
- Novo evento a logar → `service.logger.get_logger(__name__)` no topo do módulo, sem precisar saber se a gravação em disco já foi ligada (isso é responsabilidade de `main.py:configure_logging()`).

## Logger central (`service/logger.py`)

`get_logger(name)` retorna um `logging.Logger` filho de `operacao_assistida` — qualquer módulo pode chamar isso no import, sem custo (não toca em disco). A gravação real (criar `%LOCALAPPDATA%\OperacaoAssistida\logs\`, anexar o `TimedRotatingFileHandler`) só acontece quando `configure_logging()` é chamado — e isso só ocorre uma vez, dentro de `main()` em `main.py`. Essa separação existe para que importar um módulo (em testes, por exemplo) nunca crie a pasta de log real do usuário; os loggers ficam "mudos" até o composition root decidir ligar a gravação.

Hoje instrumentado em: `main.py` (ciclo de vida do processo), `service/host.py` (conexões/autenticação/protocolo), `service/security.py` (geração de token/certificado), `application/task_service.py` (casos de uso) e `ui/notification_window.py` + `ui/tray.py` (interações do operador). Nunca loga senha — só usuário, task_id e mensagens de erro/estado.
