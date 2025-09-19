"""
Cog de Guardião - Sistema Guardião BETA
Implementa os comandos /formguardiao e /turno com sistema de treinamento
"""

import discord
from discord.ext import commands, tasks
from discord import ui
import logging
import asyncio
from datetime import datetime, timedelta
from database.connection import db_manager, get_user_by_discord_id_sync
from config import GUARDIAO_MIN_ACCOUNT_AGE_MONTHS, TURN_POINTS_PER_HOUR, PROVA_COOLDOWN_HOURS

# Configuração de logging
logger = logging.getLogger(__name__)


class TrainingView(ui.View):
    """View persistente para o sistema de treinamento"""
    
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=300)  # 5 minutos de timeout
        self.bot = bot
        self.user_id = user_id
        self.current_step = 1
        self.quiz_answers = []
        self.correct_answers = 0
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica se o usuário pode interagir com a view"""
        return interaction.user.id == self.user_id
    
    @ui.button(label="Próximo", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_step(self, button: ui.Button, interaction: discord.Interaction):
        """Botão para avançar no treinamento"""
        await interaction.response.defer()
        
        if self.current_step == 1:
            await self._show_theory_step2(interaction)
        elif self.current_step == 2:
            await self._show_theory_step3(interaction)
        elif self.current_step == 3:
            await self._show_final_exam(interaction)
        else:
            await interaction.followup.send("Treinamento concluído!", ephemeral=True)
    
    @ui.button(label="A", style=discord.ButtonStyle.secondary)
    async def answer_a(self, button: ui.Button, interaction: discord.Interaction):
        await self._handle_quiz_answer(interaction, "A")
    
    @ui.button(label="B", style=discord.ButtonStyle.secondary)
    async def answer_b(self, button: ui.Button, interaction: discord.Interaction):
        await self._handle_quiz_answer(interaction, "B")
    
    @ui.button(label="C", style=discord.ButtonStyle.secondary)
    async def answer_c(self, button: ui.Button, interaction: discord.Interaction):
        await self._handle_quiz_answer(interaction, "C")
    
    @ui.button(label="D", style=discord.ButtonStyle.secondary)
    async def answer_d(self, button: ui.Button, interaction: discord.Interaction):
        await self._handle_quiz_answer(interaction, "D")
    
    async def _show_theory_step2(self, interaction: discord.Interaction):
        """Mostra a segunda etapa do treinamento"""
        self.current_step = 2
        
        embed = discord.Embed(
            title="📚 Etapa 2: Ética na Moderação",
            description="Como Guardião, você deve sempre manter a ética e imparcialidade.",
            color=0x0099ff
        )
        embed.add_field(
            name="📋 Princípios Éticos",
            value="• **Imparcialidade**: Julgue apenas o conteúdo, não a pessoa\n"
                  "• **Confidencialidade**: Nunca revele informações de denúncias\n"
                  "• **Profissionalismo**: Mantenha sempre um tom respeitoso\n"
                  "• **Justiça**: Aplique as regras de forma consistente",
            inline=False
        )
        embed.add_field(
            name="❌ O que NUNCA fazer",
            value="• Vazar informações de denúncias\n"
                  "• Fazer julgamentos pessoais\n"
                  "• Aplicar punições desproporcionais\n"
                  "• Discriminar usuários",
            inline=False
        )
        
        # Quiz da etapa 2
        embed.add_field(
            name="🧠 Quiz de Ética",
            value="**Pergunta:** Um usuário que você conhece pessoalmente foi denunciado. Como proceder?\n\n"
                  "A) Analisar normalmente, mantendo a imparcialidade\n"
                  "B) Ser mais rigoroso por conhecê-lo\n"
                  "C) Ser mais brando por conhecê-lo\n"
                  "D) Recusar-se a analisar",
            inline=False
        )
        
        # Remove o botão "Próximo" e adiciona os botões de resposta
        self.clear_items()
        self.add_item(self.answer_a)
        self.add_item(self.answer_b)
        self.add_item(self.answer_c)
        self.add_item(self.answer_d)
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def _show_theory_step3(self, interaction: discord.Interaction):
        """Mostra a terceira etapa do treinamento"""
        self.current_step = 3
        
        embed = discord.Embed(
            title="🛠️ Etapa 3: Boa e Má Utilização da Ferramenta",
            description="Aprenda a usar corretamente o sistema de moderação.",
            color=0x0099ff
        )
        embed.add_field(
            name="✅ Boa Utilização",
            value="• Analisar todas as evidências antes de votar\n"
                  "• Usar o tempo adequado para cada análise\n"
                  "• Reportar problemas técnicos\n"
                  "• Colaborar com outros Guardiões",
            inline=False
        )
        embed.add_field(
            name="❌ Má Utilização",
            value="• Votar sem analisar adequadamente\n"
                  "• Usar o sistema para vingança pessoal\n"
                  "• Ignorar evidências importantes\n"
                  "• Abandonar denúncias em andamento",
            inline=False
        )
        
        # Quiz da etapa 3
        embed.add_field(
            name="🧠 Quiz de Utilização",
            value="**Pergunta:** Você recebeu uma denúncia complexa. Qual a melhor abordagem?\n\n"
                  "A) Votar rapidamente para não perder tempo\n"
                  "B) Analisar cuidadosamente todas as evidências\n"
                  "C) Pedir para outros Guardiões decidirem\n"
                  "D) Ignorar a denúncia",
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def _show_final_exam(self, interaction: discord.Interaction):
        """Mostra a prova final"""
        self.current_step = 4
        
        embed = discord.Embed(
            title="🎓 Prova Final - Sistema Guardião BETA",
            description="Agora é hora da prova final! Você precisa acertar pelo menos 9 de 10 perguntas.",
            color=0xff6600
        )
        embed.add_field(
            name="📝 Regras da Prova",
            value="• **10 perguntas** sobre todo o conteúdo\n"
                  "• **Mínimo 9 acertos** para aprovação\n"
                  "• **Uma chance** por pergunta\n"
                  "• **Tempo limite**: 15 minutos",
            inline=False
        )
        embed.add_field(
            name="⚠️ Importante",
            value="Se você reprovar, terá que esperar 24 horas para tentar novamente.",
            inline=False
        )
        
        # Remove todos os botões e adiciona botão para começar
        self.clear_items()
        
        @ui.button(label="Começar Prova", style=discord.ButtonStyle.success, emoji="🚀")
        async def start_exam(button: ui.Button, interaction: discord.Interaction):
            await self._start_final_exam(interaction)
        
        self.add_item(start_exam)
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def _start_final_exam(self, interaction: discord.Interaction):
        """Inicia a prova final"""
        # Simulação da prova final (em um sistema real, isso seria mais elaborado)
        questions = [
            {
                "question": "Qual é o princípio mais importante na moderação?",
                "options": ["A) Imparcialidade", "B) Rapidez", "C) Rigor", "D) Popularidade"],
                "correct": "A"
            },
            {
                "question": "Quantos votos são necessários para finalizar uma denúncia?",
                "options": ["A) 3", "B) 5", "C) 7", "D) 10"],
                "correct": "B"
            },
            {
                "question": "O que fazer ao receber uma denúncia de alguém que você conhece?",
                "options": ["A) Ser mais rigoroso", "B) Ser mais brando", "C) Analisar normalmente", "D) Recusar"],
                "correct": "C"
            }
            # Adicione mais perguntas conforme necessário
        ]
        
        self.quiz_questions = questions
        self.current_question = 0
        self.correct_answers = 0
        
        await self._show_question(interaction)
    
    async def _show_question(self, interaction: discord.Interaction):
        """Mostra uma pergunta da prova"""
        if self.current_question >= len(self.quiz_questions):
            await self._finish_exam(interaction)
            return
        
        question = self.quiz_questions[self.current_question]
        
        embed = discord.Embed(
            title=f"🎓 Prova Final - Pergunta {self.current_question + 1}/10",
            description=question["question"],
            color=0xff6600
        )
        embed.add_field(
            name="Opções",
            value="\n".join(question["options"]),
            inline=False
        )
        
        # Remove todos os botões e adiciona os de resposta
        self.clear_items()
        self.add_item(self.answer_a)
        self.add_item(self.answer_b)
        self.add_item(self.answer_c)
        self.add_item(self.answer_d)
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def _handle_quiz_answer(self, interaction: discord.Interaction, answer: str):
        """Processa uma resposta do quiz"""
        if self.current_step == 2:  # Quiz de ética
            correct_answer = "A"
            is_correct = answer == correct_answer
            
            if is_correct:
                embed = discord.Embed(
                    title="✅ Resposta Correta!",
                    description="Perfeito! Você deve sempre manter a imparcialidade, independente de conhecer a pessoa.",
                    color=0x00ff00
                )
                self.current_step = 3
                self.clear_items()
                self.add_item(self.next_step)
            else:
                embed = discord.Embed(
                    title="❌ Resposta Incorreta",
                    description="A resposta correta é **A**. Como Guardião, você deve sempre manter a imparcialidade.",
                    color=0xff0000
                )
                embed.add_field(
                    name="Explicação",
                    value="Mesmo conhecendo a pessoa, você deve analisar a denúncia normalmente, mantendo a imparcialidade e julgando apenas o conteúdo.",
                    inline=False
                )
                self.clear_items()
                self.add_item(self.next_step)
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        elif self.current_step == 3:  # Quiz de utilização
            correct_answer = "B"
            is_correct = answer == correct_answer
            
            if is_correct:
                embed = discord.Embed(
                    title="✅ Resposta Correta!",
                    description="Excelente! Analisar cuidadosamente todas as evidências é fundamental para uma moderação justa.",
                    color=0x00ff00
                )
                self.current_step = 4
                self.clear_items()
                self.add_item(self.next_step)
            else:
                embed = discord.Embed(
                    title="❌ Resposta Incorreta",
                    description="A resposta correta é **B**. Sempre analise cuidadosamente todas as evidências.",
                    color=0xff0000
                )
                embed.add_field(
                    name="Explicação",
                    value="Uma moderação adequada requer análise cuidadosa de todas as evidências antes de tomar uma decisão.",
                    inline=False
                )
                self.clear_items()
                self.add_item(self.next_step)
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        elif self.current_step == 4:  # Prova final
            question = self.quiz_questions[self.current_question]
            is_correct = answer == question["correct"]
            
            if is_correct:
                self.correct_answers += 1
            
            self.current_question += 1
            
            if self.current_question < len(self.quiz_questions):
                await self._show_question(interaction)
            else:
                await self._finish_exam(interaction)
    
    async def _finish_exam(self, interaction: discord.Interaction):
        """Finaliza a prova e mostra o resultado"""
        total_questions = len(self.quiz_questions)
        percentage = (self.correct_answers / total_questions) * 100
        
        if self.correct_answers >= 9:  # Aprovado
            embed = discord.Embed(
                title="🎉 Parabéns! Você foi Aprovado!",
                description="Você agora é um **Guardião** oficial do Sistema Guardião BETA!",
                color=0x00ff00
            )
            embed.add_field(
                name="📊 Sua Performance",
                value=f"**Acertos:** {self.correct_answers}/{total_questions}\n"
                      f"**Porcentagem:** {percentage:.1f}%",
                inline=False
            )
            embed.add_field(
                name="🎖️ Próximos Passos",
                value="• Use `/turno` para entrar em serviço\n"
                      "• Use `/stats` para ver suas informações\n"
                      "• Mantenha-se sempre ético e imparcial",
                inline=False
            )
            
            # Atualiza a categoria do usuário para Guardião
            await self._update_user_to_guardian(interaction.user.id)
            
        else:  # Reprovado
            embed = discord.Embed(
                title="❌ Você foi Reprovado",
                description="Infelizmente você não atingiu a pontuação mínima para se tornar um Guardião.",
                color=0xff0000
            )
            embed.add_field(
                name="📊 Sua Performance",
                value=f"**Acertos:** {self.correct_answers}/{total_questions}\n"
                      f"**Porcentagem:** {percentage:.1f}%\n"
                      f"**Mínimo necessário:** 90%",
                inline=False
            )
            embed.add_field(
                name="⏰ Cooldown",
                value="Você pode tentar novamente em 24 horas usando `/formguardiao`.",
                inline=False
            )
            
            # Define o cooldown da prova
            await self._set_prova_cooldown(interaction.user.id)
        
        self.clear_items()
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def _update_user_to_guardian(self, user_id: int):
        """Atualiza a categoria do usuário para Guardião"""
        try:
            query = "UPDATE usuarios SET categoria = 'Guardião' WHERE id_discord = $1"
            db_manager.execute_command(query, user_id)
            logger.info(f"Usuário {user_id} promovido a Guardião")
        except Exception as e:
            logger.error(f"Erro ao promover usuário {user_id} a Guardião: {e}")
    
    async def _set_prova_cooldown(self, user_id: int):
        """Define o cooldown da prova"""
        try:
            cooldown_time = datetime.utcnow() + timedelta(hours=PROVA_COOLDOWN_HOURS)
            query = "UPDATE usuarios SET cooldown_prova = $1 WHERE id_discord = $2"
            db_manager.execute_command(query, cooldown_time, user_id)
            logger.info(f"Cooldown de prova definido para usuário {user_id}")
        except Exception as e:
            logger.error(f"Erro ao definir cooldown de prova para usuário {user_id}: {e}")


class GuardiaoCog(commands.Cog):
    """Cog para comandos de Guardião"""
    
    def __init__(self, bot):
        self.bot = bot
        self.points_loop.start()
    
    @discord.slash_command(
        name="formguardiao",
        description="Torne-se um Guardião do Sistema Guardião BETA"
    )
    async def formguardiao(self, ctx: discord.ApplicationContext):
        """
        Comando para se tornar um Guardião
        
        Inicia o processo de treinamento e prova para se tornar um Guardião
        """
        try:
            # Verifica se o banco de dados está disponível
            if not db_manager.pool:
                db_manager.initialize_pool()
            
            # Verifica a idade da conta (mínimo 3 meses)
            account_age = datetime.utcnow() - ctx.author.created_at
            if account_age.days < (GUARDIAO_MIN_ACCOUNT_AGE_MONTHS * 30):
                embed = discord.Embed(
                    title="❌ Conta Muito Nova",
                    description=f"Sua conta precisa ter pelo menos {GUARDIAO_MIN_ACCOUNT_AGE_MONTHS} meses para se tornar um Guardião.",
                    color=0xff0000
                )
                embed.add_field(
                    name="Informações da Sua Conta",
                    value=f"**Criada em:** {ctx.author.created_at.strftime('%d/%m/%Y')}\n"
                          f"**Dias de idade:** {account_age.days} dias\n"
                          f"**Dias necessários:** {GUARDIAO_MIN_ACCOUNT_AGE_MONTHS * 30} dias",
                    inline=False
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Verifica se o usuário está cadastrado
            user_data = get_user_by_discord_id_sync(ctx.author.id)
            if not user_data:
                embed = discord.Embed(
                    title="❌ Usuário Não Cadastrado",
                    description="Você precisa se cadastrar primeiro usando `/cadastro`!",
                    color=0xff0000
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Verifica se já é Guardião ou superior
            if user_data['categoria'] in ['Guardião', 'Moderador', 'Administrador']:
                embed = discord.Embed(
                    title="✅ Você Já é um Guardião!",
                    description=f"Você já possui a categoria **{user_data['categoria']}** no sistema.",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Comandos Disponíveis",
                    value="• `/turno` - Entrar/sair de serviço\n"
                          "• `/stats` - Ver suas estatísticas\n"
                          "• `/report` - Denunciar usuários",
                    inline=False
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Verifica cooldown da prova
            if user_data['cooldown_prova'] and user_data['cooldown_prova'] > datetime.utcnow():
                time_left = user_data['cooldown_prova'] - datetime.utcnow()
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                
                embed = discord.Embed(
                    title="⏰ Cooldown Ativo",
                    description="Você ainda está em cooldown da última tentativa de prova.",
                    color=0xffa500
                )
                embed.add_field(
                    name="Tempo Restante",
                    value=f"**{hours} horas e {minutes} minutos**",
                    inline=False
                )
                embed.add_field(
                    name="Quando Pode Tentar Novamente",
                    value=user_data['cooldown_prova'].strftime('%d/%m/%Y às %H:%M'),
                    inline=False
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Inicia o treinamento
            embed = discord.Embed(
                title="🎓 Treinamento para Guardião",
                description="Bem-vindo ao treinamento para se tornar um Guardião do Sistema Guardião BETA!",
                color=0x0099ff
            )
            embed.add_field(
                name="📚 O que é um Guardião?",
                value="Um Guardião é um moderador comunitário que:\n"
                      "• Analisa denúncias de forma imparcial\n"
                      "• Aplica as regras de forma justa\n"
                      "• Mantém a ordem e segurança dos servidores\n"
                      "• Colabora com outros Guardiões",
                inline=False
            )
            embed.add_field(
                name="🎯 Processo de Treinamento",
                value="• **Etapa 1:** Classificação de denúncias\n"
                      "• **Etapa 2:** Ética na moderação\n"
                      "• **Etapa 3:** Boa utilização da ferramenta\n"
                      "• **Etapa 4:** Prova final (10 perguntas)",
                inline=False
            )
            embed.add_field(
                name="⚠️ Requisitos",
                value="• Conta com pelo menos 3 meses\n"
                      "• Cadastro completo no sistema\n"
                      "• Mínimo 90% de acertos na prova final",
                inline=False
            )
            
            view = TrainingView(self.bot, ctx.author.id)
            await ctx.respond(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro no comando formguardiao para usuário {ctx.author.id}: {e}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
    
    @discord.slash_command(
        name="turno",
        description="Entre ou saia de serviço como Guardião"
    )
    async def turno(self, ctx: discord.ApplicationContext):
        """
        Comando para entrar/sair de serviço
        
        Permite aos Guardiões entrar e sair de serviço para receber denúncias
        """
        try:
            # Verifica se o banco de dados está disponível
            if not db_manager.pool:
                db_manager.initialize_pool()
            
            # Busca os dados do usuário
            user_data = get_user_by_discord_id_sync(ctx.author.id)
            if not user_data:
                embed = discord.Embed(
                    title="❌ Usuário Não Cadastrado",
                    description="Você precisa se cadastrar primeiro usando `/cadastro`!",
                    color=0xff0000
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Verifica se é Guardião ou superior
            if user_data['categoria'] not in ['Guardião', 'Moderador', 'Administrador']:
                embed = discord.Embed(
                    title="❌ Acesso Negado",
                    description="Apenas Guardiões, Moderadores e Administradores podem usar este comando.",
                    color=0xff0000
                )
                embed.add_field(
                    name="Como se tornar um Guardião",
                    value="Use o comando `/formguardiao` para iniciar o treinamento.",
                    inline=False
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Verifica se está em cooldown
            if user_data['cooldown_dispensa'] and user_data['cooldown_dispensa'] > datetime.utcnow():
                time_left = user_data['cooldown_dispensa'] - datetime.utcnow()
                minutes = time_left.seconds // 60
                
                embed = discord.Embed(
                    title="⏰ Cooldown Ativo",
                    description="Você está em cooldown por ter dispensado uma denúncia recentemente.",
                    color=0xffa500
                )
                embed.add_field(
                    name="Tempo Restante",
                    value=f"**{minutes} minutos**",
                    inline=False
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            if user_data['em_servico']:
                # Sair de serviço
                await self._exit_service(ctx, user_data)
            else:
                # Entrar em serviço
                await self._enter_service(ctx, user_data)
                
        except Exception as e:
            logger.error(f"Erro no comando turno para usuário {ctx.author.id}: {e}")
            embed = discord.Embed(
                title="❌ Erro no Sistema",
                description="Ocorreu um erro inesperado. Tente novamente mais tarde.",
                color=0xff0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
    
    async def _enter_service(self, ctx: discord.ApplicationContext, user_data: dict):
        """Entra em serviço"""
        try:
            now = datetime.utcnow()
            query = """
                UPDATE usuarios 
                SET em_servico = TRUE, ultimo_turno_inicio = $1 
                WHERE id_discord = $2
            """
            db_manager.execute_command(query, now, ctx.author.id)
            
            embed = discord.Embed(
                title="🟢 Você Entrou em Serviço!",
                description="Agora você está disponível para receber denúncias.",
                color=0x00ff00
            )
            embed.add_field(
                name="📋 Informações",
                value=f"**Início do turno:** {now.strftime('%d/%m/%Y às %H:%M')}\n"
                      f"**Pontos por hora:** {TURN_POINTS_PER_HOUR}\n"
                      f"**Status:** Ativo para receber denúncias",
                inline=False
            )
            embed.add_field(
                name="💡 Dicas",
                value="• Analise as denúncias com cuidado\n"
                      "• Seja imparcial em seus julgamentos\n"
                      "• Use `/turno` novamente para sair de serviço",
                inline=False
            )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro ao entrar em serviço para usuário {ctx.author.id}: {e}")
            raise
    
    async def _exit_service(self, ctx: discord.ApplicationContext, user_data: dict):
        """Sai de serviço"""
        try:
            now = datetime.utcnow()
            inicio_turno = user_data['ultimo_turno_inicio']
            
            if inicio_turno:
                # Calcula a duração do turno
                duracao = now - inicio_turno
                horas_completas = duracao.seconds // 3600
                pontos_ganhos = horas_completas * TURN_POINTS_PER_HOUR
                
                # Atualiza os pontos e sai de serviço
                query = """
                    UPDATE usuarios 
                    SET em_servico = FALSE, ultimo_turno_inicio = NULL, 
                        pontos = pontos + $1 
                    WHERE id_discord = $2
                """
                db_manager.execute_command(query, pontos_ganhos, ctx.author.id)
                
                embed = discord.Embed(
                    title="🔴 Você Saiu de Serviço!",
                    description="Turno finalizado com sucesso.",
                    color=0xff6600
                )
                embed.add_field(
                    name="📊 Resumo do Turno",
                    value=f"**Duração:** {horas_completas} horas\n"
                          f"**Pontos ganhos:** {pontos_ganhos}\n"
                          f"**Total de pontos:** {user_data['pontos'] + pontos_ganhos}",
                    inline=False
                )
            else:
                # Sai de serviço sem calcular pontos
                query = "UPDATE usuarios SET em_servico = FALSE, ultimo_turno_inicio = NULL WHERE id_discord = $1"
                db_manager.execute_command(query, ctx.author.id)
                
                embed = discord.Embed(
                    title="🔴 Você Saiu de Serviço!",
                    description="Turno finalizado.",
                    color=0xff6600
                )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Erro ao sair de serviço para usuário {ctx.author.id}: {e}")
            raise
    
    @tasks.loop(hours=1)
    async def points_loop(self):
        """Loop que adiciona pontos a cada hora para Guardiões em serviço"""
        try:
            if not db_manager.pool:
                return
            
            query = """
                UPDATE usuarios 
                SET pontos = pontos + $1 
                WHERE em_servico = TRUE AND categoria IN ('Guardião', 'Moderador', 'Administrador')
            """
            db_manager.execute_command(query, TURN_POINTS_PER_HOUR)
            
            logger.info(f"Pontos adicionados para Guardiões em serviço: +{TURN_POINTS_PER_HOUR}")
            
        except Exception as e:
            logger.error(f"Erro no loop de pontos: {e}")
    
    @points_loop.before_loop
    async def before_points_loop(self):
        """Aguarda o bot estar pronto antes de iniciar o loop"""
        await self.bot.wait_until_ready()
    
    @formguardiao.error
    async def formguardiao_error(self, ctx: discord.ApplicationContext, error):
        """Tratamento de erros do comando formguardiao"""
        if isinstance(error, commands.PrivateMessageOnly):
            embed = discord.Embed(
                title="⚠️ Comando Restrito",
                description="Este comando só pode ser usado em mensagens privadas (DM)!",
                color=0xffa500
            )
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            logger.error(f"Erro não tratado no comando formguardiao: {error}")
    
    @turno.error
    async def turno_error(self, ctx: discord.ApplicationContext, error):
        """Tratamento de erros do comando turno"""
        if isinstance(error, commands.PrivateMessageOnly):
            embed = discord.Embed(
                title="⚠️ Comando Restrito",
                description="Este comando só pode ser usado em mensagens privadas (DM)!",
                color=0xffa500
            )
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            logger.error(f"Erro não tratado no comando turno: {error}")


async def setup(bot):
    """Função para carregar o cog"""
    await bot.add_cog(GuardiaoCog(bot))
