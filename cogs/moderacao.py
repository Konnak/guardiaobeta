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
from datetime import datetime, timedelta, timezone
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
            
            # Atualiza o status da mensagem para "Atendida" (se a tabela existir)
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mensagens_guardioes'
                )
            """
            table_exists = db_manager.execute_scalar_sync(table_exists_query)
            
            if table_exists:
                update_msg_query = """
                    UPDATE mensagens_guardioes 
                    SET status = 'Atendida' 
                    WHERE id_guardiao = $1 AND id_denuncia = (
                        SELECT id FROM denuncias WHERE hash_denuncia = $2
                    ) AND status = 'Enviada'
                """
                db_manager.execute_command_sync(update_msg_query, interaction.user.id, self.hash_denuncia)
            else:
                # Remove do cache temporário quando atende
                denuncia_id_query = "SELECT id FROM denuncias WHERE hash_denuncia = $1"
                denuncia_id = db_manager.execute_scalar_sync(denuncia_id_query, self.hash_denuncia)
                
                # Acessa o cog para limpar o cache
                from main import bot
                moderacao_cog = bot.get_cog('ModeracaoCog')
                if moderacao_cog and denuncia_id:
                    # Remove do cache de tracking (para não tentar deletar depois)
                    if denuncia_id in moderacao_cog.temp_message_tracking:
                        moderacao_cog.temp_message_tracking[denuncia_id].pop(interaction.user.id, None)
                        if not moderacao_cog.temp_message_tracking[denuncia_id]:
                            moderacao_cog.temp_message_tracking.pop(denuncia_id, None)
            
            # Verifica se ainda há vagas para esta denúncia (considerando peso dos moderadores)
            weighted_count_query = """
                SELECT COALESCE(SUM(CASE WHEN u.categoria = 'Moderador' THEN 5 ELSE 1 END), 0) as peso_total
                FROM votos_guardioes vg
                JOIN usuarios u ON vg.id_guardiao = u.id_discord
                WHERE vg.id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $1)
            """
            weighted_count = db_manager.execute_scalar_sync(weighted_count_query, self.hash_denuncia)
            logger.info(f"Peso total de votos para denúncia {self.hash_denuncia}: {weighted_count}")
            
            if weighted_count >= REQUIRED_VOTES_FOR_DECISION:
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
            
            if not denuncia:
                # Fallback: busca sem JOINs
                simple_query = "SELECT * FROM denuncias WHERE hash_denuncia = $1"
                simple_denuncia = db_manager.execute_one_sync(simple_query, self.hash_denuncia)
                
                if simple_denuncia:
                    denuncia = simple_denuncia.copy()
                    denuncia['denunciante_name'] = f'Usuário {simple_denuncia["id_denunciante"]}'
                    denuncia['denunciado_name'] = f'Usuário {simple_denuncia["id_denunciado"]}'
                else:
                    await interaction.response.send_message("Denúncia não encontrada.", ephemeral=True)
                    return
            
            # Busca as mensagens capturadas
            mensagens_query = """
                SELECT * FROM mensagens_capturadas 
                WHERE id_denuncia = $1 
                ORDER BY timestamp_mensagem DESC
            """
            mensagens = db_manager.execute_query_sync(mensagens_query, denuncia['id'])
            
            # Cria o embed com os detalhes da denúncia
            embed = discord.Embed(
                title="🚨 Nova Ocorrência - Análise Requerida",
                description="Analise cuidadosamente as evidências antes de votar.",
                color=0xff6600
            )
            
            # Converte data da denúncia para horário de Brasília
            data_brasilia = denuncia['data_criacao'] - timedelta(hours=3)
            embed.add_field(
                name="📋 Informações da Denúncia",
                value=f"**Hash:** `{self.hash_denuncia}`\n"
                      f"**Motivo:** {denuncia['motivo']}\n"
                      f"**Data:** {data_brasilia.strftime('%d/%m/%Y às %H:%M')}",
                inline=False
            )
            
            # Adiciona as mensagens capturadas (anonimizadas)
            if mensagens:
                mensagens_anonimizadas = self._anonymize_messages(mensagens, denuncia['id_denunciado'])
                
                # Divide em chunks para não exceder limite do Discord
                chunks = self._split_into_chunks(mensagens_anonimizadas, 1000)
                
                for i, chunk in enumerate(chunks):
                    field_name = f"💬 Mensagens Capturadas" if i == 0 else f"💬 Mensagens (cont. {i+1})"
                    embed.add_field(name=field_name, value=chunk, inline=False)
            else:
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
            
        except Exception as e:
            logger.error(f"Erro ao atender denúncia: {e}")
            await interaction.response.send_message("Erro ao processar atendimento.", ephemeral=True)
    
    async def _handle_dispensar(self, interaction: discord.Interaction):
        """Processa a dispensa de uma denúncia"""
        try:
            # Atualiza o status da mensagem para "Dispensada" (se a tabela existir)
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mensagens_guardioes'
                )
            """
            table_exists = db_manager.execute_scalar_sync(table_exists_query)
            
            if table_exists:
                update_msg_query = """
                    UPDATE mensagens_guardioes 
                    SET status = 'Dispensada' 
                    WHERE id_guardiao = $1 AND id_denuncia = (
                        SELECT id FROM denuncias WHERE hash_denuncia = $2
                    ) AND status = 'Enviada'
                """
                db_manager.execute_command_sync(update_msg_query, interaction.user.id, self.hash_denuncia)
            else:
                # Remove do cache temporário quando dispensa
                denuncia_id_query = "SELECT id FROM denuncias WHERE hash_denuncia = $1"
                denuncia_id = db_manager.execute_scalar_sync(denuncia_id_query, self.hash_denuncia)
                
                # Acessa o cog para limpar o cache
                from main import bot
                moderacao_cog = bot.get_cog('ModeracaoCog')
                if moderacao_cog and denuncia_id:
                    # Remove do cache de tracking (para não tentar deletar depois)
                    if denuncia_id in moderacao_cog.temp_message_tracking:
                        moderacao_cog.temp_message_tracking[denuncia_id].pop(interaction.user.id, None)
                        if not moderacao_cog.temp_message_tracking[denuncia_id]:
                            moderacao_cog.temp_message_tracking.pop(denuncia_id, None)
            
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
        try:
            if not mensagens:
                return "Nenhuma mensagem encontrada."
            
            # Mapeia usuários únicos para nomes anônimos
            usuarios_unicos = {}
            contador_usuario = 1
            
            for msg in mensagens:
                if msg['id_autor'] not in usuarios_unicos:
                    if msg['id_autor'] == id_denunciado:
                        usuarios_unicos[msg['id_autor']] = "**🔴 Denunciado**"
                    else:
                        usuarios_unicos[msg['id_autor']] = f"**Usuário {contador_usuario}**"
                        contador_usuario += 1
            
            result = []
            for msg in mensagens[:15]:  # Limita a 15 mensagens
                # Converte para horário de Brasília
                timestamp_brasilia = msg['timestamp_mensagem'] - timedelta(hours=3)
                timestamp_formatado = timestamp_brasilia.strftime('%H:%M')
                
                autor = usuarios_unicos[msg['id_autor']]
                conteudo = msg['conteudo'][:150] + "..." if len(msg['conteudo']) > 150 else msg['conteudo']
                
                # Remove menções para anonimização
                conteudo = re.sub(r'<@!?\d+>', '[Usuário]', conteudo)
                
                if msg['id_autor'] == id_denunciado:
                    linha = f"🔴 **{autor}** ({timestamp_formatado}): **{conteudo}**"
                else:
                    linha = f"{autor} ({timestamp_formatado}): {conteudo}"
                
                result.append(linha)
            
            return "\n\n".join(result)
                
        except Exception as e:
            logger.error(f"Erro ao anonimizar mensagens: {e}")
            return "Erro ao processar mensagens."
    
    def _split_into_chunks(self, text: str, max_length: int) -> List[str]:
        """Divide o texto em chunks para não exceder o limite do Discord"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        lines = text.split('\n\n')
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk + line + "\n\n") > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + "\n\n"
            else:
                current_chunk += line + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


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
            
            # Remove do cache temporário se existir
            denuncia_id_query = "SELECT id FROM denuncias WHERE hash_denuncia = $1"
            denuncia_id = db_manager.execute_scalar_sync(denuncia_id_query, self.hash_denuncia)
            
            # Acessa o cog para limpar o cache
            from main import bot
            moderacao_cog = bot.get_cog('ModeracaoCog')
            if moderacao_cog and denuncia_id in moderacao_cog.temp_message_cache:
                moderacao_cog.temp_message_cache[denuncia_id].pop(self.guardiao_id, None)
                if not moderacao_cog.temp_message_cache[denuncia_id]:
                    moderacao_cog.temp_message_cache.pop(denuncia_id, None)
            
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
            # Conta os votos com peso (moderador = 5, guardião = 1)
            weighted_votes_query = """
                SELECT SUM(CASE WHEN u.categoria = 'Moderador' THEN 5 ELSE 1 END) as peso_total
                FROM votos_guardioes vg
                JOIN usuarios u ON vg.id_guardiao = u.id_discord
                WHERE vg.id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $1)
            """
            total_weighted_votes = db_manager.execute_scalar_sync(weighted_votes_query, self.hash_denuncia) or 0
            
            if total_weighted_votes >= REQUIRED_VOTES_FOR_DECISION:
                await self._finalize_denuncia()
                
        except Exception as e:
            logger.error(f"Erro ao verificar conclusão da denúncia: {e}")
    
    async def _finalize_denuncia(self):
        """Finaliza a denúncia e aplica a punição"""
        try:
            # Busca todos os votos com categoria do votante
            votes_query = """
                SELECT vg.voto, u.categoria 
                FROM votos_guardioes vg
                JOIN usuarios u ON vg.id_guardiao = u.id_discord
                WHERE vg.id_denuncia = (SELECT id FROM denuncias WHERE hash_denuncia = $1)
            """
            votes = db_manager.execute_query_sync(votes_query, self.hash_denuncia)
            
            # Conta os votos com peso especial para moderadores
            vote_counts = {"OK!": 0, "Intimidou": 0, "Grave": 0}
            for vote in votes:
                peso = 5 if vote['categoria'] == 'Moderador' else 1
                vote_counts[vote['voto']] += peso
                if peso > 1:
                    logger.info(f"Voto de moderador aplicado com peso {peso}: {vote['voto']}")
            
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
            if result['punishment']:
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
        
        # 4+ "Grave": Ban de 24 horas
        if grave_votes >= 4:
            return {
                "type": "Grave", 
                "punishment": True, 
                "duration": PUNISHMENT_RULES['grave_4_plus'] * 3600,
                "is_ban": True
            }
        
        # 3 "Grave": Mute de 12 horas
        if grave_votes >= 3:
            return {
                "type": "Grave", 
                "punishment": True, 
                "duration": PUNISHMENT_RULES['grave_3'] * 3600
            }
        
        # 3 "Intimidou" + 2 "Grave": Mute de 6 horas
        if intimidou_votes >= 3 and grave_votes >= 2:
            return {
                "type": "Intimidou + Grave", 
                "punishment": True, 
                "duration": PUNISHMENT_RULES['intimidou_grave'] * 3600
            }
        
        # 3 "Intimidou": Mute de 1 hora
        if intimidou_votes >= 3:
            return {
                "type": "Intimidou", 
                "punishment": True, 
                "duration": PUNISHMENT_RULES['intimidou_3'] * 3600
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
            
            # Busca o servidor através do bot
            from main import bot  # Import local para evitar circular
            server_id = int(denuncia['id_servidor'])  # Converte para inteiro
            
            # SOLUÇÃO DEFINITIVA: Aguarda bot estar completamente pronto
            if not bot.is_ready():
                logger.info("Aguardando bot estar pronto...")
                await bot.wait_until_ready()
            
            # Aguarda um pouco mais para garantir sincronização completa
            await asyncio.sleep(2)
            
            # Verifica se o bot está realmente pronto
            if not bot.is_ready() or bot.user is None:
                logger.warning("Bot ainda não está pronto após aguardar. Tentando novamente...")
                await asyncio.sleep(5)  # Aguarda mais 5 segundos
                
                if not bot.is_ready() or bot.user is None:
                    logger.error("Bot não está pronto após múltiplas tentativas. Cancelando punição.")
                    return
            
            # Tenta buscar o servidor com fallback
            guild = bot.get_guild(server_id)
            if not guild:
                # Se não encontrou no cache, tenta buscar via fetch
                try:
                    guild = await bot.fetch_guild(server_id)
                    logger.info(f"Servidor {server_id} encontrado via fetch")
                except Exception as fetch_error:
                    logger.warning(f"Servidor {server_id} não encontrado via fetch: {fetch_error}")
                    # Lista servidores disponíveis para debug
                    available_guilds = [g.id for g in bot.guilds]
                    logger.info(f"Servidores disponíveis: {available_guilds}")
                    return
            
            # Busca o membro
            member_id = int(denuncia['id_denunciado'])  # Converte para inteiro
            member = guild.get_member(member_id)
            if not member:
                # Se não encontrou no cache, tenta buscar via fetch
                try:
                    member = await guild.fetch_member(member_id)
                    logger.info(f"Membro {member_id} encontrado via fetch")
                except Exception as fetch_error:
                    logger.warning(f"Membro {member_id} não encontrado no servidor: {fetch_error}")
                    # Lista membros disponíveis para debug
                    available_members = [m.id for m in guild.members[:10]]  # Primeiros 10 para não sobrecarregar
                    logger.info(f"Alguns membros disponíveis: {available_members}")
                    return
            
            # Aplica a punição
            duration_delta = timedelta(seconds=result['duration'])
            
            if result.get('is_ban'):
                # Para bans temporários, usa timeout longo (Discord não tem ban temporário nativo)
                await member.timeout(duration_delta, reason=f"Punição automática - {result['type']}")
                logger.info(f"Ban (timeout) aplicado para {member.display_name} por {result['duration']} segundos")
                punishment_action = "🔨 Banimento Temporário"
            else:
                # Timeout normal
                await member.timeout(duration_delta, reason=f"Punição automática - {result['type']}")
                logger.info(f"Timeout aplicado para {member.display_name} por {result['duration']} segundos")
                punishment_action = "⏰ Timeout"
            
            # Enviar log para o canal configurado
            await self._send_punishment_log(guild, member, result, punishment_action)
            
        except Exception as e:
            logger.error(f"Erro ao aplicar punição: {e}")
    
    async def _send_punishment_log(self, guild: discord.Guild, member: discord.Member, result: Dict, action: str):
        """Envia log da punição para o canal configurado"""
        try:
            # Buscar canal de log configurado
            config_query = """
                SELECT canal_log FROM configuracoes_servidor 
                WHERE id_servidor = $1
            """
            config = db_manager.execute_one_sync(config_query, guild.id)
            
            if not config or not config['canal_log']:
                logger.debug(f"Nenhum canal de log configurado para servidor {guild.id}")
                return
            
            # Buscar o canal
            log_channel_id = int(config['canal_log'])
            log_channel = guild.get_channel(log_channel_id)
            
            if not log_channel:
                logger.warning(f"Canal de log {log_channel_id} não encontrado no servidor {guild.id}")
                return
            
            # Criar embed de log
            embed = discord.Embed(
                title="🛡️ Sistema Guardião - Punição Aplicada",
                color=0xff6b35,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="👤 Usuário Punido",
                value=f"{member.mention} ({member.display_name})\n`ID: {member.id}`",
                inline=True
            )
            
            embed.add_field(
                name="⚖️ Punição",
                value=f"{action}\n**Tipo:** {result['type']}\n**Duração:** {result['duration'] // 3600}h",
                inline=True
            )
            
            embed.add_field(
                name="📋 Detalhes",
                value=f"**Hash:** `{self.hash_denuncia}`\n**Sistema:** Moderação Comunitária",
                inline=False
            )
            
            embed.set_footer(text="Sistema Guardião BETA", icon_url=guild.icon.url if guild.icon else None)
            
            # Enviar para o canal de log
            await log_channel.send(embed=embed)
            logger.info(f"Log de punição enviado para canal {log_channel.name} no servidor {guild.name}")
            
        except Exception as e:
            logger.error(f"Erro ao enviar log de punição: {e}")
    
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
                from main import bot  # Import local para evitar circular
                user_id = int(denuncia['id_denunciado'])  # Converte para inteiro
                user = bot.get_user(user_id)
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
        # Cache temporário para controlar spam quando tabela não existe
        self.temp_message_cache = {}  # {denuncia_id: {guardiao_id: timestamp}}
        # Cache para rastrear mensagens enviadas e seus IDs para timeout
        self.temp_message_tracking = {}  # {denuncia_id: {guardiao_id: {'message_id': int, 'timestamp': datetime, 'user_id': int}}}
        self.distribution_loop.start()
        self.timeout_check.start()
        self.inactivity_check.start()
    
    async def _should_include_moderators(self, denuncia: dict) -> dict:
        """Verifica se deve incluir moderadores na distribuição"""
        try:
            # Verifica se a denúncia está pendente há mais de 15 minutos
            current_time = datetime.utcnow()
            denuncia_time = denuncia['data_criacao']
            
            # Se data_criacao é timezone-aware, converte para UTC naive
            if hasattr(denuncia_time, 'tzinfo') and denuncia_time.tzinfo is not None:
                denuncia_time = denuncia_time.replace(tzinfo=None)
            
            time_diff = current_time - denuncia_time
            
            # Denúncia pendente há mais de 15 minutos
            if time_diff.total_seconds() > 15 * 60:  # 15 minutos
                return {
                    'include': True,
                    'reason': f'Denúncia pendente há {int(time_diff.total_seconds() // 60)} minutos'
                }
            
            # Denúncia premium sem guardiões suficientes
            if denuncia.get('e_premium', False):
                guardians_count = db_manager.execute_scalar_sync(
                    "SELECT COUNT(*) FROM usuarios WHERE em_servico = TRUE AND categoria = 'Guardião'"
                )
                if guardians_count < 2:  # Menos de 2 guardiões disponíveis
                    return {
                        'include': True,
                        'reason': f'Denúncia premium com apenas {guardians_count} guardiões disponíveis'
                    }
            
            return {'include': False, 'reason': 'Condições não atendidas'}
            
        except Exception as e:
            logger.error(f"Erro ao verificar se deve incluir moderadores: {e}")
            return {'include': False, 'reason': 'Erro na verificação'}
    
    async def _get_available_moderators(self, denuncia_id: int, limit: int) -> list:
        """Busca moderadores disponíveis para a denúncia"""
        try:
            moderators_query = """
                SELECT id_discord, categoria FROM usuarios 
                WHERE em_servico = TRUE 
                AND categoria = 'Moderador'
                AND (cooldown_dispensa IS NULL OR cooldown_dispensa <= NOW())
                AND (cooldown_inativo IS NULL OR cooldown_inativo <= NOW())
                AND id_discord NOT IN (
                    SELECT id_guardiao FROM votos_guardioes 
                    WHERE id_denuncia = $1
                )
                AND id_discord NOT IN (
                    SELECT id_guardiao FROM mensagens_guardioes 
                    WHERE id_denuncia = $1 AND status = 'Enviada' AND timeout_expira > NOW()
                )
                ORDER BY RANDOM()
                LIMIT $2
            """
            moderators = db_manager.execute_query_sync(moderators_query, denuncia_id, limit)
            logger.info(f"Encontrados {len(moderators)} moderadores disponíveis para denúncia {denuncia_id}")
            return moderators
            
        except Exception as e:
            logger.error(f"Erro ao buscar moderadores disponíveis: {e}")
            return []

    async def _check_denuncias_limits(self, server_id: int, is_premium: bool) -> dict:
        """Verifica se o servidor pode criar mais denúncias baseado nos limites do plano"""
        try:
            # Limites baseados no plano
            if is_premium:
                max_pendentes = 15
                max_analise = 10
            else:
                max_pendentes = 5
                max_analise = 5
            
            # Conta denúncias atuais
            count_query = """
                SELECT 
                    COUNT(CASE WHEN status = 'Pendente' THEN 1 END) as pendentes,
                    COUNT(CASE WHEN status = 'Em Análise' THEN 1 END) as analise
                FROM denuncias 
                WHERE id_servidor = $1 AND status IN ('Pendente', 'Em Análise')
            """
            counts = db_manager.execute_one_sync(count_query, server_id)
            
            if not counts:
                return {'allowed': True, 'message': ''}
            
            pendentes = counts.get('pendentes', 0)
            analise = counts.get('analise', 0)
            
            # Verifica limites
            if pendentes >= max_pendentes:
                plano = "Premium" if is_premium else "Gratuito"
                return {
                    'allowed': False,
                    'message': f"Limite de denúncias pendentes atingido!\n\n"
                              f"**Plano {plano}:** {pendentes}/{max_pendentes} pendentes\n"
                              f"Aguarde algumas denúncias serem processadas."
                }
            
            if analise >= max_analise:
                plano = "Premium" if is_premium else "Gratuito"
                return {
                    'allowed': False,
                    'message': f"Limite de denúncias em análise atingido!\n\n"
                              f"**Plano {plano}:** {analise}/{max_analise} em análise\n"
                              f"Aguarde algumas denúncias serem finalizadas."
                }
            
            return {'allowed': True, 'message': ''}
            
        except Exception as e:
            logger.error(f"Erro ao verificar limites de denúncias: {e}")
            return {'allowed': True, 'message': ''}  # Em caso de erro, permite a denúncia
    
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
            # Verifica se o banco de dados está disponível
            if not db_manager.pool:
                db_manager.initialize_pool()
            
            # Verifica se o usuário está cadastrado
            user_data = await get_user_by_discord_id(interaction.user.id)
            if not user_data:
                embed = discord.Embed(
                    title="❌ Usuário Não Cadastrado",
                    description="Você precisa se cadastrar primeiro usando `/cadastro`!",
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
            
            # Verifica limites de denúncias baseado no plano
            limits_check = await self._check_denuncias_limits(interaction.guild.id, is_premium)
            if not limits_check['allowed']:
                embed = discord.Embed(
                    title="⚠️ Limite de Denúncias Atingido",
                    description=limits_check['message'],
                    color=0xffa500
                )
                if not is_premium:
                    embed.add_field(
                        name="💎 Upgrade para Premium",
                        value="Tenha mais denúncias simultâneas com o plano Premium!\n"
                              "• **15** denúncias pendentes\n"
                              "• **10** denúncias em análise\n"
                              "• Prioridade na análise",
                        inline=False
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
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
            
            # Resposta imediata
            embed_loading = discord.Embed(
                title="🔄 Processando Denúncia...",
                description=f"Capturando mensagens e criando denúncia...\n\n**Denunciado:** {usuario.display_name}\n**Motivo:** {motivo}",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed_loading, ephemeral=True)
            
            # Captura mensagens do histórico
            await self._capture_messages(interaction, usuario, denuncia_id)
            
            # Conta guardiões em serviço
            guardians_query = """
                SELECT COUNT(*) FROM usuarios 
                WHERE em_servico = TRUE AND categoria = 'Guardião'
            """
            guardians_count = db_manager.execute_scalar_sync(guardians_query)
            
            # Resposta de confirmação final
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
            
            await interaction.edit_original_response(embed=embed)
            
        except Exception as e:
            logger.error(f"Erro no comando report: {e}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _capture_messages(self, interaction: discord.Interaction, target_user: discord.Member, denuncia_id: int):
        """Captura mensagens do histórico do canal"""
        try:
            messages_captured = 0
            
            # Busca mensagens das últimas 24 horas
            now_utc = datetime.now(timezone.utc)
            cutoff_time = now_utc - timedelta(hours=24)
            
            # Coleta mensagens
            messages = []
            async for message in interaction.channel.history(limit=100, after=cutoff_time):
                messages.append(message)
            
            # Ordena do mais recente ao mais antigo
            messages.reverse()
            
            # Processa as mensagens encontradas
            for message in messages:
                # Prepara URLs dos anexos
                attachment_urls = [attachment.url for attachment in message.attachments]
                
                # Insere a mensagem no banco
                mensagem_query = """
                    INSERT INTO mensagens_capturadas (
                        id_denuncia, id_autor, conteudo, anexos_urls, timestamp_mensagem
                    ) VALUES ($1, $2, $3, $4, $5)
                """
                db_manager.execute_command_sync(
                    mensagem_query, denuncia_id, message.author.id, 
                    message.content, ",".join(attachment_urls), message.created_at.replace(tzinfo=None)
                )
                
                messages_captured += 1
            
            logger.info(f"Capturadas {messages_captured} mensagens para denúncia {denuncia_id}")
            
        except Exception as e:
            logger.error(f"Erro ao capturar mensagens: {e}")
    
    @tasks.loop(seconds=30)
    async def distribution_loop(self):
        """Loop que distribui denúncias para Guardiões em serviço"""
        try:
            if not db_manager.pool:
                return
            
            # Verifica quantos guardiões estão em serviço
            guardians_count_query = "SELECT COUNT(*) FROM usuarios WHERE em_servico = TRUE AND categoria = 'Guardião'"
            total_guardians = db_manager.execute_scalar_sync(guardians_count_query)
            logger.debug(f"Total de guardiões em serviço: {total_guardians}")
            
            if total_guardians == 0:
                logger.warning("Nenhum guardião está em serviço!")
                # Se não há guardiões, verifica se há moderadores em serviço
                moderators_count_query = "SELECT COUNT(*) FROM usuarios WHERE em_servico = TRUE AND categoria = 'Moderador'"
                total_moderators = db_manager.execute_scalar_sync(moderators_count_query)
                logger.info(f"Total de moderadores em serviço: {total_moderators}")
                
                if total_moderators == 0:
                    logger.warning("Nenhum guardião ou moderador está em serviço!")
                    return
                else:
                    logger.info("Nenhum guardião em serviço, mas há moderadores disponíveis. Continuando distribuição...")
            
            # Verifica se a tabela mensagens_guardioes existe
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mensagens_guardioes'
                )
            """
            table_exists = db_manager.execute_scalar_sync(table_exists_query)
            
            if table_exists:
                # Versão completa com rastreamento de mensagens
                denuncias_query = """
                    SELECT d.*, 
                           COALESCE(v.votos_count, 0) as votos_atuais,
                           COALESCE(m.mensagens_ativas, 0) as mensagens_ativas
                    FROM denuncias d
                    LEFT JOIN (
                        SELECT id_denuncia, COUNT(*) as votos_count 
                        FROM votos_guardioes 
                        GROUP BY id_denuncia
                    ) v ON d.id = v.id_denuncia
                    LEFT JOIN (
                        SELECT id_denuncia, COUNT(*) as mensagens_ativas 
                        FROM mensagens_guardioes 
                        WHERE status = 'Enviada' AND timeout_expira > NOW()
                        GROUP BY id_denuncia
                    ) m ON d.id = m.id_denuncia
                    WHERE d.status IN ('Pendente', 'Em Análise', 'Apelada')
                      AND COALESCE(v.votos_count, 0) < $1
                      AND COALESCE(m.mensagens_ativas, 0) < $2
                    ORDER BY d.e_premium DESC, d.data_criacao ASC
                    LIMIT 1
                """
                denuncia = db_manager.execute_one_sync(
                    denuncias_query, REQUIRED_VOTES_FOR_DECISION, MAX_GUARDIANS_PER_REPORT
                )
            else:
                # Versão simplificada sem rastreamento de mensagens
                logger.warning("Tabela mensagens_guardioes não existe. Execute a migração: database/migrate_add_mensagens_guardioes.sql")
                denuncias_query = """
                    SELECT d.*, COALESCE(v.votos_count, 0) as votos_atuais
                    FROM denuncias d
                    LEFT JOIN (
                        SELECT id_denuncia, COUNT(*) as votos_count 
                        FROM votos_guardioes 
                        GROUP BY id_denuncia
                    ) v ON d.id = v.id_denuncia
                    WHERE d.status IN ('Pendente', 'Em Análise', 'Apelada')
                      AND COALESCE(v.votos_count, 0) < $1
                    ORDER BY d.e_premium DESC, d.data_criacao ASC
                    LIMIT 1
                """
                denuncia = db_manager.execute_one_sync(denuncias_query, REQUIRED_VOTES_FOR_DECISION)
                if denuncia:
                    denuncia['mensagens_ativas'] = 0  # Assume 0 mensagens ativas
            
            if not denuncia:
                logger.debug("Nenhuma denúncia encontrada para distribuição")
                return
            
            # Calcula quantos guardiões ainda precisamos
            votos_necessarios = REQUIRED_VOTES_FOR_DECISION - denuncia['votos_atuais']
            mensagens_necessarias = min(votos_necessarios, MAX_GUARDIANS_PER_REPORT - denuncia['mensagens_ativas'])
            
            logger.info(f"Denúncia {denuncia['hash_denuncia']}: {denuncia['votos_atuais']}/{REQUIRED_VOTES_FOR_DECISION} votos, "
                       f"{denuncia['mensagens_ativas']} mensagens ativas, precisa de {mensagens_necessarias} guardiões")
            
            if mensagens_necessarias <= 0:
                logger.debug(f"Denúncia {denuncia['hash_denuncia']} não precisa de mais guardiões")
                return
            
            # Busca guardiões disponíveis (prioridade para guardiões)
            if table_exists:
                guardians_query = """
                    SELECT id_discord, categoria FROM usuarios 
                    WHERE em_servico = TRUE 
                    AND categoria = 'Guardião'
                    AND (cooldown_dispensa IS NULL OR cooldown_dispensa <= NOW())
                    AND (cooldown_inativo IS NULL OR cooldown_inativo <= NOW())
                    AND id_discord NOT IN (
                        SELECT id_guardiao FROM votos_guardioes 
                        WHERE id_denuncia = $1
                    )
                    AND id_discord NOT IN (
                        SELECT id_guardiao FROM mensagens_guardioes 
                        WHERE id_denuncia = $1 AND status = 'Enviada' AND timeout_expira > NOW()
                    )
                    ORDER BY RANDOM()
                    LIMIT $2
                """
                guardians = db_manager.execute_query_sync(guardians_query, denuncia['id'], mensagens_necessarias)
                
                # Se não há guardiões suficientes, verifica se deve incluir moderadores
                if len(guardians) < mensagens_necessarias:
                    should_include_moderators = await self._should_include_moderators(denuncia)
                    if should_include_moderators['include']:
                        logger.info(f"Incluindo moderadores para denúncia {denuncia['hash_denuncia']} - {should_include_moderators['reason']}")
                        moderators = await self._get_available_moderators(denuncia['id'], mensagens_necessarias - len(guardians))
                        guardians.extend(moderators)
                
                # NOVA FUNCIONALIDADE: Se não há guardiões em serviço, busca apenas moderadores
                if total_guardians == 0 and len(guardians) == 0:
                    logger.info("Nenhum guardião em serviço, buscando apenas moderadores...")
                    moderators_query = """
                        SELECT id_discord, categoria FROM usuarios 
                        WHERE em_servico = TRUE 
                        AND categoria = 'Moderador'
                        AND (cooldown_dispensa IS NULL OR cooldown_dispensa <= NOW())
                        AND (cooldown_inativo IS NULL OR cooldown_inativo <= NOW())
                        AND id_discord NOT IN (
                            SELECT id_guardiao FROM votos_guardioes 
                            WHERE id_denuncia = $1
                        )
                        AND id_discord NOT IN (
                            SELECT id_guardiao FROM mensagens_guardioes 
                            WHERE id_denuncia = $1 AND status = 'Enviada' AND timeout_expira > NOW()
                        )
                        ORDER BY RANDOM()
                        LIMIT $2
                    """
                    guardians = db_manager.execute_query_sync(moderators_query, denuncia['id'], mensagens_necessarias)
                    logger.info(f"Encontrados {len(guardians)} moderadores para denúncia {denuncia['hash_denuncia']}")
            else:
                # Versão simplificada usando cache temporário para evitar spam
                if total_guardians == 0:
                    # Se não há guardiões, busca apenas moderadores
                    logger.info("Nenhum guardião em serviço, buscando apenas moderadores (versão simplificada)...")
                    guardians_query = """
                    SELECT id_discord FROM usuarios 
                    WHERE em_servico = TRUE 
                    AND categoria = 'Moderador'
                    AND (cooldown_dispensa IS NULL OR cooldown_dispensa <= NOW())
                    AND (cooldown_inativo IS NULL OR cooldown_inativo <= NOW())
                    AND id_discord NOT IN (
                        SELECT id_guardiao FROM votos_guardioes 
                        WHERE id_denuncia = $1
                    )
                    ORDER BY RANDOM()
                    LIMIT $2
                """
                else:
                    # Busca guardiões normalmente
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
                all_guardians = db_manager.execute_query_sync(guardians_query, denuncia['id'], MAX_GUARDIANS_PER_REPORT)
                
                # Filtra guardiões que NÃO têm mensagens ativas (não reenvia para o mesmo guardião)
                guardians = []
                current_time = datetime.utcnow()
                denuncia_tracking = self.temp_message_tracking.get(denuncia['id'], {})
                
                for guardian_data in all_guardians:
                    guardian_id = guardian_data['id_discord']
                    
                    # Verifica se o guardião tem mensagem ativa (não expirada)
                    has_active_message = False
                    if guardian_id in denuncia_tracking:
                        msg_data = denuncia_tracking[guardian_id]
                        time_diff = (current_time - msg_data['timestamp']).total_seconds()
                        if time_diff <= 300:  # Mensagem ainda ativa (menos de 5 minutos)
                            has_active_message = True
                    
                    # Só adiciona se NÃO tem mensagem ativa
                    if not has_active_message:
                        guardians.append(guardian_data)
                        logger.debug(f"Guardião {guardian_id} disponível para denúncia {denuncia['hash_denuncia']}")
                    else:
                        logger.debug(f"Guardião {guardian_id} já tem mensagem ativa para denúncia {denuncia['hash_denuncia']}")
                    
                    if len(guardians) >= mensagens_necessarias:
                        break
            
            logger.info(f"Encontrados {len(guardians) if guardians else 0} guardiões disponíveis para denúncia {denuncia['hash_denuncia']}")
            
            if not guardians:
                logger.warning(f"Nenhum guardião disponível para denúncia {denuncia['hash_denuncia']}")
                return
            
            # Muda o status para "Em Análise" se ainda estiver pendente
            if denuncia['status'] == 'Pendente':
                update_query = "UPDATE denuncias SET status = 'Em Análise' WHERE id = $1"
                db_manager.execute_command_sync(update_query, denuncia['id'])
                logger.info(f"Status da denúncia {denuncia['hash_denuncia']} alterado para 'Em Análise'")
            
            # Envia para cada guardião
            for guardian_data in guardians:
                await self._send_to_guardian(guardian_data['id_discord'], denuncia)
            
            logger.info(f"Denúncia {denuncia['hash_denuncia']} enviada para {len(guardians)} guardiões adicionais")
            
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
                      "• Você tem 5 minutos para votar após atender\n"
                      "• A mensagem será removida em 5 minutos se não atendida",
                inline=False
            )
            
            view = ReportView(denuncia['hash_denuncia'])
            message = await user.send(embed=embed, view=view)
            
            # Registra a mensagem enviada (se a tabela existir)
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mensagens_guardioes'
                )
            """
            table_exists = db_manager.execute_scalar_sync(table_exists_query)
            
            if table_exists:
                timeout_time = datetime.utcnow() + timedelta(minutes=VOTE_TIMEOUT_MINUTES)
                insert_query = """
                    INSERT INTO mensagens_guardioes (
                        id_denuncia, id_guardiao, id_mensagem, timeout_expira
                    ) VALUES ($1, $2, $3, $4)
                """
                db_manager.execute_command_sync(
                    insert_query, denuncia['id'], guardian_id, message.id, timeout_time
                )
            else:
                # Registra no cache temporário para evitar spam
                current_time = datetime.utcnow()
                if denuncia['id'] not in self.temp_message_cache:
                    self.temp_message_cache[denuncia['id']] = {}
                self.temp_message_cache[denuncia['id']][guardian_id] = current_time
                
                # Registra também no tracking para poder deletar depois (timeout de 5 minutos)
                if denuncia['id'] not in self.temp_message_tracking:
                    self.temp_message_tracking[denuncia['id']] = {}
                self.temp_message_tracking[denuncia['id']][guardian_id] = {
                    'message_id': message.id,
                    'timestamp': current_time,
                    'user_id': guardian_id
                }
            
        except Exception as e:
            logger.error(f"Erro ao enviar denúncia para guardião {guardian_id}: {e}")
    
    async def _process_temp_timeout_messages(self):
        """Processa mensagens que expiraram usando o cache temporário"""
        try:
            if not self.temp_message_tracking:
                return
            
            current_time = datetime.utcnow()
            expired_messages = []
            
            # Busca mensagens que expiraram (5 minutos)
            for denuncia_id, guardians in self.temp_message_tracking.items():
                for guardian_id, msg_data in guardians.items():
                    time_diff = (current_time - msg_data['timestamp']).total_seconds()
                    if time_diff > 300:  # 5 minutos em segundos
                        expired_messages.append({
                            'denuncia_id': denuncia_id,
                            'guardian_id': guardian_id,
                            'message_id': msg_data['message_id'],
                            'user_id': msg_data['user_id']
                        })
            
            # Processa mensagens expiradas
            cleaned_tracking = {}
            cleaned_cache = {}
            
            for msg_data in expired_messages:
                try:
                    # Tenta deletar a mensagem
                    user = self.bot.get_user(msg_data['user_id'])
                    if user:
                        try:
                            channel = user.dm_channel
                            if not channel:
                                channel = await user.create_dm()
                            
                            message = await channel.fetch_message(msg_data['message_id'])
                            await message.delete()
                            logger.info(f"Mensagem {msg_data['message_id']} deletada por timeout (guardião {msg_data['guardian_id']})")
                            
                        except discord.NotFound:
                            pass  # Mensagem já foi deletada
                        except Exception as e:
                            logger.warning(f"Erro ao deletar mensagem {msg_data['message_id']}: {e}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem expirada: {e}")
            
            # Limpa os caches removendo mensagens expiradas
            for denuncia_id, guardians in self.temp_message_tracking.items():
                cleaned_guardians = {}
                for guardian_id, msg_data in guardians.items():
                    time_diff = (current_time - msg_data['timestamp']).total_seconds()
                    if time_diff <= 300:  # Mantém apenas mensagens não expiradas
                        cleaned_guardians[guardian_id] = msg_data
                
                if cleaned_guardians:
                    cleaned_tracking[denuncia_id] = cleaned_guardians
            
            # Limpa também o cache de spam
            for denuncia_id, guardians in self.temp_message_cache.items():
                cleaned_guardians = {}
                for guardian_id, timestamp in guardians.items():
                    time_diff = (current_time - timestamp).total_seconds()
                    if time_diff <= 600:  # Mantém por 10 minutos para evitar spam
                        cleaned_guardians[guardian_id] = timestamp
                
                if cleaned_guardians:
                    cleaned_cache[denuncia_id] = cleaned_guardians
            
            # Atualiza os caches
            self.temp_message_tracking = cleaned_tracking
            self.temp_message_cache = cleaned_cache
            
            if expired_messages:
                logger.info(f"Processadas {len(expired_messages)} mensagens expiradas do cache temporário")
                
                # Força uma nova distribuição após apagar mensagens expiradas
                # para que denúncias sejam redistribuídas imediatamente
                unique_denuncias = set(msg['denuncia_id'] for msg in expired_messages)
                logger.info(f"Forçando redistribuição para {len(unique_denuncias)} denúncias após timeout")
                
        except Exception as e:
            logger.error(f"Erro ao processar timeout de mensagens temporárias: {e}")
    
    @tasks.loop(minutes=1)
    async def timeout_check(self):
        """Verifica mensagens que expiraram e as remove"""
        try:
            if not db_manager.pool:
                return
            
            # Verifica se a tabela mensagens_guardioes existe
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mensagens_guardioes'
                )
            """
            table_exists = db_manager.execute_scalar_sync(table_exists_query)
            
            if not table_exists:
                # Processa mensagens expiradas do cache temporário
                await self._process_temp_timeout_messages()
                return
            
            # Busca mensagens expiradas
            expired_query = """
                SELECT * FROM mensagens_guardioes 
                WHERE status = 'Enviada' AND timeout_expira <= NOW()
            """
            expired_messages = db_manager.execute_query_sync(expired_query)
            
            for msg_data in expired_messages:
                try:
                    # Busca o usuário e a mensagem
                    user = self.bot.get_user(msg_data['id_guardiao'])
                    if user:
                        try:
                            # Tenta buscar e deletar a mensagem
                            channel = user.dm_channel
                            if not channel:
                                channel = await user.create_dm()
                            
                            message = await channel.fetch_message(msg_data['id_mensagem'])
                            await message.delete()
                            
                        except discord.NotFound:
                            pass  # Mensagem já foi deletada
                        except Exception as e:
                            logger.warning(f"Erro ao deletar mensagem {msg_data['id_mensagem']}: {e}")
                    
                    # Atualiza o status da mensagem
                    update_query = """
                        UPDATE mensagens_guardioes 
                        SET status = 'Expirada' 
                        WHERE id = $1
                    """
                    db_manager.execute_command_sync(update_query, msg_data['id'])
                    
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem expirada {msg_data['id']}: {e}")
            
            if expired_messages:
                logger.info(f"Processadas {len(expired_messages)} mensagens expiradas")
            
            # Limpa cache temporário se tabela não existir
            if not table_exists and self.temp_message_cache:
                current_time = datetime.utcnow()
                cleaned_cache = {}
                
                for denuncia_id, guardians in self.temp_message_cache.items():
                    cleaned_guardians = {}
                    for guardian_id, timestamp in guardians.items():
                        # Mantém apenas mensagens dos últimos 10 minutos
                        if (current_time - timestamp).total_seconds() < 600:  # 10 minutos
                            cleaned_guardians[guardian_id] = timestamp
                    
                    if cleaned_guardians:
                        cleaned_cache[denuncia_id] = cleaned_guardians
                
                self.temp_message_cache = cleaned_cache
                
        except Exception as e:
            logger.error(f"Erro na verificação de timeout: {e}")
    
    @tasks.loop(minutes=5)
    async def inactivity_check(self):
        """Verifica guardiões inativos que atenderam mas não votaram"""
        try:
            if not db_manager.pool:
                return
            
            # Verifica se a tabela mensagens_guardioes existe
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mensagens_guardioes'
                )
            """
            table_exists = db_manager.execute_scalar_sync(table_exists_query)
            
            if not table_exists:
                return  # Não faz nada se a tabela não existir
            
            # Busca guardiões que atenderam mas não votaram em 5 minutos
            inactivity_query = """
                SELECT DISTINCT mg.id_guardiao, mg.id_denuncia, d.hash_denuncia
                FROM mensagens_guardioes mg
                JOIN denuncias d ON mg.id_denuncia = d.id
                WHERE mg.status = 'Atendida'
                  AND mg.data_envio <= NOW() - INTERVAL '5 minutes'
                  AND NOT EXISTS (
                      SELECT 1 FROM votos_guardioes vg 
                      WHERE vg.id_guardiao = mg.id_guardiao 
                        AND vg.id_denuncia = mg.id_denuncia
                  )
            """
            inactive_guardians = db_manager.execute_query_sync(inactivity_query)
            
            for guardian_data in inactive_guardians:
                try:
                    # Aplica penalidade de inatividade
                    penalty_time = datetime.utcnow() + timedelta(hours=INACTIVE_PENALTY_HOURS)
                    # Remove pontos e XP correspondente (5 pontos = 10 XP)
                    penalty_query = """
                        UPDATE usuarios 
                        SET pontos = pontos - 5, experiencia = experiencia - 10, cooldown_inativo = $1 
                        WHERE id_discord = $2
                    """
                    db_manager.execute_command_sync(penalty_query, penalty_time, guardian_data['id_guardiao'])
                    
                    # Atualiza status da mensagem
                    update_msg_query = """
                        UPDATE mensagens_guardioes 
                        SET status = 'Inativo' 
                        WHERE id_guardiao = $1 AND id_denuncia = $2 AND status = 'Atendida'
                    """
                    db_manager.execute_command_sync(
                        update_msg_query, guardian_data['id_guardiao'], guardian_data['id_denuncia']
                    )
                    
                    logger.info(f"Penalidade de inatividade aplicada ao guardião {guardian_data['id_guardiao']}")
                    
                except Exception as e:
                    logger.error(f"Erro ao aplicar penalidade de inatividade: {e}")
            
        except Exception as e:
            logger.error(f"Erro na verificação de inatividade: {e}")
    
    @distribution_loop.before_loop
    async def before_distribution_loop(self):
        """Aguarda o bot estar pronto antes de iniciar o loop"""
        await self.bot.wait_until_ready()
    
    @timeout_check.before_loop
    async def before_timeout_check(self):
        """Aguarda o bot estar pronto antes de iniciar o loop"""
        await self.bot.wait_until_ready()
    
    @inactivity_check.before_loop
    async def before_inactivity_check(self):
        """Aguarda o bot estar pronto antes de iniciar o loop"""
        await self.bot.wait_until_ready()


async def setup(bot):
    """Função para carregar o cog"""
    await bot.add_cog(ModeracaoCog(bot))
