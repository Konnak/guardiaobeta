#!/usr/bin/env python3
"""
Script de migração para adicionar a tabela mensagens_guardioes
Execute com: python migrate.py
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime

# SQL da migração
MIGRATION_SQL = """
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

-- Comentários
COMMENT ON TABLE mensagens_guardioes IS 'Rastreamento de mensagens enviadas aos guardiões';
"""

async def run_migration():
    """Executa a migração da tabela mensagens_guardioes"""
    try:
        # Pega a URL do banco das variáveis de ambiente
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ Erro: Variável DATABASE_URL não encontrada!")
            print("Certifique-se de que as variáveis de ambiente estão configuradas.")
            return False
        
        print("🔄 Conectando ao banco de dados...")
        
        # Conecta ao banco
        conn = await asyncpg.connect(database_url)
        
        print("✅ Conectado com sucesso!")
        print("🔄 Executando migração...")
        
        # Executa a migração
        await conn.execute(MIGRATION_SQL)
        
        print("✅ Migração executada com sucesso!")
        
        # Verifica se a tabela foi criada
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'mensagens_guardioes'
            )
        """)
        
        if result:
            print("✅ Tabela 'mensagens_guardioes' criada e verificada!")
            
            # Conta registros existentes (deve ser 0 em uma nova tabela)
            count = await conn.fetchval("SELECT COUNT(*) FROM mensagens_guardioes")
            print(f"📊 Registros na tabela: {count}")
            
        else:
            print("❌ Erro: Tabela não foi criada corretamente!")
            return False
        
        # Fecha conexão
        await conn.close()
        print("🔒 Conexão fechada.")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        return False

def main():
    """Função principal"""
    print("=" * 50)
    print("🛡️  MIGRAÇÃO SISTEMA GUARDIÃO BETA")
    print("   Adicionando tabela mensagens_guardioes")
    print("=" * 50)
    print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Executa a migração
    success = asyncio.run(run_migration())
    
    print()
    if success:
        print("🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("   O sistema agora pode usar a tabela mensagens_guardioes")
        print("   para melhor rastreamento e performance.")
    else:
        print("💥 MIGRAÇÃO FALHOU!")
        print("   O sistema continuará funcionando com cache temporário.")
    
    print("=" * 50)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
