-- Migração para corrigir constraint UNIQUE em configuracoes_servidor
-- Execute este script no PostgreSQL do servidor para aplicar a correção

-- Adiciona constraint UNIQUE em id_servidor se não existir
DO $$
BEGIN
    -- Verifica se a constraint já existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'configuracoes_servidor' 
        AND constraint_name = 'configuracoes_servidor_id_servidor_key'
        AND constraint_type = 'UNIQUE'
    ) THEN
        -- Adiciona a constraint UNIQUE
        ALTER TABLE configuracoes_servidor 
        ADD CONSTRAINT configuracoes_servidor_id_servidor_key UNIQUE (id_servidor);
        
        RAISE NOTICE 'Constraint UNIQUE adicionada em id_servidor da tabela configuracoes_servidor';
    ELSE
        RAISE NOTICE 'Constraint UNIQUE já existe em id_servidor da tabela configuracoes_servidor';
    END IF;
END $$;

-- Verifica se a constraint foi criada corretamente
SELECT 
    constraint_name, 
    constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'configuracoes_servidor' 
AND constraint_type = 'UNIQUE';
