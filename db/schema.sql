-- Base de usuários/contas de automação vinculados ao orquestrador.
-- Cada linha diz: "esta conta, deste sistema, roda contra o agente-operador
-- desta máquina" — é o que o orquestrador (em outra máquina) consultaria
-- para saber qual conexão abrir e qual credencial de sistema está em jogo
-- antes de disparar uma execução do agente-bot.
CREATE TABLE IF NOT EXISTS usuarios (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nome              TEXT NOT NULL,               -- identificação da conta de automação (não é a credencial de login do sistema)
    sistema           TEXT NOT NULL,                -- sistema alvo, ex.: "analitico" — chave usada por CredentialStore no agente-operador
    maquina_operador  TEXT NOT NULL,                -- host/IP onde o agente-operador desta conta roda
    ativo             INTEGER NOT NULL DEFAULT 1    -- 0/1 — permite desativar sem apagar histórico
);

CREATE INDEX IF NOT EXISTS idx_usuarios_sistema ON usuarios(sistema);
CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo);
