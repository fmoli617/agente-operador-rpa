# Testes

```powershell
pip install -r requirements-dev.txt
pytest
```

| Arquivo                        | O que cobre                                                              |
|---------------------------------|---------------------------------------------------------------------------|
| `test_security.py`              | Geração/persistência do token, geração/reuso do certificado TLS         |
| `test_task.py`                  | Transições da entidade `Task` (domain) — puro, sem Qt e sem TaskStore   |
| `test_task_store.py`            | Repositório `TaskStore` — busca/adiciona/remove                         |
| `test_task_service.py`          | Casos de uso (`TaskService`) com um `TaskResponder` fake — sem WebSocket real |
| `test_host.py`                  | Protocolo WebSocket real: rejeição sem token, token errado, fluxo completo, contagem de sessões |
| `test_notification_window.py`   | UI em modo offscreen: fluxo credenciais → QR → código → execução, erro de credenciais, dismiss |
| `test_main_lock.py`             | Trava de instância única (porta 8764)                                   |

Não há teste de renderização visual (cores, posicionamento) — só lógica e transições de estado. A UI roda com `QT_QPA_PLATFORM=offscreen` (configurado em `conftest.py`), então qualquer asserção sobre layout pixel-a-pixel não é coberta aqui.

`isolated_secrets` (em `conftest.py`) redireciona `service.security` para um diretório temporário — os testes nunca tocam no `.secrets/` real do projeto.
