"""
Cog de Moderação - Sistema Guardião BETA
Implementa o sistema completo de denúncias, distribuição, votação e punições
"""

import discord
from discord.ext import commands, tasks
from discord import ui, app_commands
import logging
import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from database.connection import db_manager, get_user_by_discord_id
from utils.experience_system import calculate_experience_reward
from config import (
    MAX_GUARDIANS_PER_REPORT, REQUIRED_VOTES_FOR_DECISION, 
    VOTE_TIMEOUT_MINUTES, DISPENSE_COOLDOWN_MINUTES, 
    INACTIVE_PENALTY_HOURS, PUNISHMENT_RULES
)

# Configuração de logging
logger = logging.getLogger(__name__)


class ReportView(ui.View):
    """View para botões de atendimento/dispensa de denúncias"""
    
    def __init__(self, hash_denuncia: str, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.hash_denuncia = hash_denuncia
    
    @ui.button(label="Atender", style=discord.ButtonStyle.success, emoji="✅")
    async def atender_denuncia(self, interaction: discord.Interaction, button: ui.Button):
        await self._handle_atender(interaction)
    
    @ui.button(label="Dispensar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def dispensar_denuncia(self, interaction: discord.Interaction, button: ui.Button):
        await self._handle_dispensar(interaction)
    
    async def _handle_atender(self, interaction: discord.Interaction):
        """Processa o atendimento de uma denúncia"""
        try:
            logger.info(f"Guardian {interaction.user.id} tentando atender denúncia {self.hash_denuncia}")
            
            # Verifica se ainda há vagas para esta denúncia
            count_query = """
                SELECT COUNT(*) FROM votos_guardioes 
                WHERE id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $1)
            """
            count = db_manager.execute_scalar_sync(count_query, self.hash_denuncia)
            logger.info(f"Votos existentes para denúncia {self.hash_denuncia}: {count}")
            
            if count >= REQUIRED_VOTES_FOR_DECISION:
                embed = discord.Embed(
                    title="❌ Vaga Indisponível",
                    description="Infelizmente a ocorrência já foi atendida por outros Guardiões.",
                    color=0xff0000
                )
                await interaction.response.edit_message(embed=embed, view=None)
                return
            
            # Busca os detalhes da denúncia
            denuncia_query = """
                SELECT d.*, u.username as denunciante_name, u2.username as denunciado_name
                FROM denuncias d
                JOIN usuarios u ON d.id_denunciante = u.id_discord
                JOIN usuarios u2 ON d.id_denunciado = u2.id_discord
                WHERE d.hash_denuncia = $1
            """
            denuncia = db_manager.execute_one_sync(denuncia_query, self.hash_denuncia)
            
            # Debug: verifica se a denúncia existe sem JOINs
            if not denuncia:
                # Tenta buscar apenas a denúncia sem JOINs para debug
                simple_query = "SELECT * FROM denuncias WHERE hash_denuncia = $1"
                simple_denuncia = db_manager.execute_one_sync(simple_query, self.hash_denuncia)
                
                if simple_denuncia:
                    logger.error(f"Denúncia encontrada sem JOINs: {simple_denuncia}")
                    # Busca os usuários separadamente
                    denunciante = db_manager.execute_one_sync(
                        "SELECT username FROM usuarios WHERE id_discord = $1", 
                        simple_denuncia['id_denunciante']
                    )
                    denunciado = db_manager.execute_one_sync(
                        "SELECT username FROM usuarios WHERE id_discord = $1", 
                        simple_denuncia['id_denunciado']
                    )
                    
                    logger.info(f"Denunciante {simple_denuncia['id_denunciante']}: {denunciante}")
                    logger.info(f"Denunciado {simple_denuncia['id_denunciado']}: {denunciado}")
                    
                    # Cria o objeto denúncia manualmente
                    denuncia = simple_denuncia.copy()
                    denuncia['denunciante_name'] = denunciante['username'] if denunciante else f'Usuário {simple_denuncia["id_denunciante"]}'
                    denuncia['denunciado_name'] = denunciado['username'] if denunciado else f'Usuário {simple_denuncia["id_denunciado"]}'
                else:
                    logger.error(f"Denúncia com hash {self.hash_denuncia} não encontrada no banco")
                    await interaction.response.send_message("Denúncia não encontrada.", ephemeral=True)
                    return
            
            # Busca as mensagens capturadas
            mensagens_query = """
                SELECT * FROM mensagens_capturadas 
                WHERE id_denuncia = $1 
                ORDER BY timestamp_mensagem
            """
            mensagens = db_manager.execute_query_sync(mensagens_query, denuncia['id'])
            
            # Cria o embed com os detalhes da denúncia
            embed = discord.Embed(
                title="🚨 Nova Ocorrência - Análise Requerida",
                description="Analise cuidadosamente as evidências antes de votar.",
                color=0xff6600
            )
            
            embed.add_field(
                name="📋 Informações da Denúncia",
                value=f"**Hash:** `{self.hash_denuncia}`\n"
                      f"**Motivo:** {denuncia['motivo']}\n"
                      f"**Data:** {denuncia['data_criacao'].strftime('%d/%m/%Y às %H:%M')}",
                inline=False
            )
            
            # Adiciona as mensagens capturadas (anonimizadas)
            if mensagens:
                logger.info(f"Exibindo {len(mensagens)} mensagens capturadas")
                embed.add_field(
                    name="💬 Mensagens Capturadas",
                    value=self._anonymize_messages(mensagens, denuncia['id_denunciado']),
                    inline=False
                )
            else:
                logger.info("Nenhuma mensagem capturada encontrada")
                embed.add_field(
                    name="💬 Mensagens Capturadas",
                    value="Nenhuma mensagem foi encontrada no histórico das últimas 24 horas.",
                    inline=False
                )
            
            embed.add_field(
                name="⚠️ Importante",
                value="• Analise todas as evidências\n"
                      "• Seja imparcial em seu julgamento\n"
                      "• Você tem 5 minutos para votar\n"
                      "• Considere o contexto e as regras do servidor",
                inline=False
            )
            
            # Cria a view de votação
            vote_view = VoteView(self.hash_denuncia, interaction.user.id)
            
            await interaction.response.edit_message(embed=embed, view=vote_view)
            
            # Inicia o timer de 5 minutos
            await self._start_vote_timer(interaction.user.id, self.hash_denuncia)
            
        except Exception as e:
            logger.error(f"Erro ao atender denúncia: {e}")
            await interaction.response.send_message("Erro ao processar atendimento.", ephemeral=True)
    
    async def _handle_dispensar(self, interaction: discord.Interaction):
        """Processa a dispensa de uma denúncia"""
        try:
            # Define o cooldown de dispensa
            cooldown_time = datetime.utcnow() + timedelta(minutes=DISPENSE_COOLDOWN_MINUTES)
            query = "UPDATE usuarios SET cooldown_dispensa = $1 WHERE id_discord = $2"
            db_manager.execute_command_sync(query, cooldown_time, interaction.user.id)
            
            embed = discord.Embed(
                title="❌ Ocorrência Dispensada",
                description="Você dispensou esta ocorrência. Cooldown de 10 minutos ativado.",
                color=0xffa500
            )
            embed.add_field(
                name="⏰ Cooldown",
                value=f"Você poderá receber novas ocorrências em {DISPENSE_COOLDOWN_MINUTES} minutos.",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Erro ao dispensar denúncia: {e}")
            await interaction.response.send_message("Erro ao dispensar ocorrência.", ephemeral=True)
    
    def _anonymize_messages(self, mensagens: List[Dict], id_denunciado: int) -> str:
        """Anonimiza as mensagens para proteção da privacidade"""
        anonymized = []
        
        for msg in mensagens:
            timestamp = msg['timestamp_mensagem'].strftime('%H:%M')
            content = msg['conteudo']
            
            # Substitui menções por texto genérico
            content = re.sub(r'<@!?\d+>', '[Usuário Alvo]' if msg['id_autor'] == id_denunciado else '[Outro Usuário]', content)
            
            # Destaca mensagens do denunciado
            if msg['id_autor'] == id_denunciado:
                content = f"**{content}**"
            
            anonymized.append(f"`{timestamp}` {content}")
        
        return "\n".join(anonymized[:10])  # Limita a 10 mensagens
    
    async def _start_vote_timer(self, user_id: int, hash_denuncia: str):
        """Inicia o timer de 5 minutos para votação"""
        try:
            await asyncio.sleep(VOTE_TIMEOUT_MINUTES * 60)
            
            # Verifica se o usuário votou
            vote_check = """
                SELECT id FROM votos_guardioes 
                WHERE id_guardiao = $1 AND id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $2)
            """
            vote_exists = db_manager.execute_scalar_sync(vote_check, user_id, hash_denuncia)
            
            if not vote_exists:
                # Aplica penalidade por inatividade
                await self._apply_inactivity_penalty(user_id)
                
        except Exception as e:
            logger.error(f"Erro no timer de votação: {e}")
    
    async def _apply_inactivity_penalty(self, user_id: int):
        """Aplica penalidade por inatividade"""
        try:
            # Remove 5 pontos e define cooldown
            penalty_time = datetime.utcnow() + timedelta(hours=INACTIVE_PENALTY_HOURS)
            query = """
                UPDATE usuarios 
                SET pontos = pontos - 5, cooldown_inativo = $1 
                WHERE id_discord = $2
            """
            db_manager.execute_command_sync(query, penalty_time, user_id)
            
            logger.info(f"Penalidade de inatividade aplicada ao usuário {user_id}")
            
        except Exception as e:
            logger.error(f"Erro ao aplicar penalidade de inatividade: {e}")


class VoteView(ui.View):
    """View para votação em denúncias"""
    
    def __init__(self, hash_denuncia: str, guardiao_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.hash_denuncia = hash_denuncia
        self.guardiao_id = guardiao_id
    
    @ui.button(label="OK!", style=discord.ButtonStyle.success, emoji="✅")
    async def vote_ok(self, interaction: discord.Interaction, button: ui.Button):
        await self._process_vote(interaction, "OK!")
    
    @ui.button(label="Intimidou", style=discord.ButtonStyle.secondary, emoji="⚠️")
    async def vote_intimidou(self, interaction: discord.Interaction, button: ui.Button):
        await self._process_vote(interaction, "Intimidou")
    
    @ui.button(label="Grave", style=discord.ButtonStyle.danger, emoji="🚨")
    async def vote_grave(self, interaction: discord.Interaction, button: ui.Button):
        await self._process_vote(interaction, "Grave")
    
    async def _process_vote(self, interaction: discord.Interaction, voto: str):
        """Processa o voto do guardião"""
        try:
            # Verifica se o usuário já votou nesta denúncia
            check_query = """
                SELECT id FROM votos_guardioes 
                WHERE id_guardiao = $1 AND id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $2)
            """
            existing_vote = db_manager.execute_scalar_sync(check_query, self.guardiao_id, self.hash_denuncia)
            
            if existing_vote:
                await interaction.response.send_message("Você já votou nesta denúncia!", ephemeral=True)
                return
            
            # Registra o voto
            vote_query = """
                INSERT INTO votos_guardioes (id_denuncia, id_guardiao, voto)
                SELECT id, $1, $2 FROM denuncias WHERE hash_denuncia = $3
            """
            db_manager.execute_command_sync(vote_query, self.guardiao_id, voto, self.hash_denuncia)
            
            # Confirma o voto
            embed = discord.Embed(
                title="✅ Voto Computado!",
                description=f"Seu voto **{voto}** foi registrado com sucesso.",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Verifica se a denúncia atingiu 5 votos
            await self._check_denuncia_completion()
            
        except Exception as e:
            logger.error(f"Erro ao processar voto: {e}")
            await interaction.response.send_message("Erro ao processar voto.", ephemeral=True)
    
    async def _check_denuncia_completion(self):
        """Verifica se a denúncia atingiu 5 votos e processa o resultado"""
        try:
            # Conta os votos
            count_query = """
                SELECT COUNT(*) FROM votos_guardioes 
                WHERE id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $1)
            """
            total_votes = db_manager.execute_scalar_sync(count_query, self.hash_denuncia)
            
            if total_votes >= REQUIRED_VOTES_FOR_DECISION:
                await self._finalize_denuncia()
                
        except Exception as e:
            logger.error(f"Erro ao verificar conclusão da denúncia: {e}")
    
    async def _finalize_denuncia(self):
        """Finaliza a denúncia e aplica a punição"""
        try:
            # Busca todos os votos
            votes_query = """
                SELECT voto FROM votos_guardioes 
                WHERE id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $1)
            """
            votes = db_manager.execute_query_sync(votes_query, self.hash_denuncia)
            
            # Conta os votos
            vote_counts = {"OK!": 0, "Intimidou": 0, "Grave": 0}
            for vote in votes:
                vote_counts[vote['voto']] += 1
            
            # Determina o resultado
            result = self._determine_punishment(vote_counts)
            
            # Aplica a punição se necessário
            if result['punishment']:
                await self._apply_punishment(result)
            
            # Atualiza a denúncia
            update_query = """
                UPDATE denuncias 
                SET status = 'Finalizada', resultado_final = $1 
                WHERE hash_denuncia = $2
            """
            db_manager.execute_command_sync(update_query, result['type'], self.hash_denuncia)
            
            # Distribui experiência para os guardiões
            await self._distribute_experience()
            
            # Envia DM para o denunciado com botão de apelação
            await self._send_appeal_notification(result)
            
        except Exception as e:
            logger.error(f"Erro ao finalizar denúncia: {e}")
    
    def _determine_punishment(self, vote_counts: Dict[str, int]) -> Dict:
        """Determina a punição baseada nos votos"""
        ok_votes = vote_counts["OK!"]
        intimidou_votes = vote_counts["Intimidou"]
        grave_votes = vote_counts["Grave"]
        
        # 3+ "OK!": Improcedente
        if ok_votes >= 3:
            return {"type": "Improcedente", "punishment": False}
        
        # 3 "Intimidou": Mute de 1 hora
        if intimidou_votes >= 3 and grave_votes == 0:
            return {
                "type": "Intimidou", 
                "punishment": True, 
                "duration": PUNISHMENT_RULES['intimidou_3'] * 3600
            }
        
        # 3 "Intimidou" + 2 "Grave": Mute de 6 horas
        if intimidou_votes >= 3 and grave_votes >= 2:
            return {
                "type": "Intimidou + Grave", 
                "punishment": True, 
                "duration": PUNISHMENT_RULES['intimidou_grave'] * 3600
            }
        
        # 3 "Grave": Mute de 12 horas
        if grave_votes >= 3 and intimidou_votes < 3:
            return {
                "type": "Grave", 
                "punishment": True, 
                "duration": PUNISHMENT_RULES['grave_3'] * 3600
            }
        
        # 4+ "Grave": Ban de 24 horas
        if grave_votes >= 4:
            return {
                "type": "Grave", 
                "punishment": True, 
                "duration": PUNISHMENT_RULES['grave_4_plus'] * 3600,
                "is_ban": True
            }
        
        # Caso não se encaixe em nenhuma regra, considera improcedente
        return {"type": "Improcedente", "punishment": False}
    
    async def _apply_punishment(self, result: Dict):
        """Aplica a punição no Discord"""
        try:
            # Busca informações da denúncia
            denuncia_query = """
                SELECT id_servidor, id_denunciado FROM denuncias 
                WHERE hash_denuncia = $1
            """
            denuncia = db_manager.execute_one_sync(denuncia_query, self.hash_denuncia)
            
            if not denuncia:
                return
            
            # Busca o servidor
            guild = self.bot.get_guild(denuncia['id_servidor'])
            if not guild:
                logger.warning(f"Servidor {denuncia['id_servidor']} não encontrado")
                return
            
            # Busca o membro
            member = guild.get_member(denuncia['id_denunciado'])
            if not member:
                logger.warning(f"Membro {denuncia['id_denunciado']} não encontrado no servidor")
                return
            
            # Aplica a punição
            if result.get('is_ban'):
                # Ban temporário (não implementado no Discord, então usa timeout longo)
                await member.timeout(discord.utils.timedelta(seconds=result['duration']))
                logger.info(f"Ban aplicado para {member.display_name} por {result['duration']} segundos")
            else:
                # Timeout
                await member.timeout(discord.utils.timedelta(seconds=result['duration']))
                logger.info(f"Timeout aplicado para {member.display_name} por {result['duration']} segundos")
            
        except Exception as e:
            logger.error(f"Erro ao aplicar punição: {e}")
    
    async def _distribute_experience(self):
        """Distribui experiência para os guardiões que votaram"""
        try:
            # Busca os guardiões que votaram
            guardians_query = """
                SELECT id_guardiao, voto FROM votos_guardioes 
                WHERE id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $1)
            """
            guardians = db_manager.execute_query_sync(guardians_query, self.hash_denuncia)
            
            for guardian in guardians:
                xp_reward = calculate_experience_reward(guardian['voto'])
                
                # Adiciona experiência
                update_query = """
                    UPDATE usuarios 
                    SET experiencia = experiencia + $1 
                    WHERE id_discord = $2
                """
                db_manager.execute_command_sync(update_query, xp_reward, guardian['id_guardiao'])
            
            logger.info(f"Experiência distribuída para {len(guardians)} guardiões")
            
        except Exception as e:
            logger.error(f"Erro ao distribuir experiência: {e}")
    
    async def _send_appeal_notification(self, result: Dict):
        """Envia notificação de punição para o denunciado com botão de apelação"""
        try:
            # Busca informações da denúncia
            denuncia_query = """
                SELECT id_denunciado FROM denuncias 
                WHERE hash_denuncia = $1
            """
            denuncia = db_manager.execute_one_sync(denuncia_query, self.hash_denuncia)
            
            if not denuncia:
                return
            
            # Cria o embed de notificação
            if result['punishment']:
                embed = discord.Embed(
                    title="⚖️ Punição Aplicada",
                    description="Você recebeu uma punição baseada em denúncia da comunidade.",
                    color=0xff0000
                )
                
                duration_hours = result['duration'] // 3600
                embed.add_field(
                    name="📋 Detalhes",
                    value=f"**Tipo:** {result['type']}\n"
                          f"**Duração:** {duration_hours} horas\n"
                          f"**Hash da Denúncia:** `{self.hash_denuncia}`",
                    inline=False
                )
                
                # Cria view com botão de apelação
                appeal_view = AppealView(self.hash_denuncia)
                
                # Envia DM para o usuário
                user = self.bot.get_user(denuncia['id_denunciado'])
                if user:
                    await user.send(embed=embed, view=appeal_view)
                    
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de apelação: {e}")


class AppealView(ui.View):
    """View para apelação de punições"""
    
    def __init__(self, hash_denuncia: str, timeout: float = 86400):  # 24 horas
        super().__init__(timeout=timeout)
        self.hash_denuncia = hash_denuncia
    
    @ui.button(label="Apelar", style=discord.ButtonStyle.danger, emoji="⚖️")
    async def appeal_punishment(self, interaction: discord.Interaction, button: ui.Button):
        try:
            # Altera o status da denúncia para "Apelada"
            query = "UPDATE denuncias SET status = 'Apelada' WHERE hash_denuncia = $1"
            db_manager.execute_command_sync(query, self.hash_denuncia)
            
            embed = discord.Embed(
                title="⚖️ Apelação Registrada",
                description="Sua apelação foi registrada e será reanalisada pelos Guardiões.",
                color=0xffa500
            )
            embed.add_field(
                name="📋 Informações",
                value=f"**Hash:** `{self.hash_denuncia}`\n"
                      f"**Status:** Em reanálise\n"
                      f"**Tempo estimado:** 24-48 horas",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Erro ao processar apelação: {e}")
            await interaction.response.send_message("Erro ao processar apelação.", ephemeral=True)


class ModeracaoCog(commands.Cog):
    """Cog para comandos de moderação"""
    
    def __init__(self, bot):
        self.bot = bot
        self.distribution_loop.start()
        self.inactivity_check.start()
    
    @app_commands.command(
        name="report",
        description="Denuncie um usuário por violação das regras"
    )
    @app_commands.describe(usuario="Usuário a ser denunciado", motivo="Motivo da denúncia")
    async def report(self, interaction: discord.Interaction, usuario: discord.Member, motivo: str):
        """
        Comando para denunciar usuários
        
        Cria uma denúncia e inicia o processo de moderação comunitária
        """
        try:
            # Verifica argumentos
            if not usuario or not motivo:
                embed = discord.Embed(
                    title="❌ Uso Incorreto",
                    description="Use: `!report @usuario motivo da denúncia`",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Verifica se o banco de dados está disponível
            if not db_manager.pool:
                db_manager.initialize_pool()
            
            # Verifica se o usuário está cadastrado
            user_data = await get_user_by_discord_id(interaction.user.id)
            if not user_data:
                embed = discord.Embed(
                    title="❌ Usuário Não Cadastrado",
                    description="Você precisa se cadastrar primeiro usando `!cadastro`!",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Verifica se não está denunciando a si mesmo
            if interaction.user.id == usuario.id:
                embed = discord.Embed(
                    title="❌ Denúncia Inválida",
                    description="Você não pode denunciar a si mesmo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Gera hash único para a denúncia
            hash_input = f"{interaction.user.id}{usuario.id}{interaction.guild.id}{datetime.utcnow().isoformat()}"
            hash_denuncia = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
            
            # Verifica se o servidor é premium
            premium_query = """
                SELECT id_servidor FROM servidores_premium 
                WHERE id_servidor = $1 AND data_fim > NOW()
            """
            is_premium = db_manager.execute_scalar_sync(premium_query, interaction.guild.id) is not None
            
            # Insere a denúncia no banco
            denuncia_query = """
                INSERT INTO denuncias (
                    hash_denuncia, id_servidor, id_canal, id_denunciante, 
                    id_denunciado, motivo, e_premium
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """
            denuncia_id = db_manager.execute_scalar_sync(
                denuncia_query, hash_denuncia, interaction.guild.id, interaction.channel.id,
                interaction.user.id, usuario.id, motivo, is_premium
            )
            
            # Captura mensagens do histórico
            await self._capture_messages(interaction, usuario, denuncia_id)
            
            # Conta guardiões em serviço
            guardians_query = """
                SELECT COUNT(*) FROM usuarios 
                WHERE em_servico = TRUE AND categoria = 'Guardião'
            """
            guardians_count = db_manager.execute_scalar_sync(guardians_query)
            
            # Resposta de confirmação
            embed = discord.Embed(
                title="✅ Denúncia Registrada!",
                description="Sua denúncia foi registrada e será analisada pelos Guardiões.",
                color=0x00ff00
            )
            embed.add_field(
                name="📋 Detalhes",
                value=f"**Usuário:** {usuario.display_name}\n"
                      f"**Motivo:** {motivo}\n"
                      f"**Hash:** `{hash_denuncia}`",
                inline=False
            )
            embed.add_field(
                name="👥 Guardiões Disponíveis",
                value=f"**{guardians_count}** Guardiões estão em serviço",
                inline=True
            )
            embed.add_field(
                name="⏱️ Tempo Estimado",
                value="Análise em até 30 minutos",
                inline=True
            )
            
            if is_premium:
                embed.add_field(
                    name="⭐ Premium",
                    value="Este servidor tem prioridade na análise",
                    inline=True
                )
            
            embed.set_footer(text="Sistema Guardião BETA - Moderação Comunitária")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro no comando report: {e}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _capture_messages(self, interaction: discord.Interaction, target_user: discord.Member, denuncia_id: int):
        """Captura mensagens do histórico do canal"""
        try:
            messages_captured = 0
            total_messages_checked = 0
            target_user_messages = 0
            
            # Busca mensagens das últimas 24 horas
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            logger.info(f"Capturando mensagens do usuário {target_user.id} ({target_user.display_name}) desde {cutoff_time}")
            
            async for message in interaction.channel.history(limit=100, after=cutoff_time):
                total_messages_checked += 1
                
                # Log para debug
                if total_messages_checked <= 5:
                    logger.info(f"Mensagem {total_messages_checked}: autor={message.author.id}, criada={message.created_at}, conteúdo='{message.content[:50]}...'")
                
                # Filtra apenas mensagens do usuário denunciado
                if message.author.id == target_user.id:
                    target_user_messages += 1
                    
                    # Prepara URLs dos anexos
                    attachment_urls = []
                    for attachment in message.attachments:
                        attachment_urls.append(attachment.url)
                    
                    # Insere a mensagem no banco
                    mensagem_query = """
                        INSERT INTO mensagens_capturadas (
                            id_denuncia, id_autor, conteudo, anexos_urls, timestamp_mensagem
                        ) VALUES ($1, $2, $3, $4, $5)
                    """
                    db_manager.execute_command_sync(
                        mensagem_query, denuncia_id, message.author.id, 
                        message.content, ",".join(attachment_urls), message.created_at
                    )
                    
                    messages_captured += 1
                    
                    if messages_captured >= 20:  # Limita a 20 mensagens
                        break
            
            logger.info(f"Capturadas {messages_captured} mensagens para denúncia {denuncia_id} (total verificadas: {total_messages_checked}, do usuário: {target_user_messages})")
            
        except Exception as e:
            logger.error(f"Erro ao capturar mensagens: {e}")
    
    def _anonymize_messages(self, mensagens: List[Dict], id_denunciado: int) -> str:
        """Anonimiza mensagens para exibição"""
        try:
            if not mensagens:
                return "Nenhuma mensagem encontrada."
            
            result = []
            for msg in mensagens[:10]:  # Limita a 10 mensagens para não exceder o limite do Discord
                timestamp = msg['timestamp_mensagem'].strftime('%d/%m às %H:%M')
                
                # Anonimiza o autor (mostra como "Denunciado" se for o usuário denunciado)
                if msg['id_autor'] == id_denunciado:
                    autor = "🔴 **Denunciado**"
                else:
                    autor = "👤 **Usuário**"
                
                # Limita o conteúdo da mensagem
                conteudo = msg['conteudo'][:200] + "..." if len(msg['conteudo']) > 200 else msg['conteudo']
                
                result.append(f"{autor} ({timestamp}): {conteudo}")
                
                # Adiciona anexos se existirem
                if msg['anexos_urls']:
                    result.append(f"📎 {msg['anexos_urls']}")
            
            return "\n\n".join(result)
            
        except Exception as e:
            logger.error(f"Erro ao anonimizar mensagens: {e}")
            return "Erro ao processar mensagens."
    
    @tasks.loop(seconds=10)
    async def distribution_loop(self):
        """Loop que distribui denúncias para Guardiões em serviço"""
        try:
            if not db_manager.pool:
                return
            
            # Busca denúncias pendentes (premium primeiro)
            denuncias_query = """
                SELECT * FROM denuncias 
                WHERE status = 'Pendente' 
                ORDER BY e_premium DESC, data_criacao ASC
                LIMIT 1
            """
            denuncia = db_manager.execute_one_sync(denuncias_query)
            
            if not denuncia:
                return
            
            # Busca guardiões disponíveis
            guardians_query = """
                SELECT id_discord FROM usuarios 
                WHERE em_servico = TRUE 
                AND categoria = 'Guardião'
                AND (cooldown_dispensa IS NULL OR cooldown_dispensa <= NOW())
                AND (cooldown_inativo IS NULL OR cooldown_inativo <= NOW())
                AND id_discord NOT IN (
                    SELECT id_guardiao FROM votos_guardioes 
                    WHERE id_denuncia = $1
                )
                ORDER BY RANDOM()
                LIMIT $2
            """
            guardians = db_manager.execute_query_sync(guardians_query, denuncia['id'], MAX_GUARDIANS_PER_REPORT)
            
            if not guardians:
                return
            
            # Muda o status para "Em Análise"
            update_query = "UPDATE denuncias SET status = 'Em Análise' WHERE id = $1"
            db_manager.execute_command_sync(update_query, denuncia['id'])
            
            # Envia para cada guardião
            for guardian_data in guardians:
                await self._send_to_guardian(guardian_data['id_discord'], denuncia)
            
            logger.info(f"Denúncia {denuncia['hash_denuncia']} enviada para {len(guardians)} guardiões")
            
        except Exception as e:
            logger.error(f"Erro no loop de distribuição: {e}")
    
    async def _send_to_guardian(self, guardian_id: int, denuncia: Dict):
        """Envia denúncia para um guardião específico"""
        try:
            user = self.bot.get_user(guardian_id)
            if not user:
                return
            
            embed = discord.Embed(
                title="🚨 NOVA OCORRÊNCIA!",
                description="Você recebeu uma nova denúncia para análise.",
                color=0xff0000
            )
            
            embed.add_field(
                name="📋 Informações Básicas",
                value=f"**Hash:** `{denuncia['hash_denuncia']}`\n"
                      f"**Motivo:** {denuncia['motivo']}\n"
                      f"**Prioridade:** {'⭐ Premium' if denuncia['e_premium'] else '📋 Normal'}",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Importante",
                value="• Clique em **Atender** para analisar\n"
                      "• Clique em **Dispensar** se não puder analisar\n"
                      "• Você tem 5 minutos para votar após atender",
                inline=False
            )
            
            view = ReportView(denuncia['hash_denuncia'])
            await user.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Erro ao enviar denúncia para guardião {guardian_id}: {e}")
    
    @tasks.loop(minutes=5)
    async def inactivity_check(self):
        """Verifica guardiões inativos e aplica penalidades"""
        try:
            if not db_manager.pool:
                return
            
            # Busca guardiões que receberam denúncias mas não votaram
            # Esta lógica seria mais complexa em um sistema real
            # Por simplicidade, verificamos apenas cooldowns
            
            logger.debug("Verificação de inatividade executada")
            
        except Exception as e:
            logger.error(f"Erro na verificação de inatividade: {e}")
    
    @distribution_loop.before_loop
    async def before_distribution_loop(self):
        """Aguarda o bot estar pronto antes de iniciar o loop"""
        await self.bot.wait_until_ready()
    
    @inactivity_check.before_loop
    async def before_inactivity_check(self):
        """Aguarda o bot estar pronto antes de iniciar o loop"""
        await self.bot.wait_until_ready()


async def setup(bot):
    """Função para carregar o cog"""
    await bot.add_cog(ModeracaoCog(bot))
