-- Schema de Inicialização do Sistema Guardião BETA
-- Execute este script no PostgreSQL do Discloud para criar todas as tabelas

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id_discord BIGINT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    nome_completo VARCHAR(255) NOT NULL,
    idade INTEGER NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    pontos INTEGER DEFAULT 0 NOT NULL,
    experiencia INTEGER DEFAULT 0 NOT NULL,
    em_servico BOOLEAN DEFAULT FALSE NOT NULL,
    categoria VARCHAR(50) DEFAULT 'Usuário' NOT NULL,
    data_criacao_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ultimo_turno_inicio TIMESTAMP,
    cooldown_prova TIMESTAMP,
    cooldown_dispensa TIMESTAMP,
    cooldown_inativo TIMESTAMP
);

-- Tabela de denúncias
CREATE TABLE IF NOT EXISTS denuncias (
    id SERIAL PRIMARY KEY,
    hash_denuncia VARCHAR(64) UNIQUE NOT NULL,
    id_servidor BIGINT NOT NULL,
    id_canal BIGINT NOT NULL,
    id_denunciante BIGINT NOT NULL,
    id_denunciado BIGINT NOT NULL,
    motivo TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'Pendente' NOT NULL,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    e_premium BOOLEAN DEFAULT FALSE NOT NULL,
    resultado_final VARCHAR(50)
);

-- Tabela de mensagens capturadas
CREATE TABLE IF NOT EXISTS mensagens_capturadas (
    id SERIAL PRIMARY KEY,
    id_denuncia INTEGER NOT NULL REFERENCES denuncias(id) ON DELETE CASCADE,
    id_autor BIGINT NOT NULL,
    conteudo TEXT NOT NULL,
    anexos_urls TEXT,
    timestamp_mensagem TIMESTAMP NOT NULL
);

-- Tabela de votos dos guardiões
CREATE TABLE IF NOT EXISTS votos_guardioes (
    id SERIAL PRIMARY KEY,
    id_denuncia INTEGER NOT NULL REFERENCES denuncias(id) ON DELETE CASCADE,
    id_guardiao BIGINT NOT NULL REFERENCES usuarios(id_discord) ON DELETE CASCADE,
    voto VARCHAR(20) NOT NULL,
    data_voto TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT unique_voto_guardiao_denuncia UNIQUE (id_denuncia, id_guardiao)
);

-- Tabela de servidores premium
CREATE TABLE IF NOT EXISTS servidores_premium (
    id_servidor BIGINT PRIMARY KEY,
    data_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_fim TIMESTAMP NOT NULL
);

-- Tabela de configurações dos servidores (para servidores premium)
CREATE TABLE IF NOT EXISTS configuracoes_servidor (
    id SERIAL PRIMARY KEY,
    id_servidor BIGINT NOT NULL UNIQUE,
    canal_log BIGINT,
    duracao_intimidou INTEGER DEFAULT 1 NOT NULL,
    duracao_intimidou_grave INTEGER DEFAULT 6 NOT NULL,
    duracao_grave INTEGER DEFAULT 12 NOT NULL,
    duracao_grave_4plus INTEGER DEFAULT 24 NOT NULL
);

-- Tabela para rastrear mensagens enviadas aos guardiões
CREATE TABLE IF NOT EXISTS mensagens_guardioes (
    id SERIAL PRIMARY KEY,
    id_denuncia INTEGER NOT NULL REFERENCES denuncias(id) ON DELETE CASCADE,
    id_guardiao BIGINT NOT NULL REFERENCES usuarios(id_discord) ON DELETE CASCADE,
    id_mensagem BIGINT NOT NULL,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    timeout_expira TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'Enviada' NOT NULL
);

-- Tabela de logs de punições
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

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_usuarios_categoria ON usuarios(categoria);
CREATE INDEX IF NOT EXISTS idx_usuarios_em_servico ON usuarios(em_servico);
CREATE INDEX IF NOT EXISTS idx_denuncias_status ON denuncias(status);
CREATE INDEX IF NOT EXISTS idx_denuncias_data_criacao ON denuncias(data_criacao);
CREATE INDEX IF NOT EXISTS idx_denuncias_premium ON denuncias(e_premium);
CREATE INDEX IF NOT EXISTS idx_votos_denuncia ON votos_guardioes(id_denuncia);
CREATE INDEX IF NOT EXISTS idx_votos_guardiao ON votos_guardioes(id_guardiao);
CREATE INDEX IF NOT EXISTS idx_mensagens_denuncia ON mensagens_capturadas(id_denuncia);
CREATE INDEX IF NOT EXISTS idx_servidores_premium_fim ON servidores_premium(data_fim);
CREATE INDEX IF NOT EXISTS idx_mensagens_guardioes_denuncia ON mensagens_guardioes(id_denuncia);
CREATE INDEX IF NOT EXISTS idx_mensagens_guardioes_guardiao ON mensagens_guardioes(id_guardiao);
CREATE INDEX IF NOT EXISTS idx_mensagens_guardioes_timeout ON mensagens_guardioes(timeout_expira);
CREATE INDEX IF NOT EXISTS idx_mensagens_guardioes_status ON mensagens_guardioes(status);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_usuario ON logs_punicoes(id_usuario);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_tipo ON logs_punicoes(tipo_punicao);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_data ON logs_punicoes(data_punicao);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_ativa ON logs_punicoes(ativa);
CREATE INDEX IF NOT EXISTS idx_logs_punicoes_servidor ON logs_punicoes(id_servidor);

-- Comentários nas tabelas
COMMENT ON TABLE usuarios IS 'Tabela de usuários do sistema Guardião BETA';
COMMENT ON TABLE denuncias IS 'Tabela de denúncias reportadas pelos usuários';
COMMENT ON TABLE mensagens_capturadas IS 'Mensagens capturadas durante as denúncias';
COMMENT ON TABLE votos_guardioes IS 'Votos dos guardiões nas denúncias';
COMMENT ON TABLE servidores_premium IS 'Servidores com assinatura premium';
COMMENT ON TABLE configuracoes_servidor IS 'Configurações personalizadas dos servidores premium';
COMMENT ON TABLE mensagens_guardioes IS 'Rastreamento de mensagens enviadas aos guardiões';

-- Dados iniciais (opcional)
-- Você pode adicionar dados de teste aqui se necessário

-- Verificação das tabelas criadas
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN ('usuarios', 'denuncias', 'mensagens_capturadas', 'votos_guardioes', 'servidores_premium', 'configuracoes_servidor', 'mensagens_guardioes')
ORDER BY tablename;
