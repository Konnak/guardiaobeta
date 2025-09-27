#!/usr/bin/env python3
"""
Script de Migração para Sistema de Captcha - Sistema Guardião BETA
Executa a migração do banco de dados para adicionar o sistema de captcha
"""

import asyncio
import logging
import sys
from database.connection import db_manager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_captcha_migration():
    """Executa a migração do sistema de captcha"""
    try:
        logger.info("🚀 Iniciando migração do sistema de captcha...")
        
        # Inicializa o pool de conexões
        if not db_manager.pool:
            await db_manager.initialize_pool()
            logger.info("✅ Pool de conexões inicializado")
        
        # Lê o arquivo de migração
        with open('database/migrate_captcha_system.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Executa a migração
        await db_manager.execute_command(migration_sql)
        logger.info("✅ Migração do sistema de captcha executada com sucesso")
        
        # Verifica se a tabela foi criada
        check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'captchas_guardioes'
            )
        """
        table_exists = await db_manager.execute_scalar(check_query)
        
        if table_exists:
            logger.info("✅ Tabela 'captchas_guardioes' criada com sucesso")
        else:
            logger.error("❌ Tabela 'captchas_guardioes' não foi criada")
            return False
        
        # Verifica se os índices foram criados
        indexes_query = """
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'captchas_guardioes'
        """
        indexes = await db_manager.execute_query(indexes_query)
        
        logger.info(f"✅ {len(indexes)} índices criados para a tabela")
        for index in indexes:
            logger.info(f"  - {index['indexname']}")
        
        logger.info("🎉 Migração do sistema de captcha concluída com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro durante a migração: {e}")
        return False
    
    finally:
        # Fecha o pool de conexões
        if db_manager.pool:
            await db_manager.close_pool()
            logger.info("✅ Pool de conexões fechado")


async def main():
    """Função principal"""
    try:
        success = await run_captcha_migration()
        if success:
            logger.info("✅ Migração concluída com sucesso!")
            sys.exit(0)
        else:
            logger.error("❌ Migração falhou!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
