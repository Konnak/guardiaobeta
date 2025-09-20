"""
Rotas da Aplicação Web - Sistema Guardião BETA
Implementa todas as rotas principais do site
"""

import logging
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from database.connection import db_manager
from utils.experience_system import get_experience_rank, get_rank_emoji, format_experience_display
from web.auth import login_required, admin_required, get_user_guilds_admin, get_bot_invite_url, get_user_avatar_url, get_guild_icon_url

# Configuração de logging
logger = logging.getLogger(__name__)


def setup_routes(app):
    """Configura todas as rotas da aplicação"""
    
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
            
            # Busca informações de premium para cada servidor
            servers_info = []
            for guild in admin_guilds:
                premium_query = """
                    SELECT * FROM servidores_premium 
                    WHERE id_servidor = $1 AND data_fim > NOW()
                """
                premium_data = db_manager.execute_one_sync(premium_query, int(guild['id']))
                
                servers_info.append({
                    'guild': guild,
                    'is_premium': premium_data is not None,
                    'premium_data': premium_data,
                    'icon_url': get_guild_icon_url(guild['id'], guild.get('icon'))
                })
            
            return render_template('servers.html',
                                 user=user_data,
                                 servers=servers_info,
                                 avatar_url=get_user_avatar_url(str(user_data['id']), user_data.get('avatar'), user_data.get('discriminator')))
            
        except Exception as e:
            logger.error(f"Erro na lista de servidores: {e}")
            flash("Erro ao carregar lista de servidores.", "error")
            return redirect(url_for('dashboard'))
    
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
            periodo = request.args.get('periodo', '30')  # dias
            
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
            
            # Filtro por período
            param_count += 1
            where_conditions.append(f"data_criacao >= NOW() - INTERVAL '{periodo} days'")
            
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
        
        # Usuários mais denunciados
        top_denunciados_query = """
            SELECT id_denunciado, COUNT(*) as denuncias_count
            FROM denuncias 
            WHERE id_servidor = $1 
            AND data_criacao >= NOW() - INTERVAL '30 days'
            GROUP BY id_denunciado
            ORDER BY denuncias_count DESC
            LIMIT 10
        """
        top_denunciados = db_manager.execute_query_sync(top_denunciados_query, server_id)
        
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

    # ==================== ROTAS DO PAINEL ADMINISTRATIVO ====================
    
    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        """Painel administrativo principal"""
        try:
            # Estatísticas gerais
            stats_query = """
                SELECT 
                    (SELECT COUNT(*) FROM usuarios) as total_usuarios,
                    (SELECT COUNT(*) FROM usuarios WHERE categoria = 'Guardião') as total_guardioes,
                    (SELECT COUNT(*) FROM denuncias) as total_denuncias,
                    (SELECT COUNT(*) FROM denuncias WHERE status = 'pendente') as denuncias_pendentes,
                    (SELECT COUNT(*) FROM denuncias WHERE status = 'resolvida') as denuncias_resolvidas,
                    (SELECT COUNT(*) FROM votos_guardioes) as total_votos
            """
            stats = db_manager.execute_one_sync(stats_query)
            
            # Usuários recentes
            recent_users_query = """
                SELECT id_discord, username, display_name, categoria, data_criacao_registro 
                FROM usuarios 
                ORDER BY data_criacao_registro DESC 
                LIMIT 10
            """
            recent_users = db_manager.execute_query_sync(recent_users_query)
            
            # Denúncias recentes
            recent_denuncias_query = """
                SELECT id, id_denunciado, motivo, status, data_criacao 
                FROM denuncias 
                ORDER BY data_criacao DESC 
                LIMIT 10
            """
            recent_denuncias = db_manager.execute_query_sync(recent_denuncias_query)
            
            return render_template('admin/dashboard.html',
                                 stats=stats,
                                 recent_users=recent_users,
                                 recent_denuncias=recent_denuncias)
            
        except Exception as e:
            logger.error(f"Erro no painel admin: {e}")
            flash("Erro ao carregar painel administrativo.", "error")
            return redirect(url_for('dashboard'))
    
    @app.route('/admin/usuarios')
    @admin_required
    def admin_usuarios():
        """Lista de todos os usuários"""
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
            logger.error(f"Erro ao listar usuários: {e}")
            flash("Erro ao carregar lista de usuários.", "error")
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
                SELECT id, motivo, status, data_criacao 
                FROM denuncias 
                WHERE id_denunciado = $1 
                ORDER BY data_criacao DESC
            """
            denuncias = db_manager.execute_query_sync(denuncias_query, user_id)
            
            # Busca votos do usuário (se for guardião)
            votos_query = """
                SELECT v.id, v.voto, v.data_voto, d.motivo, d.status
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
            logger.error(f"Erro ao buscar detalhes do usuário: {e}")
            flash("Erro ao carregar detalhes do usuário.", "error")
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
            logger.error(f"Erro ao editar usuário: {e}")
            flash("Erro ao editar usuário.", "error")
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
            base_query = """
                SELECT d.id, d.id_denunciado, d.motivo, d.status, d.data_criacao,
                       u.username as denunciado_username
                FROM denuncias d
                LEFT JOIN usuarios u ON d.id_denunciado = u.id_discord
            """
            
            where_clause = ""
            params = []
            
            if status_filter:
                where_clause = " WHERE d.status = $1"
                params.append(status_filter)
            
            # Busca denúncias com filtros
            denuncias_query = base_query + where_clause + " ORDER BY d.data_criacao DESC LIMIT $" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)
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
            logger.error(f"Erro ao listar denúncias: {e}")
            flash("Erro ao carregar lista de denúncias.", "error")
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
            
            # Busca votos da denúncia
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
                ORDER BY timestamp_mensagem DESC
                LIMIT 100
            """
            mensagens = db_manager.execute_query_sync(mensagens_query, denuncia_id)
            
            return render_template('admin/denuncia_detalhes.html',
                                 denuncia=denuncia,
                                 votos=votos,
                                 mensagens=mensagens)
            
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes da denúncia: {e}")
            flash("Erro ao carregar detalhes da denúncia.", "error")
            return redirect(url_for('admin_denuncias'))
