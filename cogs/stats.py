"""
Cog de Estatísticas - Sistema Guardião BETA
Implementa o comando /stats para exibir informações do usuário
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime
from database.connection import db_manager, get_user_by_discord_id
from utils.experience_system import (
    get_experience_rank, 
    get_rank_emoji, 
    format_experience_display,
    get_experience_progress
)

# Configuração de logging
logger = logging.getLogger(__name__)


class StatsCog(commands.Cog):
    """Cog para comandos de estatísticas"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(
        name="stats",
        description="Exibe suas estatísticas no Sistema Guardião BETA"
    )
    async def stats(self, ctx: commands.Context):
        """
        Comando de estatísticas - Apenas em DM
        
        Exibe informações completas do usuário incluindo:
        - Dados pessoais
        - Pontos e experiência
        - Status de serviço
        - Estatísticas de moderação
        """
        try:
            # Verifica se o banco de dados está disponível
            if not db_manager.pool:
                await db_manager.initialize_pool()
            
            # Busca os dados do usuário
            user_data = await get_user_by_discord_id(ctx.author.id)
            
            if not user_data:
                embed = discord.Embed(
                    title="❌ Usuário Não Cadastrado",
                    description="Você precisa se cadastrar primeiro usando `/cadastro`!",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            # Busca estatísticas adicionais
            stats_data = await self._get_user_stats(ctx.author.id)
            
            # Cria o embed principal
            embed = discord.Embed(
                title="📊 Suas Estatísticas - Sistema Guardião BETA",
                color=0x00ff00 if user_data['em_servico'] else 0x0099ff
            )
            
            # Avatar do usuário
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            
            # Informações pessoais
            embed.add_field(
                name="👤 Informações Pessoais",
                value=f"**Nome:** {user_data['nome_completo']}\n"
                      f"**Idade:** {user_data['idade']} anos\n"
                      f"**Email:** {user_data['email']}\n"
                      f"**Telefone:** {user_data['telefone']}",
                inline=True
            )
            
            # Status e categoria
            status_emoji = "🟢" if user_data['em_servico'] else "🔴"
            status_text = "Em Serviço" if user_data['em_servico'] else "Fora de Serviço"
            
            embed.add_field(
                name="🎖️ Status e Categoria",
                value=f"**Categoria:** {user_data['categoria']}\n"
                      f"**Status:** {status_emoji} {status_text}\n"
                      f"**Membro desde:** {user_data['data_criacao_registro'].strftime('%d/%m/%Y')}",
                inline=True
            )
            
            # Sistema de experiência
            rank = get_experience_rank(user_data['experiencia'])
            emoji = get_rank_emoji(rank)
            experience_display = format_experience_display(user_data['experiencia'])
            
            embed.add_field(
                name="⭐ Sistema de Experiência",
                value=f"**Rank Atual:** {emoji} {rank}\n"
                      f"**Experiência:** {user_data['experiencia']} XP\n"
                      f"**Progresso:** {experience_display}",
                inline=False
            )
            
            # Pontos e estatísticas
            embed.add_field(
                name="🏆 Pontos e Estatísticas",
                value=f"**Pontos de Serviço:** {user_data['pontos']}\n"
                      f"**Denúncias Atendidas:** {stats_data['denuncias_atendidas']}\n"
                      f"**Votos Realizados:** {stats_data['votos_realizados']}\n"
                      f"**Último Turno:** {self._format_last_turn(user_data['ultimo_turno_inicio'])}",
                inline=True
            )
            
            # Cooldowns
            cooldowns = self._format_cooldowns(user_data)
            if cooldowns:
                embed.add_field(
                    name="⏰ Cooldowns",
                    value=cooldowns,
                    inline=True
                )
            
            # Footer com informações do sistema
            embed.set_footer(
                text=f"Sistema Guardião BETA • ID: {ctx.author.id}",
                icon_url=self.bot.user.display_avatar.url
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erro no comando stats para usuário {ctx.author.id}: {e}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    async def _get_user_stats(self, user_id: int) -> dict:
        """Busca estatísticas adicionais do usuário"""
        try:
            # Conta denúncias atendidas
            denuncias_query = """
                SELECT COUNT(*) as total
                FROM votos_guardioes 
                WHERE id_guardiao = $1
            """
            denuncias_atendidas = await db_manager.execute_scalar(denuncias_query, user_id)
            
            # Conta votos realizados
            votos_query = """
                SELECT COUNT(*) as total
                FROM votos_guardioes 
                WHERE id_guardiao = $1
            """
            votos_realizados = await db_manager.execute_scalar(votos_query, user_id)
            
            return {
                'denuncias_atendidas': denuncias_atendidas or 0,
                'votos_realizados': votos_realizados or 0
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas do usuário {user_id}: {e}")
            return {
                'denuncias_atendidas': 0,
                'votos_realizados': 0
            }
    
    def _format_last_turn(self, ultimo_turno_inicio) -> str:
        """Formata a informação do último turno"""
        if not ultimo_turno_inicio:
            return "Nunca"
        
        now = datetime.utcnow()
        diff = now - ultimo_turno_inicio
        
        if diff.days > 0:
            return f"{diff.days} dias atrás"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} horas atrás"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutos atrás"
        else:
            return "Agora mesmo"
    
    def _format_cooldowns(self, user_data: dict) -> str:
        """Formata as informações de cooldown"""
        cooldowns = []
        now = datetime.utcnow()
        
        # Cooldown da prova
        if user_data['cooldown_prova'] and user_data['cooldown_prova'] > now:
            diff = user_data['cooldown_prova'] - now
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            cooldowns.append(f"**Prova:** {hours}h {minutes}m")
        
        # Cooldown de dispensa
        if user_data['cooldown_dispensa'] and user_data['cooldown_dispensa'] > now:
            diff = user_data['cooldown_dispensa'] - now
            minutes = diff.seconds // 60
            cooldowns.append(f"**Dispensa:** {minutes}m")
        
        # Cooldown de inatividade
        if user_data['cooldown_inativo'] and user_data['cooldown_inativo'] > now:
            diff = user_data['cooldown_inativo'] - now
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            cooldowns.append(f"**Inativo:** {hours}h {minutes}m")
        
        return "\n".join(cooldowns) if cooldowns else "Nenhum cooldown ativo"
    
    @stats.error
    async def stats_error(self, ctx: discord.ApplicationContext, error):
        """Tratamento de erros do comando stats"""
        if isinstance(error, commands.PrivateMessageOnly):
            embed = discord.Embed(
                title="⚠️ Comando Restrito",
                description="Este comando só pode ser usado em mensagens privadas (DM)!",
                color=0xffa500
            )
            embed.add_field(
                name="Como usar:",
                value="1. Abra uma conversa privada comigo\n"
                      "2. Use o comando `/stats`",
                inline=False
            )
            await ctx.send(embed=embed)
        else:
            logger.error(f"Erro não tratado no comando stats: {error}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            await ctx.send(embed=embed)


def setup(bot):
    """Função para carregar o cog"""
    bot.add_cog(StatsCog(bot))
