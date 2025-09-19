"""
Cog de Cadastro - Sistema Guardião BETA
Implementa o comando /cadastro com Modal para registro de usuários
"""

import discord
from discord.ext import commands
from discord import ui
import re
import asyncio
import logging
from datetime import datetime
from database.connection import db_manager, create_user, get_user_by_discord_id
from config import DISCORD_CLIENT_ID

# Configuração de logging
logger = logging.getLogger(__name__)


class CadastroModal(ui.Modal, title="Cadastro no Sistema Guardião BETA"):
    """Modal para cadastro de usuários no sistema"""
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    nome_completo = ui.TextInput(
        label="Nome Completo",
        placeholder="Digite seu nome completo...",
        required=True,
        max_length=255
    )
    
    idade = ui.TextInput(
        label="Idade",
        placeholder="Digite sua idade...",
        required=True,
        max_length=3
    )
    
    email = ui.TextInput(
        label="Email",
        placeholder="seu.email@exemplo.com",
        required=True,
        max_length=255
    )
    
    telefone = ui.TextInput(
        label="Telefone (+55 DDD NÚMERO)",
        placeholder="+55 11 99999-9999",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Callback executado quando o modal é enviado"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validação dos dados
            validation_result = await self._validate_data()
            if not validation_result['valid']:
                embed = discord.Embed(
                    title="❌ Erro no Cadastro",
                    description=validation_result['error'],
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verifica se o usuário já existe
            existing_user = get_user_by_discord_id(interaction.user.id)
            if existing_user:
                embed = discord.Embed(
                    title="⚠️ Usuário Já Cadastrado",
                    description="Você já possui um cadastro no sistema Guardião BETA!",
                    color=0xffa500
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verifica se o email já existe
            email_exists = await self._check_email_exists(self.email.value)
            if email_exists:
                embed = discord.Embed(
                    title="❌ Email Já Cadastrado",
                    description="Este email já está sendo usado por outro usuário!",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Cria o usuário no banco de dados
            user_data = {
                'id_discord': interaction.user.id,
                'username': interaction.user.name,
                'display_name': interaction.user.display_name or interaction.user.name,
                'nome_completo': self.nome_completo.value.strip(),
                'idade': int(self.idade.value),
                'email': self.email.value.lower().strip(),
                'telefone': self.telefone.value.strip()
            }
            
            success = await create_user(user_data)
            
            if success:
                embed = discord.Embed(
                    title="✅ Cadastro Realizado com Sucesso!",
                    description="Bem-vindo ao Sistema Guardião BETA!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="📋 Seus Dados",
                    value=f"**Nome:** {user_data['nome_completo']}\n"
                          f"**Idade:** {user_data['idade']} anos\n"
                          f"**Email:** {user_data['email']}\n"
                          f"**Telefone:** {user_data['telefone']}",
                    inline=False
                )
                embed.add_field(
                    name="🎯 Próximos Passos",
                    value="• Use `/stats` para ver suas informações\n"
                          "• Use `/formguardiao` para se tornar um Guardião\n"
                          "• Use `/report` em servidores para denunciar problemas",
                    inline=False
                )
                embed.set_footer(text="Sistema Guardião BETA - Moderação Comunitária")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Log do cadastro
                logger.info(f"Novo usuário cadastrado: {interaction.user.name} ({interaction.user.id})")
                
            else:
                embed = discord.Embed(
                    title="❌ Erro no Cadastro",
                    description="Ocorreu um erro interno. Tente novamente mais tarde.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Erro no cadastro do usuário {interaction.user.id}: {e}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _validate_data(self) -> dict:
        """Valida os dados inseridos no modal"""
        errors = []
        
        # Validação do nome completo
        if len(self.nome_completo.value.strip()) < 2:
            errors.append("Nome completo deve ter pelo menos 2 caracteres")
        
        if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', self.nome_completo.value.strip()):
            errors.append("Nome completo deve conter apenas letras e espaços")
        
        # Validação da idade
        try:
            idade = int(self.idade.value)
            if idade < 13 or idade > 100:
                errors.append("Idade deve estar entre 13 e 100 anos")
        except ValueError:
            errors.append("Idade deve ser um número válido")
        
        # Validação do email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.email.value.strip()):
            errors.append("Email deve ter um formato válido")
        
        # Validação do telefone (formato brasileiro)
        telefone_clean = re.sub(r'[^\d+]', '', self.telefone.value)
        if not re.match(r'^\+55\d{10,11}$', telefone_clean):
            errors.append("Telefone deve estar no formato +55 DDD NÚMERO (ex: +55 11 99999-9999)")
        
        if errors:
            return {'valid': False, 'error': '\n'.join(f"• {error}" for error in errors)}
        
        return {'valid': True}
    
    async def _check_email_exists(self, email: str) -> bool:
        """Verifica se o email já existe no banco de dados"""
        try:
            query = "SELECT id_discord FROM usuarios WHERE email = $1"
            result = db_manager.execute_one(query, email.lower().strip())
            return result is not None
        except Exception as e:
            logger.error(f"Erro ao verificar email existente: {e}")
            return False


class CadastroCog(commands.Cog):
    """Cog para comandos de cadastro"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(
        name="cadastro",
        description="Cadastre-se no Sistema Guardião BETA"
    )
    async def cadastro(self, ctx: commands.Context):
        """
        Comando de cadastro - Apenas em DM
        
        Cria um modal para o usuário preencher seus dados pessoais
        e se registrar no sistema Guardião BETA
        """
        try:
            # Verifica se o banco de dados está disponível
            if not db_manager.pool:
                db_manager.initialize_pool()
            
            # Cria e envia o modal
            modal = CadastroModal(self.bot)
            await ctx.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Erro no comando cadastro: {e}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @cadastro.error
    async def cadastro_error(self, ctx: commands.Context, error):
        """Tratamento de erros do comando cadastro"""
        if isinstance(error, commands.PrivateMessageOnly):
            embed = discord.Embed(
                title="⚠️ Comando Restrito",
                description="Este comando só pode ser usado em mensagens privadas (DM)!",
                color=0xffa500
            )
            embed.add_field(
                name="Como usar:",
                value="1. Abra uma conversa privada comigo\n"
                      "2. Use o comando `/cadastro`\n"
                      "3. Preencha o formulário",
                inline=False
            )
            await ctx.send(embed=embed)
        else:
            logger.error(f"Erro não tratado no comando cadastro: {error}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            await ctx.send(embed=embed)


async def setup(bot):
    """Função para carregar o cog"""
    await bot.add_cog(CadastroCog(bot))
