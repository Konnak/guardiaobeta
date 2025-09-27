-- Migração para Sistema de Banimento - Sistema Guardião BETA
-- Adiciona tabela para controle de usuários banidos

-- Tabela de usuários banidos
CREATE TABLE IF NOT EXISTS usuarios_banidos (
    id SERIAL PRIMARY KEY,
    id_discord BIGINT UNIQUE NOT NULL,
    motivo TEXT NOT NULL,
    duracao VARCHAR(20) NOT NULL, -- 'permanent', '30', '90', '365'
    data_banimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_desbanimento TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    banido_por BIGINT, -- ID do admin que baniu
    desbanido_por BIGINT, -- ID do admin que desbaniu
    motivo_desbanimento TEXT
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_usuarios_banidos_discord ON usuarios_banidos(id_discord);
CREATE INDEX IF NOT EXISTS idx_usuarios_banidos_ativo ON usuarios_banidos(ativo);
CREATE INDEX IF NOT EXISTS idx_usuarios_banidos_data ON usuarios_banidos(data_banimento);

-- Comentários para documentação
COMMENT ON TABLE usuarios_banidos IS 'Sistema de banimento de usuários do Sistema Guardião';
COMMENT ON COLUMN usuarios_banidos.id_discord IS 'ID do usuário no Discord';
COMMENT ON COLUMN usuarios_banidos.motivo IS 'Motivo do banimento';
COMMENT ON COLUMN usuarios_banidos.duracao IS 'Duração do banimento (permanent, 30, 90, 365 dias)';
COMMENT ON COLUMN usuarios_banidos.ativo IS 'Se o banimento está ativo';
COMMENT ON COLUMN usuarios_banidos.banido_por IS 'ID do administrador que aplicou o banimento';
COMMENT ON COLUMN usuarios_banidos.desbanido_por IS 'ID do administrador que removeu o banimento';
