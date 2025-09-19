"""
Conexão com o Banco de Dados PostgreSQL - Sistema Guardião BETA
Implementa pool de conexões assíncronas para o ambiente de produção (Discloud)
"""

import asyncio
import asyncpg
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from config import DATABASE_URL, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gerenciador de conexões com o banco de dados PostgreSQL"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_url = DATABASE_URL
        
    async def initialize_pool(self, min_connections: int = 5, max_connections: int = 20):
        """
        Inicializa o pool de conexões
        
        Args:
            min_connections: Número mínimo de conexões no pool
            max_connections: Número máximo de conexões no pool
        """
        try:
            logger.info("Inicializando pool de conexões PostgreSQL...")
            
            # Configurações do pool para o ambiente de produção
            self.pool = await asyncpg.create_pool(
                host=POSTGRES_HOST,
                port=int(POSTGRES_PORT),
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                min_size=min_connections,
                max_size=max_connections,
                command_timeout=60,  # Timeout de 60 segundos para comandos
                server_settings={
                    'application_name': 'guardiao_beta_bot',
                    'timezone': 'UTC'
                }
            )
            
            logger.info(f"Pool de conexões criado com sucesso! ({min_connections}-{max_connections} conexões)")
            
            # Testa a conexão
            await self.test_connection()
            
        except Exception as e:
            logger.error(f"Erro ao inicializar pool de conexões: {e}")
            raise
    
    async def test_connection(self):
        """Testa a conexão com o banco de dados"""
        try:
            async with self.pool.acquire() as connection:
                result = await connection.fetchval("SELECT 1")
                logger.info("Conexão com PostgreSQL testada com sucesso!")
                return result == 1
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            raise
    
    async def close_pool(self):
        """Fecha o pool de conexões"""
        if self.pool:
            await self.pool.close()
            logger.info("Pool de conexões fechado.")
    
    async def create_tables(self):
        """Cria todas as tabelas necessárias no banco de dados"""
        try:
            # Verifica se as tabelas já existem
            async with self.get_connection() as conn:
                check_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'usuarios'
                    );
                """
                tables_exist = await conn.fetchval(check_query)
                
                if tables_exist:
                    logger.info("Tabelas já existem, pulando criação")
                    return True
            
            # Lê o arquivo SQL de inicialização
            import os
            sql_file = os.path.join(os.path.dirname(__file__), 'init_schema.sql')
            
            if not os.path.exists(sql_file):
                logger.error(f"Arquivo SQL não encontrado: {sql_file}")
                return False
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Executa o SQL
            async with self.get_connection() as conn:
                await conn.execute(sql_content)
            
            logger.info("Tabelas criadas com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {e}")
            return False
    
    def create_tables_sync(self):
        """Versão síncrona para criar tabelas - CONEXÃO ISOLADA"""
        import asyncio
        import asyncpg
        import os
        
        def run_query():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def execute():
                    # Lê o arquivo SQL
                    sql_file = os.path.join(os.path.dirname(__file__), 'init_schema.sql')
                    if not os.path.exists(sql_file):
                        logger.error(f"Arquivo SQL não encontrado: {sql_file}")
                        return False
                    
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                    
                    # Configurações do banco
                    db_config = {
                        'host': os.getenv('POSTGRES_HOST'),
                        'port': int(os.getenv('POSTGRES_PORT', 5432)),
                        'user': os.getenv('POSTGRES_USER'),
                        'password': os.getenv('POSTGRES_PASSWORD'),
                        'database': os.getenv('POSTGRES_DB')
                    }
                    
                    # Cria conexão direta independente
                    conn = await asyncpg.connect(**db_config)
                    try:
                        await conn.execute(sql_content)
                        return True
                    finally:
                        await conn.close()
                
                result = loop.run_until_complete(execute())
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Erro na criação síncrona isolada de tabelas: {e}")
                return False
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_query)
            return future.result(timeout=60)
    
    # Versões síncronas das funções para uso em Flask
    def execute_query_sync(self, query: str, *args) -> List[Dict[str, Any]]:
        """Versão síncrona de execute_query para uso em Flask - CONEXÃO ISOLADA"""
        import asyncio
        import asyncpg
        import os
        
        def run_query():
            try:
                # Cria um loop completamente isolado
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def execute():
                    # Configurações do banco
                    db_config = {
                        'host': os.getenv('POSTGRES_HOST'),
                        'port': int(os.getenv('POSTGRES_PORT', 5432)),
                        'user': os.getenv('POSTGRES_USER'),
                        'password': os.getenv('POSTGRES_PASSWORD'),
                        'database': os.getenv('POSTGRES_DB')
                    }
                    
                    # Cria conexão direta independente
                    conn = await asyncpg.connect(**db_config)
                    try:
                        rows = await conn.fetch(query, *args)
                        return [dict(row) for row in rows]
                    finally:
                        await conn.close()
                
                result = loop.run_until_complete(execute())
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Erro na execução síncrona isolada: {e}")
                return []
        
        # Executa em thread separada
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_query)
            return future.result(timeout=30)
    
    def execute_one_sync(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Versão síncrona de execute_one para uso em Flask - CONEXÃO ISOLADA"""
        import asyncio
        import asyncpg
        import os
        
        def run_query():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def execute():
                    db_config = {
                        'host': os.getenv('POSTGRES_HOST'),
                        'port': int(os.getenv('POSTGRES_PORT', 5432)),
                        'user': os.getenv('POSTGRES_USER'),
                        'password': os.getenv('POSTGRES_PASSWORD'),
                        'database': os.getenv('POSTGRES_DB')
                    }
                    
                    conn = await asyncpg.connect(**db_config)
                    try:
                        row = await conn.fetchrow(query, *args)
                        return dict(row) if row else None
                    finally:
                        await conn.close()
                
                result = loop.run_until_complete(execute())
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Erro na execução síncrona isolada: {e}")
                return None
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_query)
            return future.result(timeout=30)
    
    def execute_scalar_sync(self, query: str, *args) -> Any:
        """Versão síncrona de execute_scalar para uso em Flask - CONEXÃO ISOLADA"""
        import asyncio
        import asyncpg
        import os
        
        def run_query():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def execute():
                    db_config = {
                        'host': os.getenv('POSTGRES_HOST'),
                        'port': int(os.getenv('POSTGRES_PORT', 5432)),
                        'user': os.getenv('POSTGRES_USER'),
                        'password': os.getenv('POSTGRES_PASSWORD'),
                        'database': os.getenv('POSTGRES_DB')
                    }
                    
                    conn = await asyncpg.connect(**db_config)
                    try:
                        return await conn.fetchval(query, *args)
                    finally:
                        await conn.close()
                
                result = loop.run_until_complete(execute())
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Erro na execução síncrona isolada: {e}")
                return None
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_query)
            return future.result(timeout=30)
    
    def execute_command_sync(self, command: str, *args) -> str:
        """Versão síncrona de execute_command para uso em Flask - CONEXÃO ISOLADA"""
        import asyncio
        import asyncpg
        import os
        
        def run_query():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def execute():
                    db_config = {
                        'host': os.getenv('POSTGRES_HOST'),
                        'port': int(os.getenv('POSTGRES_PORT', 5432)),
                        'user': os.getenv('POSTGRES_USER'),
                        'password': os.getenv('POSTGRES_PASSWORD'),
                        'database': os.getenv('POSTGRES_DB')
                    }
                    
                    conn = await asyncpg.connect(**db_config)
                    try:
                        await conn.execute(command, *args)
                        return "OK"
                    finally:
                        await conn.close()
                
                result = loop.run_until_complete(execute())
                loop.close()
                return result
            except Exception as e:
                logger.error(f"Erro na execução síncrona isolada: {e}")
                return "ERROR"
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_query)
            return future.result(timeout=30)
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Context manager para obter uma conexão do pool
        
        Usage:
            async with db_manager.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
        """
        if not self.pool:
            raise RuntimeError("Pool de conexões não foi inicializado. Chame initialize_pool() primeiro.")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Executa uma query SELECT e retorna os resultados
        
        Args:
            query: Query SQL
            *args: Parâmetros da query
            
        Returns:
            Lista de dicionários com os resultados
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Executa uma query SELECT e retorna apenas o primeiro resultado
        
        Args:
            query: Query SQL
            *args: Parâmetros da query
            
        Returns:
            Dicionário com o resultado ou None
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def execute_scalar(self, query: str, *args) -> Any:
        """
        Executa uma query e retorna um valor escalar
        
        Args:
            query: Query SQL
            *args: Parâmetros da query
            
        Returns:
            Valor escalar
        """
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute_command(self, command: str, *args) -> str:
        """
        Executa um comando SQL (INSERT, UPDATE, DELETE)
        
        Args:
            command: Comando SQL
            *args: Parâmetros do comando
            
        Returns:
            Status do comando
        """
        async with self.get_connection() as conn:
            result = await conn.execute(command, *args)
            return result
    
    async def execute_transaction(self, commands: List[tuple]) -> bool:
        """
        Executa múltiplos comandos em uma transação
        
        Args:
            commands: Lista de tuplas (query, args)
            
        Returns:
            True se a transação foi bem-sucedida
        """
        async with self.get_connection() as conn:
            async with conn.transaction():
                for command, args in commands:
                    await conn.execute(command, *args)
            return True


# Instância global do gerenciador de banco de dados
db_manager = DatabaseManager()


# Funções utilitárias para facilitar o uso
async def init_database():
    """Inicializa a conexão com o banco de dados"""
    await db_manager.initialize_pool()


async def close_database():
    """Fecha a conexão com o banco de dados"""
    await db_manager.close_pool()


# Decorador para operações de banco de dados
def db_operation(func):
    """
    Decorador para funções que fazem operações no banco de dados
    Garante que o pool esteja inicializado
    """
    async def wrapper(*args, **kwargs):
        if not db_manager.pool:
            await db_manager.initialize_pool()
        return await func(*args, **kwargs)
    return wrapper


# Exemplo de uso das funções utilitárias
async def get_user_by_discord_id(discord_id: int) -> Optional[Dict[str, Any]]:
    """Busca um usuário pelo ID do Discord (versão assíncrona)"""
    query = "SELECT * FROM usuarios WHERE id_discord = $1"
    return await db_manager.execute_one(query, discord_id)

def get_user_by_discord_id_sync(discord_id: int) -> Optional[Dict[str, Any]]:
    """Busca um usuário pelo ID do Discord (versão síncrona)"""
    query = "SELECT * FROM usuarios WHERE id_discord = $1"
    try:
        return db_manager.execute_one_sync(query, discord_id)
    except Exception as e:
        logger.error(f"Erro ao buscar usuário por Discord ID: {e}")
        return None


async def create_user(user_data: Dict[str, Any]) -> bool:
    """Cria um novo usuário no banco de dados"""
    query = """
        INSERT INTO usuarios (id_discord, username, display_name, nome_completo, idade, email, telefone)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (id_discord) DO NOTHING
    """
    try:
        await db_manager.execute_command(
            query,
            user_data['id_discord'],
            user_data['username'],
            user_data['display_name'],
            user_data['nome_completo'],
            user_data['idade'],
            user_data['email'],
            user_data['telefone']
        )
        return True
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        return False


async def update_user_category(discord_id: int, categoria: str) -> bool:
    """Atualiza a categoria de um usuário"""
    query = "UPDATE usuarios SET categoria = $1 WHERE id_discord = $2"
    try:
        await db_manager.execute_command(query, categoria, discord_id)
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar categoria do usuário: {e}")
        return False
