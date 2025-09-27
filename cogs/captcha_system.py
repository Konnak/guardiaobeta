"""
Sistema de Captcha para Guardiões - Sistema Guardião BETA
Implementa verificação de atividade de guardiões em serviço
"""

import discord
from discord.ext import commands, tasks
from discord import ui, app_commands
import logging
import asyncio
import random
import string
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from database.connection import db_manager
from config import TURN_POINTS_PER_HOUR

# Configuração de logging
logger = logging.getLogger(__name__)

# Configurações do sistema de captcha
CAPTCHA_TIMEOUT_MINUTES = 15
CAPTCHA_CHECK_INTERVAL_MINUTES = 5
CAPTCHA_SERVICE_HOURS = 3  # Envia captcha após 3 horas em serviço
CAPTCHA_PENALTY_PERCENTAGE = 50  # 50% dos pontos são perdidos


class CaptchaView(ui.View):
    """View para responder ao captcha"""
    
    def __init__(self, captcha_id: int, correct_answer: str, timeout: float = 900):  # 15 minutos
        super().__init__(timeout=timeout)
        self.captcha_id = captcha_id
        self.correct_answer = correct_answer
    
    @ui.button(label="Responder Captcha", style=discord.ButtonStyle.primary, emoji="🔐")
    async def respond_captcha(self, interaction: discord.Interaction, button: ui.Button):
        """Abre modal para responder o captcha"""
        modal = CaptchaModal(self.captcha_id, self.correct_answer)
        await interaction.response.send_modal(modal)


