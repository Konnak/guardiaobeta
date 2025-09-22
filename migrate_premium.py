#!/usr/bin/env python3
"""
Script para migrar campos da tabela servidores_premium
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

async def run_migration():
    """Executa a migração da tabela servidores_premium"""
    
    # Configurações do banco
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'guardiao_beta'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }
    
    print("🔄 Iniciando migração da tabela servidores_premium...")
    print(f"📊 Conectando ao banco: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    try:
        # Conectar ao banco
        conn = await asyncpg.connect(**db_config)
        
        # Ler o arquivo de migração
        with open('database/migrate_premium_fields.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print("📝 Executando migração...")
        
        # Executar a migração
        await conn.execute(migration_sql)
        
        print("✅ Migração executada com sucesso!")
        
        # Verificar as colunas da tabela
        print("\n📋 Verificando estrutura da tabela servidores_premium:")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'servidores_premium' 
                AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        
        for column in columns:
            nullable = "NULL" if column['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {column['column_default']}" if column['column_default'] else ""
            print(f"  - {column['column_name']}: {column['data_type']} {nullable}{default}")
        
        # Fechar conexão
        await conn.close()
        
        print("\n🎉 Migração concluída com sucesso!")
        print("💡 Agora você pode testar a seleção de servidor premium.")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
