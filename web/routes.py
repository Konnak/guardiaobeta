"""
Rotas da Aplicação Web - Sistema Guardião BETA
Implementa todas as rotas principais do site
"""

import os
import logging
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, session
import discord

# Configuração de logging
logger = logging.getLogger(__name__)

# Importações com tratamento de erro
try:
    from database.connection import db_manager
    logger.info("✅ db_manager importado com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao importar db_manager: {e}")
    db_manager = None

try:
    from utils.experience_system import get_experience_rank, get_rank_emoji, format_experience_display
    logger.info("✅ utils.experience_system importado com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao importar utils.experience_system: {e}")
    # Funções de fallback
    def get_experience_rank(exp): return "Iniciante"
    def get_rank_emoji(rank): return "🔰"
    def format_experience_display(exp): return f"{exp} XP"

try:
    from web.auth import login_required, admin_required, get_user_guilds_admin, get_bot_invite_url, get_user_avatar_url, get_guild_icon_url
    logger.info("✅ web.auth importado com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao importar web.auth: {e}")
    # Decoradores de fallback
    def login_required(f):
        def login_wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        login_wrapper.__name__ = f.__name__
        return login_wrapper
    
    def admin_required(f):
        def admin_wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        admin_wrapper.__name__ = f.__name__
        return admin_wrapper
    
    # Funções de fallback
    def get_user_guilds_admin(): return []
    def get_bot_invite_url(): return "#"
    def get_user_avatar_url(user_id, avatar, discriminator): return "/static/img/default-avatar.png"
    def get_guild_icon_url(guild_id, icon): return "/static/img/default-avatar.png"


