#!/usr/bin/env python3
"""
Script simples para resetar cooldown - Execute no servidor Discloud
"""

import asyncio
import asyncpg

async def reset_cooldown():
    # Conecta usando as variáveis de ambiente do Discloud
    conn = await asyncpg.connect(
        host="guardiaobeta",  # Host do banco no Discloud
        user="userguardiaobeta",  # Usuário do banco
        password="senha_do_banco",  # Substitua pela senha real
        database="guardiaobeta"  # Nome da base
    )
    
    # Remove cooldown para seu usuário
    await conn.execute("UPDATE usuarios SET cooldown_prova = NULL WHERE id_discord = 1369940071246991380")
    
    print("✅ Cooldown removido com sucesso!")
    await conn.close()

# Execute
asyncio.run(reset_cooldown())
