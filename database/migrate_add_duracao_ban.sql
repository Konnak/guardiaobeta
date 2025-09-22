-- Migração: Adicionar coluna duracao_ban na tabela configuracoes_servidor
-- Data: 2025-09-22
-- Descrição: Adiciona suporte para configuração de duração de banimento

-- Adicionar coluna duracao_ban se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'configuracoes_servidor' 
        AND column_name = 'duracao_ban'
    ) THEN
        ALTER TABLE configuracoes_servidor 
        ADD COLUMN duracao_ban INTEGER DEFAULT 24;
        
        -- Adicionar comentário
        COMMENT ON COLUMN configuracoes_servidor.duracao_ban IS 'Duração em horas para banimento (1-8760 horas)';
        
        RAISE NOTICE 'Coluna duracao_ban adicionada com sucesso!';
    ELSE
        RAISE NOTICE 'Coluna duracao_ban já existe.';
    END IF;
END $$;
