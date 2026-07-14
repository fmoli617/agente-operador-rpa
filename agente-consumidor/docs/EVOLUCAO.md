# Histórico de evolução — agente-consumidor

Log cronológico das decisões estruturais. Mais recente no topo. Cada entrada: o que mudou, por quê, o que ficou pendente.
Detalhes de uso ficam no `README.md` e em outros arquivos de `docs/` — aqui é o porquê e quando.

---

## 2026-07-13 — Validação ponta a ponta: consumidor ↔ operador

**O que mudou:** validação manual do fluxo completo em produção local. Fluxo executado com sucesso: auth wss:// → tarefa → credenciais → QR Code → código → credentials_error (retry) → QR Code → código → execution_error. Todos os estados do protocolo responderam corretamente na UI do operador.

**Por quê:** era o primeiro teste real do SDK atualizado (wss:// + auth) contra o host. Necessário para confirmar que os dois módulos se comunicam de verdade antes de evoluir qualquer coisa.

**Descoberta importante:** o token de autenticação real é gerado em `%LOCALAPPDATA%\OperacaoAssistida\.secrets\ws_token.txt`, não em `.secrets/` dentro da pasta do projeto. O arquivo `.secrets/` na raiz do projeto é resquício da v1 e ignorado pelo operador atual. README e CLAUDE.md atualizados para refletir isso.

**Pendente:** sem retry automático em caso de token expirado ou conexão recusada. Sem timeout configurável por etapa.

---

## 2026-07-13 — Separação em projeto independente + estrutura de pacote Python

**O que mudou:** o código que vivia em `v1-com-estrutura-tripartida/agente_consumidor/` foi movido para este projeto independente. Criada estrutura de pacote Python (`agente_consumidor/__init__.py` exporta `OperadorSDK`), `examples/` para o simulador, `docs/` com `PROTOCOLO.md` e `EVOLUCAO.md`. Adicionados `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `.markdownlint.json`.

**Por quê:** o projeto estava misturado com `agente-operador` e `agente-supervisor` em uma estrutura de monorepo sem separação clara. Separar em projetos independentes permite versionar, distribuir e evoluir cada módulo de forma autônoma.

**Pendente:** o SDK ainda usa `ws://` sem TLS e sem handshake de autenticação — incompatível com o `agente-operador` atual (que exige `wss://` + token). Ver próxima entrada.

---

## 2026-07-13 — Atualização do SDK para wss:// + autenticação por token

**O que mudou:** `agente_consumidor/sdk.py` atualizado para:
- Conectar via `wss://` com SSL (`ssl.create_default_context()` + `check_hostname=False` + `CERT_NONE` para certificado autoassinado, ou pinning via `cafile`)
- Enviar handshake de autenticação `{"type": "auth", "token": "..."}` como primeira mensagem de toda conexão
- `OperadorSDK.__init__` agora aceita `token` (obrigatório) e `cafile` (opcional — caminho para o `.pem` do host, para pinning em vez de desabilitar verificação)
- `examples/example.py` atualizado para aceitar `--token` e `--cafile` por linha de comando

**Por quê:** o `agente-operador` v2 exige TLS e token. O SDK antigo usava `ws://` sem autenticação e fechava com código 4001 ao conectar no host atual — os dois módulos não se falavam.

**Trade-off aceito:** `ssl.CERT_NONE` (verificação desabilitada) é o padrão para facilitar o desenvolvimento local. Em produção, passar `cafile=".secrets/host_cert.pem"` (copiado da máquina do operador) habilita pinning real sem exigir CA pública.

**Pendente:** sem retry automático em caso de token expirado ou conexão recusada. Sem timeout configurável por etapa (só timeout global da sessão).
