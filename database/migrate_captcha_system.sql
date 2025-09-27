-- Migração para Sistema de Captcha - Sistema Guardião BETA
-- Adiciona tabela para controle de captchas de guardiões em serviço

-- Tabela de captchas de guardiões
CREATE TABLE IF NOT EXISTS captchas_guardioes (
    id SERIAL PRIMARY KEY,
    id_guardiao BIGINT NOT NULL REFERENCES usuarios(id_discord) ON DELETE CASCADE,
    captcha_code VARCHAR(10) NOT NULL,
    captcha_question TEXT NOT NULL,
    captcha_answer VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'Pendente' NOT NULL, -- Pendente, Respondido, Expirado
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_resposta TIMESTAMP,
    data_expiracao TIMESTAMP NOT NULL,
    pontos_penalizados INTEGER DEFAULT 0,
    mensagem_id BIGINT, -- ID da mensagem do Discord para editar
    canal_id BIGINT NOT NULL -- ID do canal onde foi enviado
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_captchas_guardiao ON captchas_guardioes(id_guardiao);
CREATE INDEX IF NOT EXISTS idx_captchas_status ON captchas_guardioes(status);
CREATE INDEX IF NOT EXISTS idx_captchas_expiracao ON captchas_guardioes(data_expiracao);

-- Comentários para documentação
COMMENT ON TABLE captchas_guardioes IS 'Sistema de captcha para verificar atividade de guardiões em serviço';
COMMENT ON COLUMN captchas_guardioes.captcha_code IS 'Código único do captcha';
COMMENT ON COLUMN captchas_guardioes.captcha_question IS 'Pergunta do captcha (ex: operação matemática)';
COMMENT ON COLUMN captchas_guardioes.captcha_answer IS 'Resposta correta do captcha';
COMMENT ON COLUMN captchas_guardioes.status IS 'Status: Pendente, Respondido, Expirado';
COMMENT ON COLUMN captchas_guardioes.pontos_penalizados IS 'Pontos removidos por não responder';
COMMENT ON COLUMN captchas_guardioes.mensagem_id IS 'ID da mensagem do Discord para editar';
COMMENT ON COLUMN captchas_guardioes.canal_id IS 'ID do canal onde foi enviado';
