#!/usr/bin/env python3
"""
Script para executar migração do canal de log
Execute este script no servidor para aplicar a correção da constraint UNIQUE
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

async def run_migration():
    """Executa a migração para corrigir constraint UNIQUE"""
    try:
        # Conecta ao banco de dados
        conn = await asyncpg.connect(
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB')
        )
        
        print("✅ Conectado ao banco de dados PostgreSQL")
        
        # Lê o script de migração
        with open('migrate_canal_log_fix.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print("📄 Executando migração...")
        
        # Executa a migração
        await conn.execute(migration_sql)
        
        print("✅ Migração executada com sucesso!")
        print("🔧 Constraint UNIQUE adicionada em id_servidor da tabela configuracoes_servidor")
        
        # Verifica se a constraint foi criada
        result = await conn.fetch("""
            SELECT constraint_name, constraint_type 
            FROM information_schema.table_constraints 
            WHERE table_name = 'configuracoes_servidor' 
            AND constraint_type = 'UNIQUE'
        """)
        
        print("\n📋 Constraints UNIQUE encontradas:")
        for row in result:
            print(f"  - {row['constraint_name']}: {row['constraint_type']}")
        
        await conn.close()
        print("\n✅ Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🛡️ Sistema Guardião BETA - Migração Canal de Log")
    print("=" * 50)
    
    success = asyncio.run(run_migration())
    
    if success:
        print("\n🎉 Migração concluída! O sistema de canal de log agora funcionará corretamente.")
    else:
        print("\n💥 Falha na migração. Verifique os logs acima.")
