import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

async def run_migration():
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    conn = None
    try:
        logger.info(f"Conectando ao banco de dados: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Conexão com o banco de dados estabelecida.")

        # Lê o script SQL de migração
        script_dir = os.path.dirname(__file__)
        migration_script_path = os.path.join(script_dir, 'migrate_logs_punicoes.sql')
        
        with open(migration_script_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()

        logger.info(f"Executando script de migração: {migration_script_path}")
        await conn.execute(migration_sql)
        logger.info("Script de migração executado com sucesso!")

        # Verifica se a tabela foi criada
        check_query = """
            SELECT 
                schemaname,
                tablename,
                tableowner
            FROM pg_tables 
            WHERE schemaname = 'public' 
                AND tablename = 'logs_punicoes';
        """
        tables = await conn.fetch(check_query)
        
        if tables:
            logger.info("✅ Tabela logs_punicoes criada com sucesso!")
            for table in tables:
                logger.info(f"  - Schema: {table['schemaname']}")
                logger.info(f"  - Tabela: {table['tablename']}")
                logger.info(f"  - Owner: {table['tableowner']}")
        else:
            logger.error("❌ Tabela logs_punicoes não foi encontrada!")

        # Verifica as colunas da tabela
        columns_query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'logs_punicoes' 
            ORDER BY ordinal_position;
        """
        columns = await conn.fetch(columns_query)
        
        if columns:
            logger.info("📋 Colunas da tabela logs_punicoes:")
            for col in columns:
                logger.info(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")

    except Exception as e:
        logger.error(f"Erro durante a migração: {e}")
    finally:
        if conn:
            await conn.close()
            logger.info("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    asyncio.run(run_migration())
