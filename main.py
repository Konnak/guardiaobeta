"""
Sistema Guardião BETA - Arquivo Principal
Integra o bot Discord com a aplicação web Flask
"""

import asyncio
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

# Discord Bot
import discord
from discord.ext import commands

# Web Application
from flask import Flask

# Sistema Guardião BETA
from config import (
    DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_TOKEN,
    POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT,
    WEB_PORT, FLASK_SECRET_KEY, BOT_PREFIX,
    GUARDIAO_MIN_ACCOUNT_AGE_MONTHS, TURN_POINTS_PER_HOUR,
    MAX_GUARDIANS_PER_REPORT, REQUIRED_VOTES_FOR_DECISION,
    VOTE_TIMEOUT_MINUTES, DISPENSE_COOLDOWN_MINUTES,
    INACTIVE_PENALTY_HOURS, PROVA_COOLDOWN_HOURS, PUNISHMENT_RULES
)
from database.connection import db_manager
from web.auth import setup_auth
from web.routes import setup_routes

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('guardiao.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Configuração do bot Discord
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.dm_messages = True
intents.members = True

# Criação do bot
bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# Criação da aplicação web
app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY or 'guardiao-beta-secret-key'

# Variável global para compartilhar o bot com a web app
web_app = app


class GuardiaoBot:
    """Classe principal do Sistema Guardião BETA"""
    
    def __init__(self):
        self.bot = bot
        self.web_app = app
        self.db_manager = db_manager
        self.start_time = datetime.now(timezone.utc)
        self.stats = {
            'total_commands': 0,
            'total_reports': 0,
            'total_punishments': 0,
            'uptime': 0
        }
    
    async def setup_bot(self):
        """Configura o bot Discord"""
        try:
            # Carrega todos os cogs
            await self.load_cogs()
            
            # Configura eventos
            self.setup_events()
            
            logger.info("Bot Discord configurado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao configurar bot: {e}")
            raise
    
    async def load_cogs(self):
        """Carrega todos os cogs do sistema"""
        cogs_to_load = [
            'cogs.cadastro',
            'cogs.guardiao', 
            'cogs.stats',
            'cogs.moderacao'
        ]
        
        for cog in cogs_to_load:
            try:
                await self.bot.load_extension(cog)
                logger.info(f"Cog {cog} carregado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao carregar cog {cog}: {e}")
                raise
    
    def setup_events(self):
        """Configura eventos do bot"""
        
        @self.bot.event
        async def on_ready():
            """Evento quando o bot está pronto"""
            logger.info(f'Bot logado como {self.bot.user} (ID: {self.bot.user.id})')
            logger.info(f'Conectado a {len(self.bot.guilds)} servidores')
            
            # Atualiza status do bot
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.bot.guilds)} servidores | Sistema Guardião BETA"
            )
            await self.bot.change_presence(activity=activity)
            
            # Inicializa banco de dados
            await self.initialize_database()
            
            # Inicia background tasks
            self.start_background_tasks()
        
        @self.bot.event
        async def on_guild_join(guild):
            """Evento quando o bot entra em um servidor"""
            logger.info(f'Bot adicionado ao servidor: {guild.name} (ID: {guild.id})')
            
            # Envia mensagem de boas-vindas
            try:
                # Procura por um canal de texto
                channel = None
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        break
                
                if channel:
                    embed = discord.Embed(
                        title="🛡️ Sistema Guardião BETA",
                        description="Obrigado por me adicionar ao seu servidor!",
                        color=0x00ff00
                    )
                    embed.add_field(
                        name="📋 Primeiros Passos",
                        value="1. Use `/cadastro` para se registrar\n"
                              "2. Use `/formguardiao` para se tornar um Guardião\n"
                              "3. Use `/report` para denunciar violações",
                        inline=False
                    )
                    embed.add_field(
                        name="🌐 Painel Web",
                        value="Acesse nosso painel web para configurações avançadas:\n"
                              "https://guardiaobeta.vercel.app",
                        inline=False
                    )
                    embed.set_footer(text="Sistema Guardião BETA - Moderação Comunitária")
                    
                    await channel.send(embed=embed)
                    
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem de boas-vindas: {e}")
        
        @self.bot.event
        async def on_guild_remove(guild):
            """Evento quando o bot sai de um servidor"""
            logger.info(f'Bot removido do servidor: {guild.name} (ID: {guild.id})')
        
        @self.bot.event
        async def on_command_error(ctx, error):
            """Tratamento de erros de comandos"""
            if isinstance(error, commands.CommandNotFound):
                return  # Ignora comandos não encontrados
            
            elif isinstance(error, commands.MissingPermissions):
                embed = discord.Embed(
                    title="❌ Permissão Negada",
                    description="Você não tem permissão para usar este comando.",
                    color=0xff0000
                )
                await ctx.send(embed=embed, ephemeral=True)
            
            elif isinstance(error, commands.MissingRequiredArgument):
                embed = discord.Embed(
                    title="❌ Argumento Faltando",
                    description=f"Você precisa fornecer o argumento: `{error.param.name}`",
                    color=0xff0000
                )
                await ctx.send(embed=embed, ephemeral=True)
            
            elif isinstance(error, commands.BadArgument):
                embed = discord.Embed(
                    title="❌ Argumento Inválido",
                    description="O argumento fornecido é inválido.",
                    color=0xff0000
                )
                await ctx.send(embed=embed, ephemeral=True)
            
            elif isinstance(error, commands.CommandOnCooldown):
                embed = discord.Embed(
                    title="⏰ Comando em Cooldown",
                    description=f"Você pode usar este comando novamente em {error.retry_after:.1f} segundos.",
                    color=0xffa500
                )
                await ctx.send(embed=embed, ephemeral=True)
            
            else:
                # Erro não tratado
                logger.error(f"Erro não tratado no comando {ctx.command}: {error}")
                embed = discord.Embed(
                    title="❌ Erro Interno",
                    description="Ocorreu um erro interno. Tente novamente mais tarde.",
                    color=0xff0000
                )
                await ctx.send(embed=embed, ephemeral=True)
    
    async def initialize_database(self):
        """Inicializa o banco de dados"""
        try:
            await self.db_manager.initialize_pool()
            logger.info("Banco de dados inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
            raise
    
    def start_background_tasks(self):
        """Inicia tarefas em background"""
        # As tasks são iniciadas automaticamente pelos cogs
        logger.info("Background tasks iniciadas")
    
    def setup_web_app(self):
        """Configura a aplicação web Flask"""
        try:
            # Configura autenticação
            setup_auth(self.web_app)
            
            # Configura rotas
            setup_routes(self.web_app)
            
            # Adiciona rota para status do bot
            @self.web_app.route('/api/bot/status')
            def bot_status():
                return {
                    'status': 'online' if self.bot.is_ready() else 'offline',
                    'guilds': len(self.bot.guilds),
                    'users': len(self.bot.users),
                    'uptime': str(datetime.now(timezone.utc) - self.start_time),
                    'stats': self.stats
                }
            
            # Adiciona rota para estatísticas gerais
            @self.web_app.route('/api/stats')
            async def general_stats():
                try:
                    if not self.db_manager.pool:
                        return {'error': 'Database not initialized'}, 500
                    
                    stats_query = """
                        SELECT 
                            (SELECT COUNT(*) FROM usuarios) as total_usuarios,
                            (SELECT COUNT(*) FROM usuarios WHERE categoria = 'Guardião') as total_guardioes,
                            (SELECT COUNT(*) FROM denuncias) as total_denuncias,
                            (SELECT COUNT(DISTINCT id_servidor) FROM denuncias) as total_servidores
                    """
                    stats = self.db_manager.execute_query(stats_query)
                    
                    return stats[0] if stats else {}
                    
                except Exception as e:
                    logger.error(f"Erro ao buscar estatísticas: {e}")
                    return {'error': 'Internal server error'}, 500
            
            logger.info("Aplicação web configurada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao configurar aplicação web: {e}")
            raise
    
    def run_web_app(self):
        """Executa a aplicação web em thread separada"""
        try:
            port = int(WEB_PORT)
            host = '0.0.0.0'  # Para funcionar na Discloud
            
            logger.info(f"Iniciando servidor web na porta {port}")
            self.web_app.run(host=host, port=port, debug=False, threaded=True)
            
        except Exception as e:
            logger.error(f"Erro ao executar aplicação web: {e}")
            raise
    
    async def run(self):
        """Executa o sistema completo"""
        try:
            # Configura aplicação web
            self.setup_web_app()
            
            # Inicia aplicação web em thread separada
            web_thread = threading.Thread(target=self.run_web_app, daemon=True)
            web_thread.start()
            
            # Aguarda um pouco para a web app inicializar
            await asyncio.sleep(2)
            
            # Configura bot
            await self.setup_bot()
            
            # Inicia bot Discord
            logger.info("Iniciando Sistema Guardião BETA...")
            await self.bot.start(DISCORD_TOKEN)
            
        except KeyboardInterrupt:
            logger.info("Sistema interrompido pelo usuário")
        except Exception as e:
            logger.error(f"Erro fatal no sistema: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Limpa recursos antes de encerrar"""
        try:
            logger.info("Encerrando Sistema Guardião BETA...")
            
            # Fecha conexões do banco
            await self.db_manager.close_pool()
            
            # Fecha sessão HTTP (se existir)
            pass
            
            logger.info("Sistema encerrado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro durante limpeza: {e}")


# Função para executar testes
async def run_tests():
    """Executa testes básicos do sistema"""
    logger.info("Executando testes do sistema...")
    
    try:
        # Testa conexão com banco
        await db_manager.initialize_pool()
        logger.info("✅ Conexão com banco de dados: OK")
        
        # Testa sistema de experiência
        from utils.experience_system import test_experience_system
        test_experience_system()
        logger.info("✅ Sistema de experiência: OK")
        
        # Testa configurações
        assert DISCORD_TOKEN, "DISCORD_TOKEN não configurado"
        assert DISCORD_CLIENT_ID, "DISCORD_CLIENT_ID não configurado"
        logger.info("✅ Configurações: OK")
        
        logger.info("Todos os testes passaram com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Teste falhou: {e}")
        return False


# Função principal
async def main():
    """Função principal do sistema"""
    logger.info("=" * 50)
    logger.info("🛡️  SISTEMA GUARDIÃO BETA - INICIANDO")
    logger.info("=" * 50)
    
    # Verifica argumentos de linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            # Modo teste
            success = await run_tests()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == '--web-only':
            # Modo apenas web
            guardiao = GuardiaoBot()
            guardiao.setup_web_app()
            guardiao.run_web_app()
            return
        elif sys.argv[1] == '--help':
            print("Sistema Guardião BETA - Opções:")
            print("  python main.py          - Executa o sistema completo")
            print("  python main.py --test   - Executa testes")
            print("  python main.py --web-only - Executa apenas a aplicação web")
            print("  python main.py --help   - Mostra esta ajuda")
            sys.exit(0)
    
    # Executa sistema completo
    guardiao = GuardiaoBot()
    await guardiao.run()


# Execução
if __name__ == "__main__":
    try:
        # Verifica se está rodando no Windows
        if os.name == 'nt':
            # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Executa o sistema
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Sistema interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)