class CaptchaModal(ui.Modal, title="🔐 Verificação de Atividade"):
    """Modal para inserir a resposta do captcha"""
    
    def __init__(self, captcha_id: int, correct_answer: str):
        super().__init__()
        self.captcha_id = captcha_id
        self.correct_answer = correct_answer
    
    answer = ui.TextInput(
        label="Digite a resposta do captcha:",
        placeholder="Ex: 42",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Processa a resposta do captcha"""
        try:
            user_answer = self.answer.value.strip().lower()
            correct_answer = self.correct_answer.lower()
            
            if user_answer == correct_answer:
                # Resposta correta
                await self._handle_correct_answer(interaction)
            else:
                # Resposta incorreta
                await self._handle_incorrect_answer(interaction)
                
        except Exception as e:
            logger.error(f"Erro ao processar resposta do captcha: {e}")
            await interaction.response.send_message(
                "❌ Erro ao processar sua resposta. Tente novamente.",
                ephemeral=True
            )
    
    async def _handle_correct_answer(self, interaction: discord.Interaction):
        """Processa resposta correta"""
        try:
            # Atualiza status do captcha
            update_query = """
                UPDATE captchas_guardioes 
                SET status = 'Respondido', data_resposta = CURRENT_TIMESTAMP 
                WHERE id = $1
            """
            await db_manager.execute_command(update_query, self.captcha_id)
            
            # Edita a mensagem original
            embed = discord.Embed(
                title="✅ Captcha Respondido Corretamente!",
                description="Você confirmou que está ativo e em serviço.",
                color=0x00ff00
            )
            embed.add_field(
                name="Status",
                value="✅ Ativo e em serviço",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Tenta editar a mensagem original (se ainda existir)
            try:
                captcha_data = await db_manager.execute_one(
                    "SELECT mensagem_id, canal_id FROM captchas_guardioes WHERE id = $1",
                    self.captcha_id
                )
                
                if captcha_data:
                    channel = interaction.client.get_channel(captcha_data['canal_id'])
                    if channel:
                        message = await channel.fetch_message(captcha_data['mensagem_id'])
                        if message:
                            await message.edit(
                                content="✅ **Captcha respondido com sucesso!**",
                                embed=embed,
                                view=None
                            )
            except Exception as e:
                logger.warning(f"Não foi possível editar mensagem original: {e}")
            
        except Exception as e:
            logger.error(f"Erro ao processar resposta correta: {e}")
            await interaction.response.send_message(
                "❌ Erro ao processar sua resposta. Tente novamente.",
                ephemeral=True
            )
    
    async def _handle_incorrect_answer(self, interaction: discord.Interaction):
        """Processa resposta incorreta"""
        embed = discord.Embed(
            title="❌ Resposta Incorreta",
            description="A resposta que você forneceu está incorreta.",
            color=0xff0000
        )
        embed.add_field(
            name="Dica",
            value="Verifique se digitou corretamente e tente novamente.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CaptchaSystemCog(commands.Cog):
    """Cog para o sistema de captcha de guardiões"""
    
    def __init__(self, bot):
        self.bot = bot
        self.captcha_check_loop.start()
        self.captcha_timeout_loop.start()
    
    def generate_captcha(self) -> tuple[str, str, str]:
        """Gera um captcha matemático simples"""
        # Tipos de captcha
        captcha_types = [
            self._generate_math_captcha,
            self._generate_word_captcha,
            self._generate_sequence_captcha
        ]
        
        # Escolhe um tipo aleatório
        captcha_type = random.choice(captcha_types)
        return captcha_type()
    
    def _generate_math_captcha(self) -> tuple[str, str, str]:
        """Gera captcha matemático"""
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        operation = random.choice(['+', '-', '*'])
        
        if operation == '+':
            question = f"{a} + {b} = ?"
            answer = str(a + b)
        elif operation == '-':
            # Garante resultado positivo
            if a < b:
                a, b = b, a
            question = f"{a} - {b} = ?"
            answer = str(a - b)
        else:  # *
            question = f"{a} × {b} = ?"
            answer = str(a * b)
        
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return code, question, answer
    
    def _generate_word_captcha(self) -> tuple[str, str, str]:
        """Gera captcha de palavra"""
        words = [
            ("Qual é a cor do céu?", "azul"),
            ("Quantos dias tem uma semana?", "7"),
            ("Qual é o primeiro mês do ano?", "janeiro"),
            ("Quantos dedos tem uma mão?", "5"),
            ("Qual é a capital do Brasil?", "brasilia")
        ]
        
        question, answer = random.choice(words)
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return code, question, answer
    
    def _generate_sequence_captcha(self) -> tuple[str, str, str]:
        """Gera captcha de sequência"""
        sequences = [
            ("2, 4, 6, ?", "8"),
            ("1, 3, 5, ?", "7"),
            ("A, C, E, ?", "G"),
            ("1, 4, 9, ?", "16"),
            ("2, 6, 12, ?", "20")
        ]
        
        question, answer = random.choice(sequences)
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return code, question, answer
    
    async def send_captcha_to_guardian(self, guardian_id: int, channel_id: int) -> bool:
        """Envia captcha para um guardião específico"""
        try:
            # Gera o captcha
            code, question, answer = self.generate_captcha()
            
            # Calcula expiração
            expiration = datetime.utcnow() + timedelta(minutes=CAPTCHA_TIMEOUT_MINUTES)
            
            # Salva no banco
            insert_query = """
                INSERT INTO captchas_guardioes 
                (id_guardiao, captcha_code, captcha_question, captcha_answer, data_expiracao, canal_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """
            captcha_id = await db_manager.execute_scalar(
                insert_query, guardian_id, code, question, answer, expiration, channel_id
            )
            
            # Busca dados do guardião
            guardian_data = await db_manager.execute_one(
                "SELECT username, display_name FROM usuarios WHERE id_discord = $1",
                guardian_id
            )
            
            if not guardian_data:
                logger.error(f"Guardião {guardian_id} não encontrado no banco")
                return False
            
            # Cria embed
            embed = discord.Embed(
                title="🔐 Verificação de Atividade",
                description="Você está em serviço há mais de 3 horas. Confirme que está ativo respondendo ao captcha abaixo.",
                color=0xffa500
            )
            embed.add_field(
                name="Pergunta",
                value=f"**{question}**",
                inline=False
            )
            embed.add_field(
                name="⏰ Tempo Limite",
                value=f"{CAPTCHA_TIMEOUT_MINUTES} minutos",
                inline=True
            )
            embed.add_field(
                name="⚠️ Consequência",
                value="Se não responder, será removido do serviço e perderá 50% dos pontos",
                inline=False
            )
            embed.set_footer(text=f"Código: {code}")
            
            # Cria view
            view = CaptchaView(captcha_id, answer)
            
            # Envia mensagem
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Canal {channel_id} não encontrado")
                return False
            
            message = await channel.send(
                content=f"<@{guardian_id}>",
                embed=embed,
                view=view
            )
            
            # Atualiza ID da mensagem no banco
            update_query = "UPDATE captchas_guardioes SET mensagem_id = $1 WHERE id = $2"
            await db_manager.execute_command(update_query, message.id, captcha_id)
            
            logger.info(f"Captcha enviado para guardião {guardian_id} (ID: {captcha_id})")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar captcha para guardião {guardian_id}: {e}")
            return False
    
    @tasks.loop(minutes=CAPTCHA_CHECK_INTERVAL_MINUTES)
    async def captcha_check_loop(self):
        """Loop que verifica guardiões que precisam receber captcha"""
        try:
            if not db_manager.pool:
                return
            
            # Busca guardiões em serviço há mais de 3 horas que não têm captcha pendente
            # E que não responderam captcha nas últimas 3+ horas
            query = """
                SELECT u.id_discord, u.username, u.ultimo_turno_inicio
                FROM usuarios u
                LEFT JOIN captchas_guardioes c_pendente ON u.id_discord = c_pendente.id_guardiao 
                    AND c_pendente.status = 'Pendente' 
                    AND c_pendente.data_envio > NOW() - INTERVAL '1 hour'
                LEFT JOIN captchas_guardioes c_respondido ON u.id_discord = c_respondido.id_guardiao 
                    AND c_respondido.status = 'Respondido' 
                    AND c_respondido.data_resposta > NOW() - INTERVAL '%s hours'
                WHERE u.em_servico = TRUE 
                    AND u.categoria IN ('Guardião', 'Moderador', 'Administrador')
                    AND u.ultimo_turno_inicio IS NOT NULL
                    AND u.ultimo_turno_inicio <= NOW() - INTERVAL '%s hours'
                    AND c_pendente.id IS NULL
                    AND c_respondido.id IS NULL
            """ % (CAPTCHA_SERVICE_HOURS, CAPTCHA_SERVICE_HOURS)
            
            guardians = await db_manager.execute_query(query)
            
            for guardian in guardians:
                try:
                    # Envia captcha via DM
                    user = self.bot.get_user(guardian['id_discord'])
                    if user:
                        dm_channel = await user.create_dm()
                        await self.send_captcha_to_guardian(guardian['id_discord'], dm_channel.id)
                    else:
                        logger.warning(f"Usuário {guardian['id_discord']} não encontrado")
                        
                except Exception as e:
                    logger.error(f"Erro ao enviar captcha para {guardian['id_discord']}: {e}")
            
        except Exception as e:
            logger.error(f"Erro no loop de verificação de captcha: {e}")
    
    @tasks.loop(minutes=1)
    async def captcha_timeout_loop(self):
        """Loop que verifica captchas expirados"""
        try:
            if not db_manager.pool:
                return
            
            # Busca captchas expirados
            query = """
                SELECT c.*, u.username, u.pontos, u.ultimo_turno_inicio
                FROM captchas_guardioes c
                JOIN usuarios u ON c.id_guardiao = u.id_discord
                WHERE c.status = 'Pendente' 
                    AND c.data_expiracao <= NOW()
            """
            
            expired_captchas = await db_manager.execute_query(query)
            
            for captcha in expired_captchas:
                try:
                    await self._handle_expired_captcha(captcha)
                except Exception as e:
                    logger.error(f"Erro ao processar captcha expirado {captcha['id']}: {e}")
            
        except Exception as e:
            logger.error(f"Erro no loop de timeout de captcha: {e}")
    
    async def _handle_expired_captcha(self, captcha_data: dict):
        """Processa captcha expirado"""
        try:
            guardian_id = captcha_data['id_guardiao']
            current_points = captcha_data['pontos']
            
            # Calcula pontos perdidos (50% do que ganharia em 3 horas)
            points_lost = int((CAPTCHA_SERVICE_HOURS * TURN_POINTS_PER_HOUR) * (CAPTCHA_PENALTY_PERCENTAGE / 100))
            new_points = max(0, current_points - points_lost)
            
            # Remove do serviço e aplica penalidade
            update_query = """
                UPDATE usuarios 
                SET em_servico = FALSE, ultimo_turno_inicio = NULL, pontos = $1
                WHERE id_discord = $2
            """
            await db_manager.execute_command(update_query, new_points, guardian_id)
            
            # Atualiza status do captcha
            captcha_update_query = """
                UPDATE captchas_guardioes 
                SET status = 'Expirado', pontos_penalizados = $1
                WHERE id = $2
            """
            await db_manager.execute_command(captcha_update_query, points_lost, captcha_data['id'])
            
            # Tenta editar a mensagem original
            try:
                channel = self.bot.get_channel(captcha_data['canal_id'])
                if channel and captcha_data['mensagem_id']:
                    message = await channel.fetch_message(captcha_data['mensagem_id'])
                    if message:
                        embed = discord.Embed(
                            title="⏰ Captcha Expirado",
                            description="Você não respondeu ao captcha a tempo e foi removido do serviço.",
                            color=0xff0000
                        )
                        embed.add_field(
                            name="Penalidade Aplicada",
                            value=f"❌ Removido do serviço\n💰 {points_lost} pontos perdidos",
                            inline=False
                        )
                        embed.add_field(
                            name="Motivo",
                            value="Não respondeu ao captcha em 15 minutos",
                            inline=False
                        )
                        
                        await message.edit(
                            content="⏰ **Captcha expirado!**",
                            embed=embed,
                            view=None
                        )
            except Exception as e:
                logger.warning(f"Não foi possível editar mensagem do captcha expirado: {e}")
            
            # Envia DM de notificação
            try:
                user = self.bot.get_user(guardian_id)
                if user:
                    dm_channel = await user.create_dm()
                    embed = discord.Embed(
                        title="⏰ Captcha Expirado",
                        description="Você não respondeu ao captcha a tempo e foi removido do serviço.",
                        color=0xff0000
                    )
                    embed.add_field(
                        name="Penalidade Aplicada",
                        value=f"❌ Removido do serviço\n💰 {points_lost} pontos perdidos",
                        inline=False
                    )
                    embed.add_field(
                        name="Próximos Passos",
                        value="Use `/turno` para entrar em serviço novamente",
                        inline=False
                    )
                    
                    await dm_channel.send(embed=embed)
            except Exception as e:
                logger.warning(f"Não foi possível enviar DM de notificação: {e}")
            
            logger.info(f"Captcha expirado processado para guardião {guardian_id} - {points_lost} pontos perdidos")
            
        except Exception as e:
            logger.error(f"Erro ao processar captcha expirado: {e}")
    
    @captcha_check_loop.before_loop
    async def before_captcha_check_loop(self):
        """Aguarda o bot estar pronto antes de iniciar o loop"""
        await self.bot.wait_until_ready()
    
    @captcha_timeout_loop.before_loop
    async def before_captcha_timeout_loop(self):
        """Aguarda o bot estar pronto antes de iniciar o loop"""
        await self.bot.wait_until_ready()


async def setup(bot):
    """Função de setup do cog"""
    await bot.add_cog(CaptchaSystemCog(bot))
