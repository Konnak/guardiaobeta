"""
Painel Administrativo Completo - Sistema Guardião BETA
Funcionalidades completas para gerenciamento do sistema
"""

import logging
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, session

logger = logging.getLogger(__name__)

# Importações com tratamento de erro
try:
    from database.connection import db_manager
    logger.info("✅ db_manager importado com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao importar db_manager: {e}")
    db_manager = None

def setup_admin_complete(app):
    """Configura painel administrativo completo"""
    
    # ==================== VERIFICAÇÃO DE ADMIN ====================
    def is_admin(user_id):
        """Verifica se o usuário é administrador"""
        # ID do administrador principal
        return user_id == 1369940071246991380
    
    def admin_required_simple(f):
        """Decorador simples para verificar admin"""
        def wrapper(*args, **kwargs):
            if 'user' not in session:
                return redirect('/admin/login')
            
            user_id = session['user']['id']
            if not is_admin(user_id):
                return """
                <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
                    <h2>❌ Acesso Negado</h2>
                    <p>Você não tem permissões de administrador.</p>
                    <p>ID do usuário: {}</p>
                    <a href="/dashboard" style="color: #3498db;">← Voltar ao Dashboard</a>
                </div>
                """.format(user_id)
            
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    
    # ==================== LOGIN ADMIN ====================
    @app.route('/admin/login')
    def admin_login():
        """Página de login do admin"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>🛡️ Login Admin - Sistema Guardião</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
                .container { max-width: 400px; margin: 0 auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); text-align: center; }
                .btn { background: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 10px; }
                .btn:hover { background: #2980b9; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ Login Administrativo</h1>
                <p>Faça login com Discord para acessar o painel admin</p>
                <a href="/auth/login" class="btn">🔐 Login com Discord</a>
                <br><br>
                <a href="/" style="color: #666;">← Voltar ao Início</a>
            </div>
        </body>
        </html>
        """
    
    # ==================== DASHBOARD PRINCIPAL ====================
    @app.route('/admin/dashboard')
    @admin_required_simple
    def admin_dashboard_complete():
        """Dashboard administrativo completo"""
        try:
            # Busca estatísticas gerais
            stats = {}
            
            if db_manager and db_manager.pool:
                # Estatísticas de usuários
                user_stats = db_manager.execute_one_sync("""
                    SELECT 
                        COUNT(*) as total_usuarios,
                        COUNT(CASE WHEN categoria = 'Guardião' THEN 1 END) as total_guardioes,
                        COUNT(CASE WHEN em_servico = true THEN 1 END) as guardioes_servico,
                        COUNT(CASE WHEN data_criacao_registro >= NOW() - INTERVAL '24 hours' THEN 1 END) as novos_24h
                    FROM usuarios
                """)
                
                # Estatísticas de denúncias
                report_stats = db_manager.execute_one_sync("""
                    SELECT 
                        COUNT(*) as total_denuncias,
                        COUNT(CASE WHEN status = 'Pendente' THEN 1 END) as pendentes,
                        COUNT(CASE WHEN status = 'Em Análise' THEN 1 END) as em_analise,
                        COUNT(CASE WHEN status = 'Finalizada' THEN 1 END) as finalizadas,
                        COUNT(CASE WHEN data_criacao >= NOW() - INTERVAL '24 hours' THEN 1 END) as novas_24h
                    FROM denuncias
                """)
                
                # Estatísticas de votos
                vote_stats = db_manager.execute_one_sync("""
                    SELECT 
                        COUNT(*) as total_votos,
                        COUNT(CASE WHEN voto = 'OK!' THEN 1 END) as votos_ok,
                        COUNT(CASE WHEN voto = 'Intimidou' THEN 1 END) as votos_intimidou,
                        COUNT(CASE WHEN voto = 'Grave' THEN 1 END) as votos_grave
                    FROM votos_guardioes
                """)
                
                # Servidores premium
                premium_stats = db_manager.execute_one_sync("""
                    SELECT 
                        COUNT(*) as total_premium,
                        COUNT(CASE WHEN data_fim > NOW() THEN 1 END) as premium_ativos
                    FROM servidores_premium
                """)
                
                # Atividade recente
                recent_activity = db_manager.execute_query_sync("""
                    SELECT 'denuncia' as tipo, data_criacao as data, motivo as descricao 
                    FROM denuncias 
                    WHERE data_criacao >= NOW() - INTERVAL '24 hours'
                    UNION ALL
                    SELECT 'voto' as tipo, data_voto as data, CONCAT('Voto: ', voto) as descricao
                    FROM votos_guardioes 
                    WHERE data_voto >= NOW() - INTERVAL '24 hours'
                    ORDER BY data DESC 
                    LIMIT 10
                """)
                
                stats = {
                    'users': user_stats or {},
                    'reports': report_stats or {},
                    'votes': vote_stats or {},
                    'premium': premium_stats or {},
                    'activity': recent_activity or []
                }
            
            return render_template('admin/dashboard_complete.html', stats=stats)
            
        except Exception as e:
            logger.error(f"Erro no dashboard admin: {e}")
            return f"<h2>Erro no dashboard: {e}</h2><a href='/admin'>← Voltar</a>"
    
    # ==================== GESTÃO DE USUÁRIOS ====================
    @app.route('/admin/users')
    @admin_required_simple
    def admin_users_list():
        """Lista de usuários com filtros"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = 25
            offset = (page - 1) * per_page
            
            # Filtros
            categoria = request.args.get('categoria', '')
            em_servico = request.args.get('em_servico', '')
            search = request.args.get('search', '')
            
            # Construir query
            where_conditions = []
            params = []
            param_count = 0
            
            if categoria:
                param_count += 1
                where_conditions.append(f"categoria = ${param_count}")
                params.append(categoria)
            
            if em_servico:
                param_count += 1
                where_conditions.append(f"em_servico = ${param_count}")
                params.append(em_servico == 'true')
            
            if search:
                param_count += 1
                where_conditions.append(f"(username ILIKE ${param_count} OR display_name ILIKE ${param_count} OR nome_completo ILIKE ${param_count})")
                params.append(f"%{search}%")
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Query principal
            users_query = f"""
                SELECT id_discord, username, display_name, nome_completo, categoria, 
                       pontos, experiencia, em_servico, data_criacao_registro
                FROM usuarios 
                {where_clause}
                ORDER BY data_criacao_registro DESC 
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([per_page, offset])
            
            users = db_manager.execute_query_sync(users_query, *params) if db_manager else []
            
            # Total para paginação
            count_query = f"SELECT COUNT(*) as total FROM usuarios {where_clause}"
            count_params = params[:-2]  # Remove limit e offset
            total = db_manager.execute_one_sync(count_query, *count_params) if db_manager else {'total': 0}
            total_users = total['total']
            total_pages = (total_users + per_page - 1) // per_page
            
            return render_template('admin/users_list.html', 
                                 users=users,
                                 page=page,
                                 total_pages=total_pages,
                                 total_users=total_users,
                                 filters={'categoria': categoria, 'em_servico': em_servico, 'search': search})
            
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}")
            return f"<h2>Erro: {e}</h2><a href='/admin/dashboard'>← Voltar</a>"
    
    @app.route('/admin/users/<int:user_id>')
    @admin_required_simple
    def admin_user_detail(user_id):
        """Detalhes de um usuário específico"""
        try:
            # Buscar dados do usuário
            user = db_manager.execute_one_sync("SELECT * FROM usuarios WHERE id_discord = $1", user_id) if db_manager else None
            
            if not user:
                return "<h2>Usuário não encontrado</h2><a href='/admin/users'>← Voltar</a>"
            
            # Estatísticas do usuário
            user_stats = db_manager.execute_one_sync("""
                SELECT 
                    (SELECT COUNT(*) FROM denuncias WHERE id_denunciante = $1) as denuncias_feitas,
                    (SELECT COUNT(*) FROM denuncias WHERE id_denunciado = $1) as denuncias_recebidas,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = $1) as votos_dados
            """, user_id) if db_manager else {}
            
            # Denúncias feitas pelo usuário
            denuncias_feitas = db_manager.execute_query_sync("""
                SELECT d.*, u.username as denunciado_username 
                FROM denuncias d
                LEFT JOIN usuarios u ON d.id_denunciado = u.id_discord
                WHERE d.id_denunciante = $1 
                ORDER BY d.data_criacao DESC 
                LIMIT 10
            """, user_id) if db_manager else []
            
            # Denúncias recebidas
            denuncias_recebidas = db_manager.execute_query_sync("""
                SELECT d.*, u.username as denunciante_username 
                FROM denuncias d
                LEFT JOIN usuarios u ON d.id_denunciante = u.id_discord
                WHERE d.id_denunciado = $1 
                ORDER BY d.data_criacao DESC 
                LIMIT 10
            """, user_id) if db_manager else []
            
            # Votos dados (se for guardião)
            votos_dados = db_manager.execute_query_sync("""
                SELECT v.*, d.motivo 
                FROM votos_guardioes v
                JOIN denuncias d ON v.id_denuncia = d.id
                WHERE v.id_guardiao = $1 
                ORDER BY v.data_voto DESC 
                LIMIT 10
            """, user_id) if db_manager else []
            
            return render_template('admin/user_detail.html',
                                 user=user,
                                 stats=user_stats,
                                 denuncias_feitas=denuncias_feitas,
                                 denuncias_recebidas=denuncias_recebidas,
                                 votos_dados=votos_dados)
            
        except Exception as e:
            logger.error(f"Erro ao buscar usuário: {e}")
            return f"<h2>Erro: {e}</h2><a href='/admin/users'>← Voltar</a>"
    
    @app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
    @admin_required_simple
    def admin_user_edit(user_id):
        """Editar usuário"""
        try:
            if request.method == 'POST':
                # Atualizar dados
                categoria = request.form.get('categoria')
                pontos = int(request.form.get('pontos', 0))
                experiencia = int(request.form.get('experiencia', 0))
                em_servico = request.form.get('em_servico') == 'on'
                
                if db_manager:
                    db_manager.execute_command_sync("""
                        UPDATE usuarios 
                        SET categoria = $1, pontos = $2, experiencia = $3, em_servico = $4
                        WHERE id_discord = $5
                    """, categoria, pontos, experiencia, em_servico, user_id)
                
                return redirect(f'/admin/users/{user_id}')
            
            # GET - mostrar formulário
            user = db_manager.execute_one_sync("SELECT * FROM usuarios WHERE id_discord = $1", user_id) if db_manager else None
            
            if not user:
                return "<h2>Usuário não encontrado</h2><a href='/admin/users'>← Voltar</a>"
            
            return render_template('admin/user_edit.html', user=user)
            
        except Exception as e:
            logger.error(f"Erro ao editar usuário: {e}")
            return f"<h2>Erro: {e}</h2><a href='/admin/users/{user_id}'>← Voltar</a>"
    
    # ==================== GESTÃO DE DENÚNCIAS ====================
    @app.route('/admin/reports')
    @admin_required_simple
    def admin_reports_list():
        """Lista de denúncias"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = 25
            offset = (page - 1) * per_page
            
            # Filtros
            status = request.args.get('status', '')
            periodo = request.args.get('periodo', '')
            
            # Construir query
            where_conditions = []
            params = []
            param_count = 0
            
            if status:
                param_count += 1
                where_conditions.append(f"d.status = ${param_count}")
                params.append(status)
            
            if periodo:
                param_count += 1
                where_conditions.append(f"d.data_criacao >= NOW() - INTERVAL '{periodo} days'")
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Query principal
            reports_query = f"""
                SELECT d.*, 
                       u1.username as denunciante_username,
                       u2.username as denunciado_username
                FROM denuncias d
                LEFT JOIN usuarios u1 ON d.id_denunciante = u1.id_discord
                LEFT JOIN usuarios u2 ON d.id_denunciado = u2.id_discord
                {where_clause}
                ORDER BY d.data_criacao DESC 
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([per_page, offset])
            
            reports = db_manager.execute_query_sync(reports_query, *params) if db_manager else []
            
            # Total para paginação
            count_query = f"SELECT COUNT(*) as total FROM denuncias d {where_clause}"
            count_params = params[:-2]
            total = db_manager.execute_one_sync(count_query, *count_params) if db_manager else {'total': 0}
            total_reports = total['total']
            total_pages = max(1, (total_reports + per_page - 1) // per_page)
            
            return render_template('admin/reports_list.html',
                                 reports=reports,
                                 page=page,
                                 total_pages=total_pages,
                                 total_reports=total_reports,
                                 filters={'status': status, 'periodo': periodo})
            
        except Exception as e:
            logger.error(f"Erro ao listar denúncias: {e}")
            return f"<h2>Erro: {e}</h2><a href='/admin/dashboard'>← Voltar</a>"
    
    @app.route('/admin/reports/<int:report_id>')
    @admin_required_simple
    def admin_report_detail(report_id):
        """Detalhes de uma denúncia"""
        try:
            # Buscar denúncia
            report = db_manager.execute_one_sync("""
                SELECT d.*, 
                       u1.username as denunciante_username, u1.display_name as denunciante_display,
                       u2.username as denunciado_username, u2.display_name as denunciado_display
                FROM denuncias d
                LEFT JOIN usuarios u1 ON d.id_denunciante = u1.id_discord
                LEFT JOIN usuarios u2 ON d.id_denunciado = u2.id_discord
                WHERE d.id = $1
            """, report_id) if db_manager else None
            
            if not report:
                return "<h2>Denúncia não encontrada</h2><a href='/admin/reports'>← Voltar</a>"
            
            # Buscar votos
            votes = db_manager.execute_query_sync("""
                SELECT v.*, u.username as guardiao_username
                FROM votos_guardioes v
                LEFT JOIN usuarios u ON v.id_guardiao = u.id_discord
                WHERE v.id_denuncia = $1
                ORDER BY v.data_voto
            """, report_id) if db_manager else []
            
            # Buscar mensagens capturadas
            messages = db_manager.execute_query_sync("""
                SELECT m.*, u.username as autor_username
                FROM mensagens_capturadas m
                LEFT JOIN usuarios u ON m.id_autor = u.id_discord
                WHERE m.id_denuncia = $1
                ORDER BY m.timestamp_mensagem
            """, report_id) if db_manager else []
            
            return render_template('admin/report_detail.html',
                                 report=report,
                                 votes=votes,
                                 messages=messages)
            
        except Exception as e:
            logger.error(f"Erro ao buscar denúncia: {e}")
            return f"<h2>Erro: {e}</h2><a href='/admin/reports'>← Voltar</a>"
    
    # ==================== GESTÃO DE SERVIDORES PREMIUM ====================
    @app.route('/admin/premium')
    @admin_required_simple
    def admin_premium_list():
        """Lista de servidores premium"""
        try:
            # Buscar todos os servidores premium
            premium_servers = db_manager.execute_query_sync("""
                SELECT sp.*, 
                       CASE WHEN sp.data_fim > NOW() THEN 'Ativo' ELSE 'Expirado' END as status,
                       cs.canal_log, cs.duracao_intimidou, cs.duracao_grave
                FROM servidores_premium sp
                LEFT JOIN configuracoes_servidor cs ON sp.id_servidor = cs.id_servidor
                ORDER BY sp.data_fim DESC
            """) if db_manager else []
            
            return render_template('admin/premium_list.html', servers=premium_servers)
            
        except Exception as e:
            logger.error(f"Erro ao listar premium: {e}")
            return f"<h2>Erro: {e}</h2><a href='/admin/dashboard'>← Voltar</a>"
    
    # ==================== API ENDPOINTS ====================
    @app.route('/admin/api/stats')
    @admin_required_simple
    def admin_api_stats():
        """API para estatísticas em tempo real"""
        try:
            if not db_manager:
                return jsonify({'error': 'Database not available'})
            
            # Estatísticas rápidas
            stats = db_manager.execute_one_sync("""
                SELECT 
                    (SELECT COUNT(*) FROM usuarios) as total_users,
                    (SELECT COUNT(*) FROM usuarios WHERE categoria = 'Guardião') as guardians,
                    (SELECT COUNT(*) FROM denuncias WHERE status = 'Pendente') as pending_reports,
                    (SELECT COUNT(*) FROM denuncias WHERE data_criacao >= NOW() - INTERVAL '24 hours') as reports_24h
            """)
            
            return jsonify(stats or {})
            
        except Exception as e:
            logger.error(f"Erro na API de stats: {e}")
            return jsonify({'error': str(e)})
    
    # ==================== ROTA PRINCIPAL ADMIN ====================
    @app.route('/admin')
    def admin_main_redirect():
        """Redireciona para o dashboard completo"""
        return redirect('/admin/dashboard')
    
    logger.info("✅ Painel administrativo completo configurado!")
