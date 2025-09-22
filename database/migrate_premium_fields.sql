-- Migração para adicionar campos motivo e stripe_session_id na tabela servidores_premium
-- Execute este script no PostgreSQL

-- Adicionar coluna motivo (opcional)
ALTER TABLE servidores_premium 
ADD COLUMN IF NOT EXISTS motivo VARCHAR(500) DEFAULT 'Premium ativado';

-- Adicionar coluna stripe_session_id (opcional)
ALTER TABLE servidores_premium 
ADD COLUMN IF NOT EXISTS stripe_session_id VARCHAR(200);

-- Adicionar comentários
COMMENT ON COLUMN servidores_premium.motivo IS 'Motivo da ativação do premium';
COMMENT ON COLUMN servidores_premium.stripe_session_id IS 'ID da sessão Stripe para rastreamento';

-- Verificar se as colunas foram adicionadas
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'servidores_premium' 
    AND table_schema = 'public'
ORDER BY ordinal_position;
