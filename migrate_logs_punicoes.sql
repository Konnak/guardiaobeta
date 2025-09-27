-- Migração para criar tabela logs_punicoes
-- Este script adiciona a tabela de logs de punições para o mural da vergonha

-- Cria a tabela logs_punicoes se não existir
CREATE TABLE IF NOT EXISTS logs_punicoes (
    id SERIAL PRIMARY KEY,
    id_usuario BIGINT NOT NULL,
    username VARCHAR(255), -- Nome de usuário do Discord
    display_name VARCHAR(255), -- Nome de exibição do Discord
    avatar_url TEXT, -- URL do avatar do usuário
    tipo_punicao VARCHAR(50) NOT NULL, -- 'Intimidou', 'Grave', 'Ban', 'Kick', 'Warn', 'Mute', etc.
    motivo TEXT NOT NULL,
    duracao VARCHAR(100) DEFAULT 'Permanente',
    duracao_segundos INTEGER, -- Duração em segundos para cálculos
    data_punicao TIMESTAMP DEFAULT NOW(),
    aplicado_por BIGINT NOT NULL, -- ID do admin que aplicou
    id_servidor BIGINT, -- Servidor onde foi aplicada (opcional)
    ativa BOOLEAN DEFAULT TRUE, -- Se a punição ainda está ativa
    data_remocao TIMESTAMP, -- Quando foi removida (se aplicável)
    removido_por BIGINT, -- Quem removeu a punição
    motivo_remocao TEXT, -- Motivo da remoção
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Cria índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_usuario ON logs_punicoes(id_usuario);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_tipo ON logs_punicoes(tipo_punicao);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_data ON logs_punicoes(data_punicao);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_ativa ON logs_punicoes(ativa);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_servidor ON logs_punicoes(id_servidor);

-- Adiciona comentários na tabela
COMMENT ON TABLE logs_punicoes IS 'Tabela de logs de punições para o mural da vergonha';
COMMENT ON COLUMN logs_punicoes.id_usuario IS 'ID do usuário punido no Discord';
COMMENT ON COLUMN logs_punicoes.username IS 'Nome de usuário do Discord';
COMMENT ON COLUMN logs_punicoes.display_name IS 'Nome de exibição do Discord';
COMMENT ON COLUMN logs_punicoes.avatar_url IS 'URL do avatar do usuário';
COMMENT ON COLUMN logs_punicoes.tipo_punicao IS 'Tipo de punição aplicada';
COMMENT ON COLUMN logs_punicoes.duracao_segundos IS 'Duração em segundos para cálculos';

-- Verifica se a tabela foi criada
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename = 'logs_punicoes';