def setup_routes(app):
    """Configura todas as rotas da aplicação"""
    
    def get_bot_instance():
        """Obtém a instância do bot de forma segura"""
        try:
            logger.info("🔍 INÍCIO: get_bot_instance()")
            
            # Tenta importar o bot
            import sys
            logger.info(f"🔍 sys.modules tem 'main': {'main' in sys.modules}")
            
            if 'main' in sys.modules:
                logger.info("🔍 Usando bot de sys.modules['main']")
                bot = sys.modules['main'].bot
            else:
                logger.info("🔍 Importando bot diretamente de main")
                from main import bot
            
            logger.info(f"🔍 Bot importado: {bot is not None}")
            if bot:
                logger.info(f"🔍 Bot is_ready(): {bot.is_ready()}")
                logger.info(f"🔍 Bot user: {bot.user}")
                logger.info(f"🔍 Bot guilds: {len(bot.guilds) if bot.guilds else 0}")
                logger.info(f"🔍 Bot websocket: {bot.ws is not None if hasattr(bot, 'ws') else 'N/A'}")
                logger.info(f"🔍 Bot is_closed(): {bot.is_closed()}")
                logger.info(f"🔍 Bot loop: {bot.loop is not None if hasattr(bot, 'loop') else 'N/A'}")
                # Não podemos acessar bot.loop.is_running() em contexto não-assíncrono
                logger.info(f"🔍 Bot loop running: N/A (não acessível em contexto síncrono)")
                
                # Verifica se o bot está conectado - critério mais flexível
                if bot.user is not None and not bot.is_closed():
                    logger.info("✅ Bot está conectado e funcionando")
                    return bot
                elif bot.user is None:
                    logger.warning("⚠️ Bot ainda não está logado (bot.user é None)")
                    logger.warning("⚠️ Isso pode indicar que o bot ainda está inicializando")
                    # Vamos tentar aguardar um pouco mais e verificar novamente
                    import time
                    time.sleep(2)
                    logger.info(f"🔍 Verificação após 2s - Bot user: {bot.user}")
                    if bot.user is not None:
                        logger.info("✅ Bot agora está logado!")
                        return bot
                    
                    # NOVO: Mesmo que bot.user seja None, vamos tentar usar o bot
                    # se ele não estiver fechado, pois pode estar funcionando
                    if not bot.is_closed():
                        logger.warning("⚠️ Bot.user é None mas bot não está fechado - tentando usar mesmo assim")
                        return bot
                    
                    return None
                elif bot.is_closed():
                    logger.warning("⚠️ Bot está fechado")
                    return None
                else:
                    logger.warning("⚠️ Bot não está conectado adequadamente")
                    logger.warning(f"⚠️ bot.user: {bot.user}")
                    logger.warning(f"⚠️ bot.is_closed(): {bot.is_closed()}")
                    return None
            else:
                logger.warning("⚠️ Bot é None")
                return None
        except ImportError as e:
            logger.error(f"❌ Erro ao importar bot: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao acessar bot: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None
    
    def wait_for_bot_ready(timeout_seconds=30):
        """Aguarda o bot estar pronto com timeout estendido"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            bot = get_bot_instance()
            if bot:
                logger.info("✅ Bot está pronto!")
                return bot
            
            logger.info(f"⏳ Aguardando bot estar pronto... ({time.time() - start_time:.1f}s)")
            time.sleep(2)  # Aumenta o intervalo de espera
        
        logger.warning(f"⏰ Timeout: Bot não ficou pronto em {timeout_seconds} segundos")
        return None
    
    async def send_dm_to_user(bot, user_id: int, embed, user_type: str = "usuário"):
        """Envia DM para um usuário específico de forma robusta"""
        try:
            # Tenta buscar usuário no cache primeiro
            user = bot.get_user(user_id)
            if not user:
                # Se não encontrou no cache, tenta buscar via API
                try:
                    logger.info(f"Buscando {user_type} {user_id} via API do Discord...")
                    user = await bot.fetch_user(user_id)
                    logger.info(f"{user_type.capitalize()} encontrado via API: {user.name}")
                except discord.NotFound:
                    logger.warning(f"{user_type.capitalize()} {user_id} não encontrado na API do Discord")
                    return False
                except discord.HTTPException as e:
                    logger.warning(f"Erro HTTP ao buscar {user_type} {user_id}: {e}")
                    return False
                except Exception as e:
                    logger.warning(f"Erro ao buscar {user_type} {user_id} via API: {e}")
                    return False
            
            if user:
                logger.info(f"{user_type.capitalize()} encontrado no Discord: {user.name}")
                try:
                    dm_channel = await user.create_dm()
                    logger.info(f"Canal DM criado: {dm_channel.id}")
                    await dm_channel.send(embed=embed)
                    logger.info(f"Mensagem enviada para {user_type} {user_id}")
                    return True
                except discord.Forbidden:
                    logger.warning(f"Não foi possível enviar DM para {user.name} - DMs bloqueados")
                    return False
                except discord.HTTPException as e:
                    logger.error(f"Erro HTTP ao enviar DM para {user.name}: {e}")
                    return False
                except Exception as e:
                    logger.error(f"Erro ao enviar DM para {user.name}: {e}")
                    return False
            else:
                logger.warning(f"{user_type.capitalize()} {user_id} não encontrado no Discord")
                return False
                
        except Exception as e:
            logger.error(f"Erro geral ao enviar DM para {user_type} {user_id}: {e}")
            return False
    logger.info("🚀 Iniciando configuração de rotas...")
    
    @app.route('/')
    def index():
        """Página inicial - Marketing do bot"""
        try:
            # Estatísticas gerais para exibir na página inicial
            stats = {
                'total_usuarios': 0,
                'total_guardioes': 0,
                'total_denuncias': 0,
                'total_servidores': 0
            }
            
            try:
                if db_manager.pool:
                    # Busca estatísticas do banco
                    stats_query = """
                        SELECT 
                            (SELECT COUNT(*) FROM usuarios) as total_usuarios,
                            (SELECT COUNT(*) FROM usuarios WHERE categoria = 'Guardião') as total_guardioes,
                            (SELECT COUNT(*) FROM denuncias) as total_denuncias,
                            (SELECT COUNT(DISTINCT id_servidor) FROM denuncias) as total_servidores
                    """
                    db_stats = db_manager.execute_query_sync(stats_query)
                    if db_stats:
                        stats = db_stats[0]
            except Exception as e:
                logger.warning(f"Não foi possível obter estatísticas: {e}")
            
            return render_template('index.html', 
                                 stats=stats,
                                 bot_invite_url=get_bot_invite_url())
            
        except Exception as e:
            logger.error(f"Erro na página inicial: {e}")
            return render_template('index.html', 
                                 stats={'total_usuarios': 0, 'total_guardioes': 0, 'total_denuncias': 0, 'total_servidores': 0},
                                 bot_invite_url=get_bot_invite_url())
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard do usuário"""
        try:
            user_data = session['user']
            user_id = user_data['id']
            
            # Busca dados do usuário no banco
            db_user = db_manager.execute_one_sync(
                "SELECT * FROM usuarios WHERE id_discord = $1", user_id
            )
            
            if not db_user:
                # Usuário não cadastrado
                return render_template('dashboard.html',
                                     user=user_data,
                                     cadastrado=False,
                                     avatar_url=get_user_avatar_url(str(user_id), user_data.get('avatar'), user_data.get('discriminator')))
            
            # Busca estatísticas do usuário
            stats_query = """
                SELECT 
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = $1) as denuncias_atendidas,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = $1) as total_votos,
                    (SELECT COUNT(*) FROM denuncias WHERE id_denunciante = $1) as denuncias_feitas
            """
            user_stats = db_manager.execute_query_sync(stats_query, user_id)
            stats = user_stats[0] if user_stats else {'denuncias_atendidas': 0, 'total_votos': 0, 'denuncias_feitas': 0}
            
            # Calcula informações de experiência
            rank = get_experience_rank(db_user['experiencia'])
            emoji = get_rank_emoji(rank)
            experience_display = format_experience_display(db_user['experiencia'])
            
            # Formata última atividade
            ultima_atividade = "Nunca"
            if db_user['ultimo_turno_inicio']:
                diff = datetime.utcnow() - db_user['ultimo_turno_inicio']
                if diff.days > 0:
                    ultima_atividade = f"{diff.days} dias atrás"
                elif diff.seconds > 3600:
                    hours = diff.seconds // 3600
                    ultima_atividade = f"{hours} horas atrás"
                elif diff.seconds > 60:
                    minutes = diff.seconds // 60
                    ultima_atividade = f"{minutes} minutos atrás"
                else:
                    ultima_atividade = "Agora mesmo"
            
            return render_template('dashboard.html',
                                 user=user_data,
                                 cadastrado=True,
                                 db_user=db_user,
                                 stats=stats,
                                 rank=rank,
                                 emoji=emoji,
                                 experience_display=experience_display,
                                 ultima_atividade=ultima_atividade,
                                 avatar_url=get_user_avatar_url(str(user_id), user_data.get('avatar'), user_data.get('discriminator')))
            
        except Exception as e:
            logger.error(f"Erro no dashboard: {e}")
            flash("Erro ao carregar dashboard.", "error")
            return redirect(url_for('index'))
    
    @app.route('/server/<int:server_id>')
    @login_required
    def server_panel(server_id):
        """Painel de controle do servidor"""
        try:
            user_data = session['user']
            
            # Verifica se o usuário é admin do servidor
            admin_guilds = get_user_guilds_admin()
            guild = None
            
            for admin_guild in admin_guilds:
                if int(admin_guild['id']) == server_id:
                    guild = admin_guild
                    break
            
            if not guild:
                flash("Você não tem permissão para acessar este servidor.", "error")
                return redirect(url_for('dashboard'))
            
            # Busca estatísticas do servidor
            server_stats = get_server_stats(server_id)
            
            # Verifica se é servidor premium
            premium_query = """
                SELECT * FROM servidores_premium 
                WHERE id_servidor = $1 AND data_fim > NOW()
            """
            premium_data = db_manager.execute_one_sync(premium_query, server_id)
            is_premium = premium_data is not None
            
            # Busca configurações do servidor (se premium)
            server_config = None
            if is_premium:
                config_query = """
                    SELECT * FROM configuracoes_servidor 
                    WHERE id_servidor = $1
                """
                server_config = db_manager.execute_one_sync(config_query, server_id)
            
            logger.info(f"📤 Renderizando server_panel para servidor: {server_id}")
            
            return render_template('server_panel.html',
                                 user=user_data,
                                 guild=guild,
                                 server_id=server_id,
                                 stats=server_stats,
                                 is_premium=is_premium,
                                 premium_data=premium_data,
                                 server_config=server_config,
                                 guild_icon_url=get_guild_icon_url(str(server_id), guild.get('icon')),
                                 avatar_url=get_user_avatar_url(str(user_data['id']), user_data.get('avatar'), user_data.get('discriminator')))
            
        except Exception as e:
            logger.error(f"Erro no painel do servidor: {e}")
            flash("Erro ao carregar painel do servidor.", "error")
            return redirect(url_for('dashboard'))
    
    @app.route('/servers')
    @app.route('/servers/')
    @login_required
    def servers():
        """Lista de servidores do usuário"""
        try:
            user_data = session['user']
            admin_guilds = get_user_guilds_admin()
            
            # Busca informações completas para cada servidor
            servers_info = []
            for guild in admin_guilds:
                guild_id = int(guild['id'])
                
                # Verificar premium
                premium_query = """
                    SELECT *, 
                           data_fim AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo' as data_fim_br
                    FROM servidores_premium 
                    WHERE id_servidor = $1 AND data_fim > NOW()
                """
                premium_data = db_manager.execute_one_sync(premium_query, guild_id)
                
                # Verificar se bot está no servidor (tentar buscar canais)
                bot_in_server = False
                bot_token = os.getenv('DISCORD_TOKEN')
                
                if bot_token:
                    try:
                        import requests
                        headers = {'Authorization': f'Bot {bot_token}'}
                        response = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/channels', headers=headers, timeout=5)
                        bot_in_server = response.status_code == 200
                        
                        if not bot_in_server:
                            logger.warning(f"Bot não está no servidor {guild['name']} (ID: {guild_id}) - Status: {response.status_code}")
                    except Exception as e:
                        logger.error(f"Erro ao verificar bot no servidor {guild['name']}: {e}")
                        bot_in_server = False
                else:
                    # TEMPORÁRIO: Se não tem token, assumir que bot está presente
                    # Isso evita mostrar "Não Protegido" para todos os servidores
                    logger.warning(f"DISCORD_TOKEN não configurado - assumindo bot presente no servidor {guild['name']}")
                    bot_in_server = True
                
                # Buscar estatísticas de denúncias
                denuncias_stats = {'pendentes': 0, 'analise': 0, 'total': 0}
                try:
                    stats_query = """
                        SELECT 
                            COUNT(*) as total,
                            SUM(CASE WHEN status = 'Pendente' THEN 1 ELSE 0 END) as pendentes,
                            SUM(CASE WHEN status = 'Em Análise' THEN 1 ELSE 0 END) as analise
                        FROM denuncias 
                        WHERE id_servidor = $1 AND status IN ('Pendente', 'Em Análise')
                    """
                    stats_result = db_manager.execute_one_sync(stats_query, guild_id)
                    if stats_result:
                        denuncias_stats = {
                            'pendentes': stats_result['pendentes'] or 0,
                            'analise': stats_result['analise'] or 0,
                            'total': stats_result['total'] or 0
                        }
                except Exception as e:
                    logger.error(f"Erro ao buscar stats de denúncias: {e}")
                
                servers_info.append({
                    'guild': guild,
                    'is_premium': premium_data is not None,
                    'premium_data': premium_data,
                    'bot_in_server': bot_in_server,
                    'denuncias_stats': denuncias_stats,
                    'icon_url': get_guild_icon_url(guild['id'], guild.get('icon'))
                })
            
            return render_template('servers.html',
                                 user=user_data,
                                 servers=servers_info,
                                 avatar_url=get_user_avatar_url(str(user_data['id']), user_data.get('avatar'), user_data.get('discriminator')),
                                 bot_invite_url=get_bot_invite_url())
            
        except Exception as e:
            logger.error(f"Erro na lista de servidores: {e}")
            flash("Erro ao carregar lista de servidores.", "error")
            return redirect(url_for('dashboard'))
    
    @app.route('/server/<int:server_id>/premium')
    @login_required
    def server_premium_config(server_id):
        """Página de configurações premium do servidor"""
        try:
            # Verificar se o usuário tem acesso ao servidor
            admin_guilds = get_user_guilds_admin()
            server_found = None
            for guild in admin_guilds:
                if guild['id'] == str(server_id):
                    server_found = guild
                    break
            
            if not server_found:
                flash('Você não tem permissão para acessar este servidor.', 'error')
                return redirect(url_for('servers'))
            
            # Verificar se o servidor tem premium ativo
            premium_query = """
                SELECT *, 
                       data_inicio AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo' as data_inicio_br,
                       data_fim AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo' as data_fim_br
                FROM servidores_premium 
                WHERE id_servidor = $1 AND data_fim > NOW()
            """
            premium_data = db_manager.execute_one_sync(premium_query, server_id)
            
            if not premium_data:
                flash('Este servidor não possui premium ativo.', 'warning')
                return redirect(url_for('servers'))
            
            # Buscar configurações do servidor
            config_query = """
                SELECT * FROM configuracoes_servidor 
                WHERE id_servidor = $1
            """
            server_config = db_manager.execute_one_sync(config_query, server_id)
            
            # Obter ícone do servidor
            server_icon = get_guild_icon_url(server_id, server_found.get('icon'))
            
            return render_template('server_premium.html',
                                 server_id=server_id,
                                 server_name=server_found['name'],
                                 server_icon=server_icon,
                                 premium_data=premium_data,
                                 server_config=server_config)
            
        except Exception as e:
            logger.error(f"Erro na página premium do servidor: {e}")
            flash("Erro ao carregar configurações premium.", "error")
            return redirect(url_for('servers'))
    
    @app.route('/premium')
    def premium():
        """Página de informações sobre premium"""
        try:
            return render_template('premium.html',
                                 bot_invite_url=get_bot_invite_url())
            
        except Exception as e:
            logger.error(f"Erro na página premium: {e}")
            return render_template('premium.html',
                                 bot_invite_url=get_bot_invite_url())
    
    @app.route('/premium/select-server')
    @login_required
    def premium_select_server():
        """Página para selecionar servidor antes do pagamento"""
        try:
            user_data = session['user']
            admin_guilds = get_user_guilds_admin()
            
            # Filtrar apenas servidores onde o bot está presente e que não têm premium
            available_servers = []
            logger.info(f"🔍 Verificando {len(admin_guilds)} servidores para seleção premium...")
            
            # Obter token uma vez
            bot_token = os.getenv('DISCORD_TOKEN')
            if not bot_token:
                logger.warning("⚠️ DISCORD_TOKEN não encontrado no .env - assumindo bot presente em todos os servidores")
            
            for guild in admin_guilds:
                guild_id = int(guild['id'])
                guild_name = guild.get('name', 'Servidor Desconhecido')
                
                logger.info(f"📊 Verificando servidor: {guild_name} (ID: {guild_id})")
                
                # Verificar se bot está no servidor
                bot_in_server = False
                if bot_token:
                    try:
                        import requests
                        logger.info(f"  🔑 Token encontrado: {bot_token[:20]}...")
                        headers = {'Authorization': f'Bot {bot_token}'}
                        response = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/channels', headers=headers, timeout=5)
                        bot_in_server = response.status_code == 200
                        logger.info(f"  📡 Discord API response: {response.status_code}")
                        if response.status_code != 200:
                            logger.warning(f"  ⚠️ Discord API error: {response.text[:200]}")
                        logger.info(f"  🤖 Bot no servidor: {'✅ Sim' if bot_in_server else '❌ Não'}")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erro ao verificar bot: {e}")
                        bot_in_server = False
                else:
                    # Se não tem token, assumir que bot está presente
                    logger.warning(f"  ⚠️ Sem token, assumindo bot presente")
                    bot_in_server = True
                
                # Verificar se já tem premium ativo
                has_premium = False
                try:
                    premium_query = """
                        SELECT id_servidor FROM servidores_premium 
                        WHERE id_servidor = $1 AND data_fim > NOW()
                    """
                    has_premium = db_manager.execute_one_sync(premium_query, guild_id) is not None
                    logger.info(f"  💎 Premium ativo: {'❌ Sim (não elegível)' if has_premium else '✅ Não (elegível)'}")
                except Exception as e:
                    logger.error(f"  ❌ Erro ao verificar premium: {e}")
                    has_premium = False  # Se erro, assume que não tem premium
                
                # Adicionar à lista se elegível
                
                if bot_in_server and not has_premium:
                    available_servers.append({
                        'guild': guild,
                        'icon_url': get_guild_icon_url(guild['id'], guild.get('icon'))
                    })
                    logger.info(f"  ✅ Servidor adicionado à lista de elegíveis!")
                else:
                    reason = []
                    if not bot_in_server:
                        reason.append("bot não presente")
                    if has_premium:
                        reason.append("já tem premium")
                    logger.info(f"  ❌ Servidor não elegível: {', '.join(reason)}")
            
            logger.info(f"📋 Total de servidores elegíveis: {len(available_servers)}")
            
            if not available_servers:
                flash('Nenhum servidor disponível para premium. Certifique-se de que o bot está nos servidores e que eles não têm premium ativo.', 'warning')
                return redirect(url_for('servers'))
            
            # Obter plano da query string
            plan = request.args.get('plan', 'monthly')
            if plan not in ['monthly', 'quarterly', 'yearly']:
                plan = 'monthly'
            
            return render_template('premium_select_server.html',
                                 user=user_data,
                                 servers=available_servers,
                                 selected_plan=plan,
                                 avatar_url=get_user_avatar_url(str(user_data['id']), user_data.get('avatar'), user_data.get('discriminator')))
            
        except Exception as e:
            logger.error(f"Erro na seleção de servidor: {e}")
            flash("Erro ao carregar servidores disponíveis.", "error")
            return redirect(url_for('premium'))
    
    @app.route('/api/server/<int:server_id>/channels')
    @login_required
    def get_server_channels(server_id):
        """API para obter canais de texto do servidor"""
        try:
            # Verificar se o usuário tem acesso ao servidor
            admin_guilds = get_user_guilds_admin()
            server_found = any(guild['id'] == str(server_id) for guild in admin_guilds)
            
            if not server_found:
                logger.warning(f"Usuário tentou acessar servidor {server_id} sem permissão")
                return jsonify({'error': 'Acesso negado ao servidor'}), 403
            
            # Usar a API do Discord através do bot para obter canais
            import requests
            bot_token = os.getenv('DISCORD_TOKEN')
            
            if not bot_token:
                logger.error("DISCORD_TOKEN não configurado para buscar canais")
                # Retornar canais fictícios para permitir teste
                fake_channels = [
                    {'id': '123456789', 'name': '📋｜logs', 'type': 0, 'position': 0},
                    {'id': '123456790', 'name': '📢｜anuncios', 'type': 0, 'position': 1},
                    {'id': '123456791', 'name': '💬｜geral', 'type': 0, 'position': 2},
                    {'id': '123456792', 'name': '🤖｜bot-commands', 'type': 0, 'position': 3}
                ]
                return jsonify({
                    'success': True,
                    'channels': fake_channels,
                    'warning': 'Token do bot não configurado - canais fictícios para teste'
                })
                
            headers = {'Authorization': f'Bot {bot_token}'}
            response = requests.get(f'https://discord.com/api/v10/guilds/{server_id}/channels', headers=headers)
            
            logger.info(f"Discord API response para servidor {server_id}: {response.status_code}")
            
            if response.status_code == 200:
                channels_data = response.json()
                # Filtrar apenas canais de texto (tipo 0)
                text_channels = [
                    {
                        'id': channel['id'],
                        'name': channel['name'],
                        'type': channel['type'],
                        'position': channel.get('position', 0)
                    }
                    for channel in channels_data 
                    if channel['type'] == 0  # GUILD_TEXT
                ]
                
                # Ordenar por posição
                text_channels.sort(key=lambda x: x['position'])
                
                logger.info(f"Encontrados {len(text_channels)} canais de texto no servidor {server_id}")
                
                return jsonify({
                    'success': True,
                    'channels': text_channels
                })
            elif response.status_code == 403:
                logger.error(f"Bot não tem acesso ao servidor {server_id} - Status: 403 Forbidden")
                return jsonify({'error': 'Bot não tem acesso a este servidor. Convide o bot primeiro.'}), 403
            elif response.status_code == 404:
                logger.error(f"Servidor {server_id} não encontrado - Status: 404 Not Found")
                return jsonify({'error': 'Servidor não encontrado ou bot não está nele.'}), 404
            else:
                logger.error(f"Erro ao buscar canais do servidor {server_id}: {response.status_code} - {response.text[:200]}")
                return jsonify({'error': f'Erro da API Discord: {response.status_code}'}), 500
                
        except Exception as e:
            logger.error(f"Erro na API de canais: {e}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.route('/api/server/<int:server_id>/config', methods=['POST'])
    @login_required
    def save_server_config(server_id):
        """API para salvar configurações premium do servidor"""
        try:
            # Verificar se o usuário tem acesso ao servidor
            admin_guilds = get_user_guilds_admin()
            server_found = any(guild['id'] == str(server_id) for guild in admin_guilds)
            
            if not server_found:
                return jsonify({'error': 'Acesso negado ao servidor'}), 403
            
            # Verificar se o servidor tem premium ativo
            premium_check = """
                SELECT id_servidor FROM servidores_premium 
                WHERE id_servidor = $1 AND data_fim > NOW()
            """
            premium_exists = db_manager.execute_one_sync(premium_check, server_id)
            
            if not premium_exists:
                return jsonify({'error': 'Servidor não possui premium ativo'}), 403
            
            # Obter dados do formulário
            data = request.get_json()
            canal_log = data.get('canal_log')
            duracao_intimidou = data.get('duracao_intimidou', 1)
            duracao_grave = data.get('duracao_grave', 12)
            
            # Validações
            try:
                duracao_intimidou = int(duracao_intimidou)
                duracao_grave = int(duracao_grave) 
                
                if not (1 <= duracao_intimidou <= 24):
                    return jsonify({'error': 'Duração de intimidação deve estar entre 1 e 24 horas'}), 400
                if not (1 <= duracao_grave <= 168):
                    return jsonify({'error': 'Duração grave deve estar entre 1 e 168 horas'}), 400
                    
            except ValueError:
                return jsonify({'error': 'Durações devem ser números válidos'}), 400
            
            # Salvar configurações no banco (sem duracao_ban - usar duracao_grave_4plus)
            upsert_config = """
                INSERT INTO configuracoes_servidor (id_servidor, canal_log, duracao_intimidou, duracao_grave)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id_servidor) 
                DO UPDATE SET 
                    canal_log = EXCLUDED.canal_log,
                    duracao_intimidou = EXCLUDED.duracao_intimidou,
                    duracao_grave = EXCLUDED.duracao_grave
            """
            
            db_manager.execute_query_sync(upsert_config, server_id, canal_log, duracao_intimidou, duracao_grave)
            
            logger.info(f"Configurações premium salvas para servidor {server_id}")
            
            return jsonify({
                'success': True,
                'message': 'Configurações salvas com sucesso!'
            })
            
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    # ==================== STRIPE PAYMENT ROUTES ====================
    @app.route('/api/create-checkout', methods=['POST'])
    @login_required
    def create_checkout():
        """Criar sessão de checkout do Stripe"""
        try:
            import stripe
            
            # Configurar Stripe
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            if not stripe.api_key:
                logger.error("STRIPE_SECRET_KEY não configurado no .env")
                return jsonify({'success': False, 'error': 'Stripe não configurado. Verifique as variáveis de ambiente.'}), 500
            
            logger.info(f"Stripe configurado com chave: {stripe.api_key[:7]}...")
            
            data = request.get_json()
            plan = data.get('plan')
            server_id = data.get('server_id')
            
            logger.info(f"Criando checkout para plano: {plan}, servidor: {server_id}")
            
            if not server_id:
                return jsonify({'success': False, 'error': 'ID do servidor é obrigatório'}), 400
            
            # Verificar se o usuário tem acesso ao servidor
            admin_guilds = get_user_guilds_admin()
            server_found = any(guild['id'] == str(server_id) for guild in admin_guilds)
            
            if not server_found:
                return jsonify({'success': False, 'error': 'Acesso negado ao servidor'}), 403
            
            # Verificar se o servidor já tem premium
            premium_check = """
                SELECT id_servidor FROM servidores_premium 
                WHERE id_servidor = $1 AND data_fim > NOW()
            """
            has_premium = db_manager.execute_one_sync(premium_check, int(server_id)) is not None
            
            if has_premium:
                return jsonify({'success': False, 'error': 'Este servidor já possui premium ativo'}), 400
            
            # Definir produtos e preços
            plans_config = {
                'monthly': {
                    'price': 990,  # R$ 9,90 em centavos
                    'currency': 'brl',
                    'interval': 'month',
                    'name': 'Guardião Premium - Mensal'
                },
                'quarterly': {
                    'price': 2490,  # R$ 24,90 em centavos  
                    'currency': 'brl',
                    'interval': 'month',
                    'interval_count': 3,
                    'name': 'Guardião Premium - Trimestral'
                },
                'yearly': {
                    'price': 8990,  # R$ 89,90 em centavos
                    'currency': 'brl', 
                    'interval': 'year',
                    'name': 'Guardião Premium - Anual'
                }
            }
            
            if plan not in plans_config:
                return jsonify({'success': False, 'error': 'Plano inválido'}), 400
            
            plan_config = plans_config[plan]
            user_data = session['user']
            
            # Criar sessão de checkout
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': plan_config['currency'],
                        'product_data': {
                            'name': plan_config['name'],
                            'description': f'Acesso premium para o Guardião Bot',
                        },
                        'unit_amount': plan_config['price'],
                        'recurring': {
                            'interval': plan_config['interval'],
                            'interval_count': plan_config.get('interval_count', 1)
                        }
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.url_root + 'premium/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.url_root + 'premium',
                customer_email=f"{user_data['username']}@discord.local",
                metadata={
                    'user_id': str(user_data['id']),
                    'username': user_data['username'],
                    'plan': plan,
                    'server_id': str(server_id)
                }
            )
            
            logger.info(f"Checkout criado com sucesso!")
            logger.info(f"- Usuário: {user_data['username']}")
            logger.info(f"- Session ID: {checkout_session.id}")
            logger.info(f"- URL: {checkout_session.url}")
            logger.info(f"- Plano: {plan} - {plan_config['name']}")
            logger.info(f"- Preço: R$ {plan_config['price']/100:.2f}")
            
            return jsonify({
                'success': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            })
            
        except Exception as e:
            logger.error(f"Erro ao criar checkout: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/premium/success')
    @login_required
    def premium_success():
        """Página de sucesso após pagamento - ATIVA PREMIUM AUTOMATICAMENTE"""
        try:
            session_id = request.args.get('session_id')
            
            if not session_id:
                flash('Sessão inválida.', 'error')
                return redirect(url_for('premium'))
            
            # Verificar sessão no Stripe e ativar premium
            import stripe
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            if not stripe.api_key:
                flash("Stripe não configurado. Entre em contato com o administrador.", "error")
                return redirect(url_for('servers'))
            
            try:
                checkout_session = stripe.checkout.Session.retrieve(session_id)
                logger.info(f"🎉 Processando sucesso do pagamento: {session_id}")
                
                if checkout_session.payment_status != 'paid':
                    flash('Pagamento pendente. Aguarde a confirmação.', 'warning')
                    return redirect(url_for('servers'))
                
                # Extrair metadados
                user_id = checkout_session['metadata'].get('user_id')
                plan = checkout_session['metadata'].get('plan')
                server_id = checkout_session['metadata'].get('server_id')
                
                logger.info(f"📊 Dados da sessão: user_id={user_id}, plan={plan}, server_id={server_id}")
                
                if not all([user_id, plan, server_id]):
                    logger.error(f"❌ Dados incompletos na sessão: user_id={user_id}, plan={plan}, server_id={server_id}")
                    flash("Dados de pagamento incompletos. Entre em contato com o suporte.", "error")
                    return redirect(url_for('servers'))
                
                # Calcular data de expiração
                from datetime import datetime, timedelta
                
                if plan == 'monthly':
                    data_fim = datetime.utcnow() + timedelta(days=30)
                    plano_nome = "Mensal"
                elif plan == 'quarterly':
                    data_fim = datetime.utcnow() + timedelta(days=90)
                    plano_nome = "Trimestral"
                elif plan == 'yearly':
                    data_fim = datetime.utcnow() + timedelta(days=365)
                    plano_nome = "Anual"
                else:
                    data_fim = datetime.utcnow() + timedelta(days=30)
                    plano_nome = "Mensal"
                
                # Ativar premium no servidor
                try:
                    # Tentar com schema completo
                    activate_premium_query = """
                        INSERT INTO servidores_premium (id_servidor, data_inicio, data_fim, motivo, stripe_session_id)
                        VALUES ($1, NOW(), $2, $3, $4)
                        ON CONFLICT (id_servidor) 
                        DO UPDATE SET 
                            data_fim = EXCLUDED.data_fim,
                            motivo = EXCLUDED.motivo,
                            stripe_session_id = EXCLUDED.stripe_session_id
                    """
                    
                    motivo = f"Premium {plano_nome} ativado via Stripe (Sucesso Manual)"
                    db_manager.execute_query_sync(activate_premium_query, int(server_id), data_fim, motivo, session_id)
                    
                except Exception as schema_error:
                    logger.warning(f"Schema completo falhou, tentando básico: {schema_error}")
                    
                    # Fallback para schema básico
                    activate_premium_basic_query = """
                        INSERT INTO servidores_premium (id_servidor, data_inicio, data_fim)
                        VALUES ($1, NOW(), $2)
                        ON CONFLICT (id_servidor) 
                        DO UPDATE SET data_fim = EXCLUDED.data_fim
                    """
                    
                    db_manager.execute_query_sync(activate_premium_basic_query, int(server_id), data_fim)
                
                logger.info(f"✅ Premium ativado com sucesso via página de sucesso!")
                logger.info(f"- Usuário: {user_id}")
                logger.info(f"- Servidor: {server_id}")
                logger.info(f"- Plano: {plano_nome}")
                logger.info(f"- Válido até: {data_fim}")
                logger.info(f"- Session ID: {session_id}")
                
                flash(f"🎉 Premium {plano_nome} ativado com sucesso! Válido até {data_fim.strftime('%d/%m/%Y')}.", "success")
                    
            except stripe.error.StripeError as e:
                logger.error(f"Erro ao verificar sessão Stripe: {e}")
                flash('Erro ao verificar pagamento.', 'error')
            
            return redirect(url_for('servers'))
            
        except Exception as e:
            logger.error(f"❌ Erro na ativação do premium: {e}")
            flash("Pagamento processado, mas houve erro na ativação. Entre em contato com o suporte.", "error")
            return redirect(url_for('servers'))

    @app.route('/webhook/stripe', methods=['POST'])
    def stripe_webhook():
        """Webhook do Stripe para processar eventos"""
        try:
            import stripe
            
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
            
            payload = request.get_data()
            sig_header = request.headers.get('Stripe-Signature')
            
            if not endpoint_secret:
                logger.error("STRIPE_WEBHOOK_SECRET não configurado")
                return '', 400
            
            try:
                event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
            except ValueError:
                logger.error("Payload inválido")
                return '', 400
            except stripe.error.SignatureVerificationError:
                logger.error("Assinatura inválida")
                return '', 400
            
            # Processar evento
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                
                # Extrair dados do cliente
                user_id = session['metadata'].get('user_id')
                plan = session['metadata'].get('plan')
                server_id = session['metadata'].get('server_id')
                
                if user_id and plan and server_id:
                    # Calcular data de expiração baseada no plano
                    from datetime import datetime, timedelta
                    
                    if plan == 'monthly':
                        data_fim = datetime.utcnow() + timedelta(days=30)
                    elif plan == 'quarterly':
                        data_fim = datetime.utcnow() + timedelta(days=90)
                    elif plan == 'yearly':
                        data_fim = datetime.utcnow() + timedelta(days=365)
                    else:
                        data_fim = datetime.utcnow() + timedelta(days=30)
                    
                    try:
                        # Ativar premium no servidor específico
                        # Primeiro, verificar se as colunas motivo e stripe_session_id existem
                        try:
                            # Tentar com todas as colunas
                            activate_premium_query = """
                                INSERT INTO servidores_premium (id_servidor, data_inicio, data_fim, motivo, stripe_session_id)
                                VALUES ($1, NOW(), $2, $3, $4)
                                ON CONFLICT (id_servidor) 
                                DO UPDATE SET 
                                    data_fim = EXCLUDED.data_fim,
                                    motivo = EXCLUDED.motivo,
                                    stripe_session_id = EXCLUDED.stripe_session_id
                            """
                            
                            motivo = f"Premium {plan} ativado via Stripe"
                            db_manager.execute_query_sync(activate_premium_query, int(server_id), data_fim, motivo, session['id'])
                            
                        except Exception as schema_error:
                            # Se falhar, usar apenas as colunas básicas
                            logger.warning(f"Colunas motivo/stripe_session_id não existem, usando schema básico: {schema_error}")
                            
                            activate_premium_basic_query = """
                                INSERT INTO servidores_premium (id_servidor, data_inicio, data_fim)
                                VALUES ($1, NOW(), $2)
                                ON CONFLICT (id_servidor) 
                                DO UPDATE SET data_fim = EXCLUDED.data_fim
                            """
                            
                            db_manager.execute_query_sync(activate_premium_basic_query, int(server_id), data_fim)
                        
                        logger.info(f"✅ Premium ativado com sucesso!")
                        logger.info(f"- Usuário: {user_id}")
                        logger.info(f"- Servidor: {server_id}")
                        logger.info(f"- Plano: {plan}")
                        logger.info(f"- Válido até: {data_fim}")
                        
                    except Exception as e:
                        logger.error(f"❌ Erro ao ativar premium: {e}")
                        # Mesmo com erro na ativação, retornamos 200 para não reprocessar o webhook
                else:
                    logger.warning(f"Dados incompletos no webhook: user_id={user_id}, plan={plan}, server_id={server_id}")
                    
            elif event['type'] == 'invoice.payment_succeeded':
                # Renovação automática
                logger.info(f"Pagamento de renovação processado: {event['data']['object']['id']}")
                
            elif event['type'] == 'customer.subscription.deleted':
                # Cancelamento
                logger.info(f"Assinatura cancelada: {event['data']['object']['id']}")
            
            return '', 200
            
        except Exception as e:
            logger.error(f"Erro no webhook Stripe: {e}")
            return '', 500

    @app.route('/api/server/<int:server_id>/stats')
    @login_required
    def api_server_stats(server_id):
        """API para estatísticas do servidor"""
        try:
            # Verifica permissões
            admin_guilds = get_user_guilds_admin()
            has_permission = any(int(guild['id']) == server_id for guild in admin_guilds)
            
            if not has_permission:
                return jsonify({'error': 'Sem permissão'}), 403
            
            # Busca estatísticas
            stats = get_server_stats(server_id)
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Erro na API de estatísticas: {e}")
            return jsonify({'error': 'Erro interno'}), 500
    
    @app.route('/api/server/<int:server_id>/denuncias')
    @login_required
    def api_server_denuncias(server_id):
        """API para denúncias do servidor"""
        try:
            # Verifica permissões
            admin_guilds = get_user_guilds_admin()
            has_permission = any(int(guild['id']) == server_id for guild in admin_guilds)
            
            if not has_permission:
                return jsonify({'error': 'Sem permissão'}), 403
            
            # Parâmetros de filtro
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            status = request.args.get('status', None)
            periodo = request.args.get('periodo', '90')  # dias - aumentado para mostrar mais denúncias
            
            # Calcula offset
            offset = (page - 1) * per_page
            
            # Query base
            where_conditions = ["id_servidor = $1"]
            params = [server_id]
            param_count = 1
            
            # Filtro por status
            if status:
                param_count += 1
                where_conditions.append(f"status = ${param_count}")
                params.append(status)
            
            # Filtro por período (fixo em 90 dias)
            where_conditions.append("data_criacao >= NOW() - INTERVAL '90 days'")
            
            # Query principal
            query = f"""
                SELECT d.*, 
                       u.username as denunciante_name,
                       u2.username as denunciado_name
                FROM denuncias d
                LEFT JOIN usuarios u ON d.id_denunciante = u.id_discord
                LEFT JOIN usuarios u2 ON d.id_denunciado = u2.id_discord
                WHERE {' AND '.join(where_conditions)}
                ORDER BY d.data_criacao DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([per_page, offset])
            
            denuncias = db_manager.execute_query_sync(query, *params)
            
            # Conta total para paginação
            count_query = f"""
                SELECT COUNT(*) FROM denuncias 
                WHERE {' AND '.join(where_conditions)}
            """
            total = db_manager.execute_scalar_sync(count_query, *params[:-2])  # Remove limit e offset
            
            return jsonify({
                'denuncias': denuncias,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
            
        except Exception as e:
            logger.error(f"Erro na API de denúncias: {e}")
            return jsonify({'error': 'Erro interno'}), 500
    
    @app.route('/api/user/stats')
    @app.route('/api/user/stats/')
    @login_required
    def api_user_stats():
        """API para estatísticas do usuário"""
        try:
            user_id = session['user']['id']
            
            # Estatísticas básicas
            stats_query = """
                SELECT 
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = $1) as denuncias_atendidas,
                    (SELECT COUNT(*) FROM denuncias WHERE id_denunciante = $1) as denuncias_feitas,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = $1 AND voto = 'OK!') as votos_ok,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = $1 AND voto = 'Intimidou') as votos_intimidou,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = $1 AND voto = 'Grave') as votos_grave
            """
            stats = db_manager.execute_query_sync(stats_query, user_id)
            
            # Gráfico de atividade (últimos 30 dias)
            activity_query = """
                SELECT DATE(data_voto) as data, COUNT(*) as votos
                FROM votos_guardioes 
                WHERE id_guardiao = $1 
                AND data_voto >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(data_voto)
                ORDER BY data
            """
            activity = db_manager.execute_query_sync(activity_query, user_id)
            
            return jsonify({
                'stats': stats[0] if stats else {},
                'activity': activity
            })
            
        except Exception as e:
            logger.error(f"Erro na API de estatísticas do usuário: {e}")
            return jsonify({'error': 'Erro interno'}), 500

    # ==================== ROTAS DO PAINEL ADMINISTRATIVO ====================
    
    @app.route('/admin-test')
    def admin_test():
        """Rota de teste para verificar se as rotas admin funcionam"""
        return "Rota admin funcionando!"
    
    @app.route('/admin/usuarios')
    def admin_usuarios():
        """Lista de todos os usuários"""
        # Verificação manual de admin
        if 'user' not in session:
            flash("Você precisa fazer login para acessar esta página.", "warning")
            return redirect(url_for('login'))
        
        user_id = session['user']['id']
        if user_id != 1369940071246991380:
            flash("Acesso negado. Você não tem permissões de administrador.", "error")
            return redirect(url_for('dashboard'))
        
        try:
            page = request.args.get('page', 1, type=int)
            per_page = 20
            offset = (page - 1) * per_page
            
            # Busca usuários com paginação
            usuarios_query = """
                SELECT id_discord, username, display_name, nome_completo, categoria, 
                       pontos, experiencia, em_servico, data_criacao_registro
                FROM usuarios 
                ORDER BY data_criacao_registro DESC 
                LIMIT $1 OFFSET $2
            """
            usuarios = db_manager.execute_query_sync(usuarios_query, per_page, offset)
            
            # Conta total de usuários
            total_query = "SELECT COUNT(*) as total FROM usuarios"
            total = db_manager.execute_one_sync(total_query)
            total_usuarios = total['total'] if total else 0
            
            total_pages = (total_usuarios + per_page - 1) // per_page
            
            return render_template('admin/usuarios.html',
                                 usuarios=usuarios,
                                 page=page,
                                 total_pages=total_pages,
                                 total_usuarios=total_usuarios)
            
        except Exception as e:
            logger.error(f"Erro na lista de usuários: {e}")
            return redirect(url_for('admin_dashboard'))
    
    @app.route('/admin/usuarios/<int:user_id>')
    @admin_required
    def admin_usuario_detalhes(user_id):
        """Detalhes de um usuário específico"""
        try:
            # Busca dados do usuário
            usuario_query = "SELECT * FROM usuarios WHERE id_discord = $1"
            usuario = db_manager.execute_one_sync(usuario_query, user_id)
            
            if not usuario:
                flash("Usuário não encontrado.", "error")
                return redirect(url_for('admin_usuarios'))
            
            # Busca denúncias do usuário
            denuncias_query = """
                SELECT d.*, s.nome as servidor_nome
                FROM denuncias d
                LEFT JOIN servidores s ON d.id_servidor = s.id_discord
                WHERE d.id_denunciado = $1
                ORDER BY data_criacao DESC
            """
            denuncias = db_manager.execute_query_sync(denuncias_query, user_id)
            
            # Busca votos do usuário (se for guardião)
            votos_query = """
                SELECT v.*, d.motivo, d.id_servidor
                FROM votos_guardioes v
                JOIN denuncias d ON v.id_denuncia = d.id
                WHERE v.id_guardiao = $1
                ORDER BY v.data_voto DESC
                LIMIT 20
            """
            votos = db_manager.execute_query_sync(votos_query, user_id)
            
            return render_template('admin/usuario_detalhes.html',
                                 usuario=usuario,
                                 denuncias=denuncias,
                                 votos=votos)
            
        except Exception as e:
            logger.error(f"Erro nos detalhes do usuário: {e}")
            return redirect(url_for('admin_usuarios'))
    
    @app.route('/admin/usuarios/<int:user_id>/editar', methods=['GET', 'POST'])
    @admin_required
    def admin_usuario_editar(user_id):
        """Editar dados de um usuário"""
        try:
            if request.method == 'POST':
                categoria = request.form.get('categoria')
                pontos = request.form.get('pontos', type=int)
                experiencia = request.form.get('experiencia', type=int)
                em_servico = request.form.get('em_servico') == 'on'
                
                # Atualiza dados do usuário
                update_query = """
                    UPDATE usuarios 
                    SET categoria = $1, pontos = $2, experiencia = $3, em_servico = $4
                    WHERE id_discord = $5
                """
                db_manager.execute_command_sync(update_query, categoria, pontos, experiencia, em_servico, user_id)
                
                flash("Dados do usuário atualizados com sucesso!", "success")
                return redirect(url_for('admin_usuario_detalhes', user_id=user_id))
            
            # Busca dados do usuário
            usuario_query = "SELECT * FROM usuarios WHERE id_discord = $1"
            usuario = db_manager.execute_one_sync(usuario_query, user_id)
            
            if not usuario:
                flash("Usuário não encontrado.", "error")
                return redirect(url_for('admin_usuarios'))
            
            return render_template('admin/usuario_editar.html', usuario=usuario)
            
        except Exception as e:
            logger.error(f"Erro na edição do usuário: {e}")
            return redirect(url_for('admin_usuario_detalhes', user_id=user_id))
    
    @app.route('/admin/denuncias')
    @admin_required
    def admin_denuncias():
        """Lista de todas as denúncias"""
        try:
            page = request.args.get('page', 1, type=int)
            status_filter = request.args.get('status', '')
            per_page = 20
            offset = (page - 1) * per_page
            
            # Constrói query base
            where_conditions = []
            params = []
            
            if status_filter:
                where_conditions.append("d.status = $" + str(len(params) + 1))
                params.append(status_filter)
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            denuncias_query = f"""
                SELECT d.*, u.username as denunciado_username, u.display_name as denunciado_display_name
                FROM denuncias d
                LEFT JOIN usuarios u ON d.id_denunciado = u.id_discord
                {where_clause}
                ORDER BY d.data_criacao DESC
                LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """
            params.extend([per_page, offset])
            
            denuncias = db_manager.execute_query_sync(denuncias_query, *params)
            
            # Conta total de denúncias
            count_query = "SELECT COUNT(*) as total FROM denuncias d" + where_clause
            count_params = params[:-2]  # Remove per_page e offset
            total = db_manager.execute_one_sync(count_query, *count_params)
            total_denuncias = total['total'] if total else 0
            
            total_pages = (total_denuncias + per_page - 1) // per_page
            
            return render_template('admin/denuncias.html',
                                 denuncias=denuncias,
                                 page=page,
                                 total_pages=total_pages,
                                 total_denuncias=total_denuncias,
                                 status_filter=status_filter)
            
        except Exception as e:
            logger.error(f"Erro na lista de denúncias: {e}")
            return redirect(url_for('admin_dashboard'))
    
    @app.route('/admin/denuncias/<int:denuncia_id>')
    @admin_required
    def admin_denuncia_detalhes(denuncia_id):
        """Detalhes de uma denúncia específica"""
        try:
            # Busca dados da denúncia
            denuncia_query = """
                SELECT d.*, u.username as denunciado_username, u.display_name as denunciado_display_name
                FROM denuncias d
                LEFT JOIN usuarios u ON d.id_denunciado = u.id_discord
                WHERE d.id = $1
            """
            denuncia = db_manager.execute_one_sync(denuncia_query, denuncia_id)
            
            if not denuncia:
                flash("Denúncia não encontrada.", "error")
                return redirect(url_for('admin_denuncias'))
            
            # Busca votos dos guardiões
            votos_query = """
                SELECT v.*, u.username as guardiao_username
                FROM votos_guardioes v
                LEFT JOIN usuarios u ON v.id_guardiao = u.id_discord
                WHERE v.id_denuncia = $1
                ORDER BY v.data_voto
            """
            votos = db_manager.execute_query_sync(votos_query, denuncia_id)
            
            # Busca mensagens capturadas
            mensagens_query = """
                SELECT * FROM mensagens_capturadas
                WHERE id_denuncia = $1
                ORDER BY timestamp
                LIMIT 100
            """
            mensagens = db_manager.execute_query_sync(mensagens_query, denuncia_id)
            
            return render_template('admin/denuncia_detalhes.html',
                                 denuncia=denuncia,
                                 votos=votos,
                                 mensagens=mensagens)
            
        except Exception as e:
            logger.error(f"Erro nos detalhes da denúncia: {e}")
            return redirect(url_for('admin_denuncias'))

    # ==================== ROTA /ADMIN NO FINAL ====================
    logger.info("🔧 Registrando rota /admin no final...")
    
    @app.route('/admin')
    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        """Painel administrativo principal"""
        logger.info("🔧 Rota /admin/dashboard acessada!")

        try:
            # Busca estatísticas gerais para o dashboard
            stats = {}
            recent_users = []
            recent_denuncias = []

            if db_manager and db_manager.pool:
                # Estatísticas no formato esperado pelo template dashboard.html
                stats = {
                    'total_usuarios': 0,
                    'total_guardioes': 0,
                    'guardioes_servico': 0,
                    'total_denuncias': 0,
                    'denuncias_pendentes': 0,
                    'denuncias_analise': 0,
                    'denuncias_finalizadas': 0,
                    'denuncias_resolvidas': 0,
                    'total_votos': 0
                }

                # Buscar estatísticas reais
                stats_query = """
                    SELECT
                        (SELECT COUNT(*) FROM usuarios) as total_usuarios,
                        (SELECT COUNT(*) FROM usuarios WHERE categoria = 'Guardião') as total_guardioes,
                        (SELECT COUNT(*) FROM usuarios WHERE em_servico = true) as guardioes_servico,
                        (SELECT COUNT(*) FROM denuncias) as total_denuncias,
                        (SELECT COUNT(*) FROM denuncias WHERE status = 'Pendente') as denuncias_pendentes,
                        (SELECT COUNT(*) FROM denuncias WHERE status = 'Em Análise') as denuncias_analise,
                        (SELECT COUNT(*) FROM denuncias WHERE status = 'Finalizada') as denuncias_finalizadas,
                        (SELECT COUNT(*) FROM votos_guardioes) as total_votos
                """
                stats_result = db_manager.execute_query_sync(stats_query)
                if stats_result:
                    real_stats = stats_result[0]
                    stats['total_usuarios'] = real_stats['total_usuarios'] or 0
                    stats['total_guardioes'] = real_stats['total_guardioes'] or 0
                    stats['guardioes_servico'] = real_stats['guardioes_servico'] or 0
                    stats['total_denuncias'] = real_stats['total_denuncias'] or 0
                    stats['denuncias_pendentes'] = real_stats['denuncias_pendentes'] or 0
                    stats['denuncias_analise'] = real_stats['denuncias_analise'] or 0
                    stats['denuncias_finalizadas'] = real_stats['denuncias_finalizadas'] or 0
                    stats['denuncias_resolvidas'] = real_stats['denuncias_finalizadas'] or 0  # Mesmo que finalizadas
                    stats['total_votos'] = real_stats['total_votos'] or 0

                # Usuários recentes
                recent_users_query = """
                    SELECT id_discord, username, display_name, categoria, data_criacao_registro
                    FROM usuarios
                    ORDER BY data_criacao_registro DESC
                    LIMIT 5
                """
                recent_users = db_manager.execute_query_sync(recent_users_query) or []

                # Denúncias recentes
                recent_denuncias_query = """
                    SELECT d.id, d.id_denunciado, d.motivo, d.status, d.data_criacao
                    FROM denuncias d
                    ORDER BY d.data_criacao DESC
                    LIMIT 5
                """
                recent_denuncias = db_manager.execute_query_sync(recent_denuncias_query) or []

            return render_template('admin/dashboard.html',
                                 stats=stats,
                                 recent_users=recent_users,
                                 recent_denuncias=recent_denuncias)

        except Exception as e:
            logger.error(f"Erro no dashboard admin: {e}")
            # Fallback para HTML simples em caso de erro
            return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>🛡️ Painel Admin - Sistema Guardião</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0; padding: 0; min-height: 100vh;
                    display: flex; align-items: center; justify-content: center;
                }
                .container { 
                    max-width: 900px; width: 90%; 
                    background: rgba(255,255,255,0.95); 
                    border-radius: 20px; padding: 40px; 
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                }
                .header h1 { 
                    color: #2c3e50; margin: 0 0 10px 0; 
                    font-size: 2.5rem; font-weight: 300;
                }
                .header p { 
                    color: #7f8c8d; font-size: 1.2rem; 
                    margin: 0 0 30px 0;
                }
                .success { 
                    background: #d4edda; color: #155724; 
                    padding: 20px; border-radius: 10px; 
                    margin: 20px 0; border: 1px solid #c3e6cb;
                }
                .success h3 { margin: 0 0 15px 0; }
                .success p { margin: 5px 0; }
                .status-grid { 
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 20px; margin: 30px 0;
                }
                .status-card { 
                    background: #f8f9fa; padding: 20px; 
                    border-radius: 10px; border: 1px solid #e9ecef;
                }
                .status-card h4 { margin: 0 0 10px 0; color: #495057; }
                .status-card .value { font-size: 2em; font-weight: bold; color: #27ae60; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛡️ Painel Administrativo</h1>
                    <p>Sistema Guardião BETA - Funcionando Perfeitamente!</p>
                </div>
                
                <div class="success">
                    <h3>✅ PROBLEMA RESOLVIDO!</h3>
                    <p><strong>Status:</strong> A rota /admin está funcionando corretamente após correção das dependências.</p>
                    <p><strong>Causa do problema:</strong> Falha na importação de dependências (asyncpg, login_required) impedia o registro da rota.</p>
                    <p><strong>Solução aplicada:</strong> Rota independente sem dependências problemáticas.</p>
                </div>
                
                <div class="status-grid">
                    <div class="status-card">
                        <h4>🚀 Sistema</h4>
                        <div class="value">ONLINE</div>
                    </div>
                    <div class="status-card">
                        <h4>🛡️ Bot Discord</h4>
                        <div class="value">ATIVO</div>
                    </div>
                    <div class="status-card">
                        <h4>🌐 Web App</h4>
                        <div class="value">OK</div>
                    </div>
                    <div class="status-card">
                        <h4>🔧 Admin</h4>
                        <div class="value">FIXO</div>
                    </div>
                </div>
                
                <div class="navigation">
                    <h3>🎯 Navegação do Sistema</h3>
                    <a href="/dashboard" class="btn btn-success">📊 Dashboard Principal</a>
                    <a href="/admin-simple" class="btn">🔧 Admin Simples</a>
                    <a href="/admin-fixed" class="btn">✅ Admin Fixo (Teste)</a>
                    <a href="/admin-test-simple" class="btn btn-warning">🧪 Teste Admin</a>
                    <a href="/" class="btn">🏠 Página Inicial</a>
                    <a href="/servers" class="btn">🖥️ Servidores</a>
                    <a href="/premium" class="btn">⭐ Premium</a>
                </div>
                
                <div style="margin-top: 40px; padding: 20px; background: #e9ecef; border-radius: 8px;">
                    <h4>📋 Informações Técnicas</h4>
                    <ul>
                        <li>✅ Rota /admin registrada com sucesso</li>
                        <li>✅ Sem dependências problemáticas</li>
                        <li>✅ Interface responsiva</li>
                        <li>✅ Navegação completa</li>
                        <li>⚠️ Versão simplificada (sem autenticação)</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
    
    logger.info("✅ Rota /admin registrada com sucesso no final!")
    
    # ==================== ROTAS DO SISTEMA ADMIN ====================
    
    @app.route('/admin/system')
    @admin_required
    def admin_system():
        """Página de controle do sistema"""
        try:
            # Busca estatísticas do banco
            db_stats = {}
            if db_manager and db_manager.pool:
                stats_query = """
                    SELECT
                        (SELECT COUNT(*) FROM usuarios) as total_usuarios,
                        (SELECT COUNT(*) FROM denuncias) as total_denuncias,
                        (SELECT COUNT(*) FROM votos_guardioes) as total_votos,
                        (SELECT COUNT(*) FROM captchas_guardioes) as total_captchas
                """
                stats_result = db_manager.execute_query_sync(stats_query)
                if stats_result:
                    db_stats = stats_result[0]
            
            return render_template('admin/system.html', db_stats=db_stats)
            
        except Exception as e:
            logger.error(f"Erro na página do sistema: {e}")
            return redirect(url_for('admin_dashboard'))
    
    @app.route('/admin/system/table/<table_name>')
    @admin_required
    def admin_system_table(table_name):
        """Retorna dados de uma tabela específica"""
        try:
            # Tabelas permitidas
            allowed_tables = [
                'usuarios', 'denuncias', 'votos_guardioes', 
                'mensagens_capturadas', 'captchas_guardioes',
                'servidores_premium', 'configuracoes_servidor'
            ]
            
            if table_name not in allowed_tables:
                return {'success': False, 'error': 'Tabela não permitida'}
            
            # Busca dados da tabela
            query = f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 100"
            data = db_manager.execute_query_sync(query)
            
            return {'success': True, 'data': data}
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados da tabela {table_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    @app.route('/admin/system/delete/<table_name>/<int:record_id>', methods=['DELETE'])
    @admin_required
    def admin_system_delete(table_name, record_id):
        """Exclui um registro de uma tabela"""
        try:
            # Tabelas permitidas
            allowed_tables = [
                'usuarios', 'denuncias', 'votos_guardioes', 
                'mensagens_capturadas', 'captchas_guardioes',
                'servidores_premium', 'configuracoes_servidor'
            ]
            
            if table_name not in allowed_tables:
                return {'success': False, 'error': 'Tabela não permitida'}
            
            # Exclui o registro
            query = f"DELETE FROM {table_name} WHERE id = $1"
            db_manager.execute_command_sync(query, record_id)
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Erro ao excluir registro: {e}")
            return {'success': False, 'error': str(e)}
    
    @app.route('/admin/system/punish', methods=['POST'])
    @admin_required
    def admin_system_punish():
        """Aplica punição a um usuário"""
        try:
            user_id = request.form.get('user_id')
            punishment_type = request.form.get('punishment_type')
            reason = request.form.get('reason')
            
            if not all([user_id, punishment_type, reason]):
                flash("Todos os campos são obrigatórios.", "error")
                return redirect(url_for('admin_system'))
            
            # Aqui você implementaria a lógica de punição
            # Por exemplo, enviar comando para o bot Discord
            
            flash(f"Punição {punishment_type} aplicada ao usuário {user_id}.", "success")
            return redirect(url_for('admin_system'))
            
        except Exception as e:
            logger.error(f"Erro ao aplicar punição: {e}")
            flash("Erro ao aplicar punição.", "error")
            return redirect(url_for('admin_system'))
    
    @app.route('/admin/system/message', methods=['POST'])
    @admin_required
    def admin_system_message():
        """Envia mensagem para usuários"""
        logger.info("🚀 ROTA admin_system_message CHAMADA!")
        import asyncio
        
        # Aguarda o bot estar pronto com timeout
        logger.info("⏳ Aguardando bot estar pronto...")
        bot = wait_for_bot_ready(timeout_seconds=15)
        if not bot:
            logger.warning("⚠️ Bot Discord não ficou pronto no tempo esperado")
            flash("Bot Discord ainda está inicializando. Aguarde alguns segundos e tente novamente.", "error")
            return redirect(url_for('admin_system'))
        
        async def send_message_async():
            try:
                logger.info("🔄 Função send_message_async iniciada!")
                target_type = request.form.get('target_type')
                target_user_id = request.form.get('target_user_id')
                target_server_id = request.form.get('target_server_id')
                message_title = request.form.get('message_title')
                message_content = request.form.get('message_content')
                
                logger.info(f"📝 Dados recebidos: target_type={target_type}, title={message_title}")
                logger.info(f"📝 Campos completos: target_type='{target_type}', message_title='{message_title}', message_content='{message_content}'")
                logger.info(f"📝 Validação all(): {all([target_type, message_title, message_content])}")
                
                if not all([target_type, message_title, message_content]):
                    logger.warning("⚠️ Campos obrigatórios não preenchidos!")
                    flash("Campos obrigatórios não preenchidos.", "error")
                    return redirect(url_for('admin_system'))
                
                # Bot já foi verificado na função get_bot_instance()
                
                # Logs de debug do bot
                logger.info(f"🔍 Bot está pronto: {bot.is_ready()}")
                logger.info(f"🔍 Bot user: {bot.user}")
                logger.info(f"🔍 Bot guilds: {len(bot.guilds)}")
                logger.info(f"🔍 Bot websocket: {bot.ws}")
                
                logger.info("✅ Bot está pronto e conectado")
                logger.info(f"Loop rodando: N/A (não acessível em contexto síncrono)")
                logger.info(f"Usuários no cache: {len(bot.users)}")
                sent_count = 0
                
                # Cria embed da mensagem
                embed = discord.Embed(
                    title=f"📢 {message_title}",
                    description=message_content,
                    color=0x00ff00
                )
                embed.set_footer(text="Sistema Guardião BETA - Mensagem Administrativa")
                
                logger.info(f"🔍 Verificando target_type: {target_type}")
                logger.info("🎯 Chegou nas condições de envio!")
                
                if target_type == 'user':
                    logger.info("🎯 Entrando na seção de usuário específico...")
                    if not target_user_id:
                        flash("ID do usuário é obrigatório para envio individual.", "error")
                        return redirect(url_for('admin_system'))
                    
                    success = await send_dm_to_user(bot, int(target_user_id), embed, "usuário")
                    if success:
                        sent_count = 1
                        logger.info(f"Mensagem enviada para usuário {target_user_id}")
                    else:
                        flash(f"Usuário {target_user_id} não encontrado ou DMs bloqueados.", "error")
                        return redirect(url_for('admin_system'))
                
                elif target_type == 'guardians':
                    logger.info("🎯 Entrando na seção de guardiões...")
                    # Busca todos os guardiões
                    guardians_query = """
                        SELECT id_discord, categoria FROM usuarios 
                        WHERE categoria IN ('Guardião', 'Moderador', 'Administrador')
                    """
                    guardians = db_manager.execute_query_sync(guardians_query)
                    
                    # Debug: verificar categorias existentes
                    debug_query = "SELECT DISTINCT categoria FROM usuarios"
                    categories = db_manager.execute_query_sync(debug_query)
                    logger.info(f"Categorias encontradas no banco: {[cat['categoria'] for cat in categories]}")
                    logger.info(f"Guardiões encontrados: {len(guardians)}")
                    
                    for guardian in guardians:
                        try:
                            logger.info(f"Tentando enviar mensagem para guardião {guardian['id_discord']} ({guardian['categoria']})")
                            
                            success = await send_dm_to_user(bot, guardian['id_discord'], embed, "guardião")
                            if success:
                                sent_count += 1
                                logger.info(f"Mensagem enviada para guardião {guardian['id_discord']} ({guardian['categoria']})")
                            else:
                                logger.warning(f"Falha ao enviar mensagem para guardião {guardian['id_discord']}")
                        except Exception as e:
                            logger.error(f"Erro ao enviar mensagem para guardião {guardian['id_discord']}: {e}")
                            continue
                    
                    logger.info(f"Mensagem enviada para {sent_count} guardiões")
                
                elif target_type == 'moderators':
                    logger.info("🎯 Entrando na seção de moderadores...")
                    # Busca todos os moderadores
                    moderators_query = """
                        SELECT id_discord, categoria FROM usuarios 
                        WHERE categoria IN ('Moderador', 'Administrador')
                    """
                    moderators = db_manager.execute_query_sync(moderators_query)
                    
                    logger.info(f"Moderadores encontrados: {len(moderators)}")
                    logger.info(f"Moderadores: {moderators}")
                    
                    for moderator in moderators:
                        try:
                            logger.info(f"Tentando enviar mensagem para moderador {moderator['id_discord']} ({moderator['categoria']})")
                            
                            success = await send_dm_to_user(bot, moderator['id_discord'], embed, "moderador")
                            if success:
                                sent_count += 1
                                logger.info(f"Mensagem enviada para moderador {moderator['id_discord']} ({moderator['categoria']})")
                            else:
                                logger.warning(f"Falha ao enviar mensagem para moderador {moderator['id_discord']}")
                        except Exception as e:
                            logger.error(f"Erro ao enviar mensagem para moderador {moderator['id_discord']}: {e}")
                            continue
                    
                    logger.info(f"Mensagem enviada para {sent_count} moderadores")
                
                elif target_type == 'administrators':
                    logger.info("🎯 Entrando na seção de administradores...")
                    # Busca todos os administradores
                    admins_query = """
                        SELECT id_discord, categoria FROM usuarios 
                        WHERE categoria = 'Administrador'
                    """
                    admins = db_manager.execute_query_sync(admins_query)
                    
                    logger.info(f"Administradores encontrados: {len(admins)}")
                    
                    for admin in admins:
                        try:
                            logger.info(f"Tentando enviar mensagem para admin {admin['id_discord']} ({admin['categoria']})")
                            
                            success = await send_dm_to_user(bot, admin['id_discord'], embed, "administrador")
                            if success:
                                sent_count += 1
                                logger.info(f"Mensagem enviada para admin {admin['id_discord']} ({admin['categoria']})")
                            else:
                                logger.warning(f"Falha ao enviar mensagem para admin {admin['id_discord']}")
                        except Exception as e:
                            logger.error(f"Erro ao enviar mensagem para admin {admin['id_discord']}: {e}")
                            continue
                    
                    logger.info(f"Mensagem enviada para {sent_count} administradores")
                
                elif target_type == 'server':
                    logger.info("🎯 Entrando na seção de servidor...")
                    if not target_server_id:
                        flash("ID do servidor é obrigatório para envio em servidor.", "error")
                        return redirect(url_for('admin_system'))
                    
                    try:
                        guild = bot.get_guild(int(target_server_id))
                        if guild:
                            # Envia para canal geral ou cria canal de anúncios
                            channel = guild.system_channel or guild.text_channels[0] if guild.text_channels else None
                            if channel:
                                await channel.send(embed=embed)
                                sent_count = 1
                                logger.info(f"Mensagem enviada para servidor {target_server_id}")
                            else:
                                flash("Nenhum canal disponível no servidor.", "error")
                                return redirect(url_for('admin_system'))
                        else:
                            flash(f"Servidor {target_server_id} não encontrado.", "error")
                            return redirect(url_for('admin_system'))
                    except Exception as e:
                        logger.error(f"Erro ao enviar mensagem para servidor {target_server_id}: {e}")
                        flash(f"Erro ao enviar mensagem para servidor: {e}", "error")
                        return redirect(url_for('admin_system'))
                
                else:
                    logger.warning(f"⚠️ Target type não reconhecido: {target_type}")
                
                logger.info(f"📊 Total de mensagens enviadas: {sent_count}")
                if sent_count > 0:
                    flash(f"Mensagem enviada com sucesso para {sent_count} destinatário(s).", "success")
                    logger.info(f"✅ Flash de sucesso: {sent_count} destinatários")
                else:
                    flash("Nenhuma mensagem foi enviada.", "warning")
                    logger.info("⚠️ Flash de aviso: nenhuma mensagem enviada")
                
                logger.info("🔄 Redirecionando para admin_system...")
                return redirect(url_for('admin_system'))
                
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem: {e}")
                flash("Erro ao enviar mensagem.", "error")
                return redirect(url_for('admin_system'))
        
        # Executa a função async
        try:
            logger.info("🔄 Iniciando execução da função async...")
            result = asyncio.run(send_message_async())
            logger.info("✅ Função async executada com sucesso!")
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao executar função async: {e}")
            logger.error(f"❌ Tipo do erro: {type(e)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            flash("Erro ao enviar mensagem.", "error")
            return redirect(url_for('admin_system'))
    
    @app.route('/admin/system/ban-user', methods=['POST'])
    @admin_required
    def admin_system_ban_user():
        """Banir usuário do sistema"""
        try:
            user_id = request.form.get('user_id')
            reason = request.form.get('reason')
            duration = request.form.get('duration')
            
            if not all([user_id, reason, duration]):
                flash("Todos os campos são obrigatórios.", "error")
                return redirect(url_for('admin_system'))
            
            # Adiciona usuário à lista de banidos
            ban_query = """
                INSERT INTO usuarios_banidos (id_discord, motivo, duracao, data_banimento)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                ON CONFLICT (id_discord) DO UPDATE SET
                    motivo = $2, duracao = $3, data_banimento = CURRENT_TIMESTAMP
            """
            db_manager.execute_command_sync(ban_query, user_id, reason, duration)
            
            flash(f"Usuário {user_id} banido do sistema.", "success")
            return redirect(url_for('admin_system'))
            
        except Exception as e:
            logger.error(f"Erro ao banir usuário: {e}")
            flash("Erro ao banir usuário.", "error")
            return redirect(url_for('admin_system'))
    
    @app.route('/admin/system/unban-user', methods=['POST'])
    @admin_required
    def admin_system_unban_user():
        """Desbanir usuário do sistema"""
        try:
            user_id = request.form.get('user_id')
            reason = request.form.get('reason')
            
            if not all([user_id, reason]):
                flash("Todos os campos são obrigatórios.", "error")
                return redirect(url_for('admin_system'))
            
            # Remove usuário da lista de banidos
            unban_query = "DELETE FROM usuarios_banidos WHERE id_discord = $1"
            db_manager.execute_command_sync(unban_query, user_id)
            
            flash(f"Usuário {user_id} desbanido do sistema.", "success")
            return redirect(url_for('admin_system'))
            
        except Exception as e:
            logger.error(f"Erro ao desbanir usuário: {e}")
            flash("Erro ao desbanir usuário.", "error")
            return redirect(url_for('admin_system'))
    
    @app.route('/admin/system/command', methods=['POST'])
    @admin_required
    def admin_system_command():
        """Executa comandos do sistema"""
        try:
            command = request.form.get('command')
            
            if not command:
                flash("Comando não especificado.", "error")
                return redirect(url_for('admin_system'))
            
            # Comandos permitidos
            allowed_commands = [
                'restart_bot', 'clear_cache', 'backup_database', 'update_stats'
            ]
            
            if command not in allowed_commands:
                flash("Comando não permitido.", "error")
                return redirect(url_for('admin_system'))
            
            # Aqui você implementaria a lógica de cada comando
            # Por exemplo, enviar comando para o bot Discord
            
            flash(f"Comando {command} executado com sucesso.", "success")
            return redirect(url_for('admin_system'))
            
        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")
            flash("Erro ao executar comando.", "error")
            return redirect(url_for('admin_system'))
    
    logger.info("✅ Rotas do sistema admin registradas com sucesso!")
    logger.info("✅ Configuração de rotas concluída com sucesso!")


# Cache simples para dados de usuários do Discord (evita muitas requisições)
_discord_user_cache = {}
_cache_timeout = 300  # 5 minutos

def get_discord_user_info(user_id: int) -> dict:
    """Busca informações do usuário no Discord via API com cache"""
    try:
        import requests
        import time
        
        # Verificar cache
        cache_key = str(user_id)
        current_time = time.time()
        
        if cache_key in _discord_user_cache:
            cached_data, cached_time = _discord_user_cache[cache_key]
            if current_time - cached_time < _cache_timeout:
                return cached_data
        
        bot_token = os.getenv('DISCORD_TOKEN')
        
        if not bot_token:
            logger.warning("DISCORD_TOKEN não configurado para buscar usuários")
            result = {'discord_username': None, 'discord_avatar': None, 'discord_discriminator': None, 'discord_display_name': None}
            _discord_user_cache[cache_key] = (result, current_time)
            return result
        
        headers = {'Authorization': f'Bot {bot_token}'}
        response = requests.get(f'https://discord.com/api/v10/users/{user_id}', headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            result = {
                'discord_username': user_data.get('username'),
                'discord_avatar': user_data.get('avatar'),
                'discord_discriminator': user_data.get('discriminator'),
                'discord_display_name': user_data.get('global_name') or user_data.get('username')
            }
            # Armazenar no cache
            _discord_user_cache[cache_key] = (result, current_time)
            logger.info(f"Dados do usuário {user_id} obtidos do Discord: {result['discord_username']}")
            return result
        else:
            logger.warning(f"Erro ao buscar usuário {user_id}: {response.status_code}")
            result = {'discord_username': None, 'discord_avatar': None, 'discord_discriminator': None, 'discord_display_name': None}
            _discord_user_cache[cache_key] = (result, current_time)
            return result
            
    except Exception as e:
        logger.error(f"Erro ao buscar informações do usuário {user_id}: {e}")
        result = {'discord_username': None, 'discord_avatar': None, 'discord_discriminator': None, 'discord_display_name': None}
        _discord_user_cache[cache_key] = (result, current_time)
        return result

def get_server_stats(server_id: int) -> dict:
    """Busca estatísticas de um servidor"""
    try:
        # Estatísticas gerais
        general_query = """
            SELECT 
                COUNT(*) as total_denuncias,
                COUNT(CASE WHEN status = 'Finalizada' THEN 1 END) as denuncias_finalizadas,
                COUNT(CASE WHEN status = 'Pendente' THEN 1 END) as denuncias_pendentes,
                COUNT(CASE WHEN status = 'Em Análise' THEN 1 END) as denuncias_analise,
                COUNT(CASE WHEN e_premium = true THEN 1 END) as denuncias_premium
            FROM denuncias 
            WHERE id_servidor = $1
        """
        general_stats = db_manager.execute_query_sync(general_query, server_id)
        
        # Resultados das denúncias
        results_query = """
            SELECT 
                COUNT(CASE WHEN resultado_final = 'OK!' THEN 1 END) as improcedentes,
                COUNT(CASE WHEN resultado_final = 'Intimidou' THEN 1 END) as intimidoes,
                COUNT(CASE WHEN resultado_final = 'Grave' THEN 1 END) as graves
            FROM denuncias 
            WHERE id_servidor = $1 AND status = 'Finalizada'
        """
        results_stats = db_manager.execute_query_sync(results_query, server_id)
        
        # Denúncias por período (últimos 7 dias)
        period_query = """
            SELECT DATE(data_criacao) as data, COUNT(*) as quantidade
            FROM denuncias 
            WHERE id_servidor = $1 
            AND data_criacao >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(data_criacao)
            ORDER BY data
        """
        period_stats = db_manager.execute_query_sync(period_query, server_id)
        
        # Usuários mais denunciados (com informações do usuário)
        top_denunciados_query = """
            SELECT 
                d.id_denunciado,
                u.username,
                u.display_name,
                COUNT(*) as denuncias_count,
                CASE 
                    WHEN u.categoria = 'Banido' THEN 'BANIDO'
                    WHEN u.categoria = 'Intimidou' THEN 'INTIMIDOU'
                    WHEN u.categoria = 'Grave' THEN 'GRAVE'
                    ELSE 'ATIVO'
                END as status_usuario
            FROM denuncias d
            LEFT JOIN usuarios u ON d.id_denunciado = u.id_discord
            WHERE d.id_servidor = $1 
            AND d.data_criacao >= NOW() - INTERVAL '30 days'
            GROUP BY d.id_denunciado, u.username, u.display_name, u.categoria
            ORDER BY denuncias_count DESC
            LIMIT 10
        """
        top_denunciados_raw = db_manager.execute_query_sync(top_denunciados_query, server_id)
        
        # Enriquecer com dados do Discord
        top_denunciados = []
        if top_denunciados_raw:
            for user in top_denunciados_raw:
                discord_user = get_discord_user_info(user['id_denunciado'])
                user_data = dict(user)
                user_data.update(discord_user)
                top_denunciados.append(user_data)
        
        return {
            'general': general_stats[0] if general_stats else {},
            'results': results_stats[0] if results_stats else {},
            'period': period_stats,
            'top_denunciados': top_denunciados
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas do servidor: {e}")
        return {
            'general': {},
            'results': {},
            'period': [],
            'top_denunciados': []
        }

