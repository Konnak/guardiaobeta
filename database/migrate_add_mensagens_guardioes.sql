-- Migração para adicionar tabela mensagens_guardioes
-- Execute este script no PostgreSQL para adicionar a nova tabela

-- Criar a tabela mensagens_guardioes
CREATE TABLE IF NOT EXISTS mensagens_guardioes (
    id SERIAL PRIMARY KEY,
    id_denuncia INTEGER NOT NULL REFERENCES denuncias(id) ON DELETE CASCADE,
    id_guardiao BIGINT NOT NULL REFERENCES usuarios(id_discord) ON DELETE CASCADE,
    id_mensagem BIGINT NOT NULL,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    timeout_expira TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'Enviada' NOT NULL
);

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_mensagens_guardioes_denuncia ON mensagens_guardioes(id_denuncia);
CREATE INDEX IF NOT EXISTS idx_mensagens_guardioes_guardiao ON mensagens_guardioes(id_guardiao);
CREATE INDEX IF NOT EXISTS idx_mensagens_guardioes_timeout ON mensagens_guardioes(timeout_expira);
CREATE INDEX IF NOT EXISTS idx_mensagens_guardioes_status ON mensagens_guardioes(status);

-- Adicionar comentário na tabela
COMMENT ON TABLE mensagens_guardioes IS 'Rastreamento de mensagens enviadas aos guardiões';

-- Verificar se a tabela foi criada
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename = 'mensagens_guardioes';

-- Mostrar estrutura da tabela
\d mensagens_guardioes;
