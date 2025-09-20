#!/usr/bin/env python3
"""
Script para remover cooldown da prova do usuário
Execute no servidor Discloud: python3 remove_cooldown.py
"""

import asyncio
import asyncpg
import os
from datetime import datetime

# ID do usuário para remover cooldown
USER_ID = 1369940071246991380

async def remove_cooldown():
    """Remove o cooldown da prova para o usuário especificado"""
    try:
        # Conecta ao banco de dados
        conn = await asyncpg.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB', 'guardiaobeta')
        )
        
        print(f"🔗 Conectado ao banco de dados PostgreSQL")
        
        # Verifica o cooldown atual
        current_cooldown = await conn.fetchval(
            "SELECT cooldown_prova FROM usuarios WHERE id_discord = $1", 
            USER_ID
        )
        
        if current_cooldown:
            print(f"⏰ Cooldown atual: {current_cooldown}")
        else:
            print("✅ Usuário não possui cooldown ativo")
            return
        
        # Remove o cooldown
        await conn.execute(
            "UPDATE usuarios SET cooldown_prova = NULL WHERE id_discord = $1", 
            USER_ID
        )
        
        print(f"✅ Cooldown removido com sucesso para usuário {USER_ID}")
        
        # Verifica se foi removido
        new_cooldown = await conn.fetchval(
            "SELECT cooldown_prova FROM usuarios WHERE id_discord = $1", 
            USER_ID
        )
        
        if new_cooldown is None:
            print("✅ Verificação: Cooldown removido com sucesso!")
        else:
            print(f"❌ Erro: Cooldown ainda ativo: {new_cooldown}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        if 'conn' in locals():
            await conn.close()
            print("🔌 Conexão com banco fechada")

if __name__ == "__main__":
    print("🛡️ Sistema Guardião BETA - Remover Cooldown")
    print("=" * 50)
    asyncio.run(remove_cooldown())
