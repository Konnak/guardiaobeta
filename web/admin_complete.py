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
    """Configura painel administrativo completo - DESABILITADO TEMPORARIAMENTE"""
    logger.info("⚠️ setup_admin_complete DESABILITADO - Usando sistema principal de rotas admin")
    
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
    
    @app.route('/admin/users/<int:user_id>/points', methods=['POST'])
    @admin_required_simple
    def admin_user_modify_points(user_id):
        """Modificar pontos de um usuário"""
        try:
            from utils.experience_system import calculate_xp_from_points_change
            
            # Busca o usuário atual
            user = db_manager.execute_one_sync("SELECT * FROM usuarios WHERE id_discord = $1", user_id) if db_manager else None
            
            if not user:
                flash('Usuário não encontrado.', 'error')
                return redirect(url_for('admin_users_list'))
            
            # Pega os dados do formulário
            action = request.form.get('action')  # 'add' ou 'set' ou 'remove'
            points_value = request.form.get('points_value', type=int)
            reason = request.form.get('reason', '').strip()
            
            if points_value is None:
                flash('Valor de pontos inválido.', 'error')
                return redirect(url_for('admin_user_detail', user_id=user_id))
            
            old_points = user['pontos']
            old_xp = user['experiencia']
            
            if action == 'add':
                # Adicionar pontos
                new_points = old_points + points_value
                points_change = points_value
                action_text = f"Adicionados {points_value} pontos"
            elif action == 'remove':
                # Remover pontos
                new_points = max(0, old_points - points_value)  # Não permite pontos negativos
                points_change = -(old_points - new_points)  # Calcula a diferença real
                action_text = f"Removidos {abs(points_change)} pontos"
            elif action == 'set':
                # Definir pontos
                new_points = max(0, points_value)
                points_change = new_points - old_points
                action_text = f"Pontos definidos para {new_points}"
            else:
                flash('Ação inválida.', 'error')
                return redirect(url_for('admin_user_detail', user_id=user_id))
            
            # Calcula XP correspondente (1 ponto = 2 XP)
            xp_change = calculate_xp_from_points_change(points_change)
            new_xp = max(0, old_xp + xp_change)  # Não permite XP negativo
            
            # Atualiza no banco de dados
            update_query = """
                UPDATE usuarios 
                SET pontos = $1, experiencia = $2
                WHERE id_discord = $3
            """
            db_manager.execute_command_sync(update_query, new_points, new_xp, user_id)
            
            # Registra log da ação
            log_message = f"Admin modificou pontos: {action_text}. Pontos: {old_points} → {new_points}. XP: {old_xp} → {new_xp}"
            if reason:
                log_message += f". Motivo: {reason}"
            
            logger.info(f"[ADMIN] {log_message} (Usuário: {user['username']})")
            
            # Flash message com detalhes
            flash_message = f"{action_text}. XP ajustado: {old_xp} → {new_xp} ({xp_change:+d} XP)"
            if reason:
                flash_message += f". Motivo: {reason}"
            
            flash(flash_message, 'success')
            return redirect(url_for('admin_user_detail', user_id=user_id))
            
        except Exception as e:
            logger.error(f"Erro ao modificar pontos do usuário: {e}")
            flash(f'Erro ao modificar pontos: {e}', 'error')
            return redirect(url_for('admin_user_detail', user_id=user_id))
    
    # ==================== GESTÃO DE DENÚNCIAS ====================
    @app.route('/admin/reports')
    @admin_required_simple
    def admin_reports_list():
        """Lista de denúncias com filtros avançados"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 25, type=int)
            offset = (page - 1) * per_page
            
            # Filtros avançados
            status = request.args.get('status', '')
            periodo = request.args.get('periodo', '')
            hash_search = request.args.get('hash', '')
            denunciado_search = request.args.get('denunciado', '')
            denunciante_search = request.args.get('denunciante', '')
            guardiao_search = request.args.get('guardiao', '')
            motivo_search = request.args.get('motivo', '')
            resultado = request.args.get('resultado', '')
            premium = request.args.get('premium', '')
            servidor_id = request.args.get('servidor', '')
            
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
                if periodo == 'hoje':
                    where_conditions.append(f"d.data_criacao >= CURRENT_DATE")
                elif periodo == 'semana':
                    where_conditions.append(f"d.data_criacao >= NOW() - INTERVAL '7 days'")
                elif periodo == 'mes':
                    where_conditions.append(f"d.data_criacao >= NOW() - INTERVAL '30 days'")
                elif periodo.isdigit():
                    where_conditions.append(f"d.data_criacao >= NOW() - INTERVAL '{periodo} days'")
            
            if hash_search:
                param_count += 1
                where_conditions.append(f"d.hash_denuncia ILIKE ${param_count}")
                params.append(f"%{hash_search}%")
            
            if denunciado_search:
                param_count += 1
                where_conditions.append(f"(u2.username ILIKE ${param_count} OR u2.display_name ILIKE ${param_count} OR d.id_denunciado::text ILIKE ${param_count})")
                params.append(f"%{denunciado_search}%")
            
            if denunciante_search:
                param_count += 1
                where_conditions.append(f"(u1.username ILIKE ${param_count} OR u1.display_name ILIKE ${param_count} OR d.id_denunciante::text ILIKE ${param_count})")
                params.append(f"%{denunciante_search}%")
            
            if motivo_search:
                param_count += 1
                where_conditions.append(f"d.motivo ILIKE ${param_count}")
                params.append(f"%{motivo_search}%")
            
            if resultado:
                param_count += 1
                where_conditions.append(f"d.resultado_final = ${param_count}")
                params.append(resultado)
            
            if premium:
                param_count += 1
                where_conditions.append(f"d.e_premium = ${param_count}")
                params.append(premium == 'true')
            
            if servidor_id:
                param_count += 1
                where_conditions.append(f"d.id_servidor = ${param_count}")
                params.append(int(servidor_id))
            
            # Filtro por guardião que votou
            if guardiao_search:
                param_count += 1
                where_conditions.append(f"""
                    d.id IN (
                        SELECT vg.id_denuncia FROM votos_guardioes vg
                        JOIN usuarios ug ON vg.id_guardiao = ug.id_discord
                        WHERE ug.username ILIKE ${param_count} OR ug.display_name ILIKE ${param_count} OR vg.id_guardiao::text ILIKE ${param_count}
                    )
                """)
                params.append(f"%{guardiao_search}%")
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Query principal com contagem de votos
            reports_query = f"""
                SELECT d.*, 
                       u1.username as denunciante_username,
                       u1.display_name as denunciante_display,
                       u2.username as denunciado_username,
                       u2.display_name as denunciado_display,
                       COALESCE(v.votos_count, 0) as total_votos,
                       COALESCE(v.votos_ok, 0) as votos_ok,
                       COALESCE(v.votos_intimidou, 0) as votos_intimidou,
                       COALESCE(v.votos_grave, 0) as votos_grave
                FROM denuncias d
                LEFT JOIN usuarios u1 ON d.id_denunciante = u1.id_discord
                LEFT JOIN usuarios u2 ON d.id_denunciado = u2.id_discord
                LEFT JOIN (
                    SELECT id_denuncia,
                           COUNT(*) as votos_count,
                           COUNT(CASE WHEN voto = 'OK!' THEN 1 END) as votos_ok,
                           COUNT(CASE WHEN voto = 'Intimidou' THEN 1 END) as votos_intimidou,
                           COUNT(CASE WHEN voto = 'Grave' THEN 1 END) as votos_grave
                    FROM votos_guardioes 
                    GROUP BY id_denuncia
                ) v ON d.id = v.id_denuncia
                {where_clause}
                ORDER BY d.data_criacao DESC 
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([per_page, offset])
            
            reports = db_manager.execute_query_sync(reports_query, *params) if db_manager else []
            
            # Total para paginação
            count_query = f"""
                SELECT COUNT(DISTINCT d.id) as total 
                FROM denuncias d
                LEFT JOIN usuarios u1 ON d.id_denunciante = u1.id_discord
                LEFT JOIN usuarios u2 ON d.id_denunciado = u2.id_discord
                {where_clause}
            """
            count_params = params[:-2]
            total = db_manager.execute_one_sync(count_query, *count_params) if db_manager else {'total': 0}
            total_reports = total['total']
            total_pages = max(1, (total_reports + per_page - 1) // per_page)
            
            # Estatísticas dos filtros aplicados
            stats_query = f"""
                SELECT 
                    COUNT(DISTINCT d.id) as total_filtrado,
                    COUNT(CASE WHEN d.status = 'Pendente' THEN 1 END) as pendentes,
                    COUNT(CASE WHEN d.status = 'Em Análise' THEN 1 END) as em_analise,
                    COUNT(CASE WHEN d.status = 'Finalizada' THEN 1 END) as finalizadas,
                    COUNT(CASE WHEN d.e_premium = true THEN 1 END) as premium_count
                FROM denuncias d
                LEFT JOIN usuarios u1 ON d.id_denunciante = u1.id_discord
                LEFT JOIN usuarios u2 ON d.id_denunciado = u2.id_discord
                {where_clause}
            """
            filter_stats = db_manager.execute_one_sync(stats_query, *count_params) if db_manager else {}
            
            filters = {
                'status': status, 'periodo': periodo, 'hash': hash_search,
                'denunciado': denunciado_search, 'denunciante': denunciante_search,
                'guardiao': guardiao_search, 'motivo': motivo_search,
                'resultado': resultado, 'premium': premium, 'servidor': servidor_id
            }
            
            return render_template('admin/reports_list_enhanced.html',
                                 reports=reports,
                                 page=page,
                                 total_pages=total_pages,
                                 total_reports=total_reports,
                                 per_page=per_page,
                                 filters=filters,
                                 filter_stats=filter_stats or {})
            
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
            
            return render_template('admin/report_detail_enhanced.html',
                                 report=report,
                                 votes=votes,
                                 messages=messages)
            
        except Exception as e:
            logger.error(f"Erro ao buscar denúncia: {e}")
            return f"<h2>Erro: {e}</h2><a href='/admin/reports'>← Voltar</a>"
    
    @app.route('/admin/reports/<int:report_id>/delete', methods=['POST'])
    @admin_required_simple
    def admin_report_delete(report_id):
        """Excluir uma denúncia"""
        try:
            # Verifica se a denúncia existe
            report = db_manager.execute_one_sync("""
                SELECT hash_denuncia, motivo FROM denuncias WHERE id = $1
            """, report_id) if db_manager else None
            
            if not report:
                flash('Denúncia não encontrada.', 'error')
                return redirect(url_for('admin_reports_list'))
            
            # Exclui votos relacionados primeiro
            db_manager.execute_command_sync("""
                DELETE FROM votos_guardioes WHERE id_denuncia = $1
            """, report_id)
            
            # Exclui mensagens capturadas
            db_manager.execute_command_sync("""
                DELETE FROM mensagens_capturadas WHERE id_denuncia = $1
            """, report_id)
            
            # Exclui mensagens de guardiões (se a tabela existir)
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mensagens_guardioes'
                )
            """
            table_exists = db_manager.execute_scalar_sync(table_exists_query)
            
            if table_exists:
                db_manager.execute_command_sync("""
                    DELETE FROM mensagens_guardioes WHERE id_denuncia = $1
                """, report_id)
            
            # Exclui a denúncia
            db_manager.execute_command_sync("""
                DELETE FROM denuncias WHERE id = $1
            """, report_id)
            
            flash(f'Denúncia {report["hash_denuncia"]} excluída com sucesso.', 'success')
            logger.info(f"Denúncia {report['hash_denuncia']} excluída pelo admin")
            
            return redirect(url_for('admin_reports_list'))
            
        except Exception as e:
            logger.error(f"Erro ao excluir denúncia: {e}")
            flash(f'Erro ao excluir denúncia: {e}', 'error')
            return redirect(url_for('admin_reports_list'))
    
    @app.route('/admin/reports/bulk-delete', methods=['POST'])
    @admin_required_simple
    def admin_reports_bulk_delete():
        """Exclusão em massa de denúncias"""
        try:
            report_ids = request.form.getlist('report_ids')
            
            if not report_ids:
                flash('Nenhuma denúncia selecionada.', 'warning')
                return redirect(url_for('admin_reports_list'))
            
            # Converte para integers
            report_ids = [int(rid) for rid in report_ids if rid.isdigit()]
            
            if not report_ids:
                flash('IDs de denúncia inválidos.', 'error')
                return redirect(url_for('admin_reports_list'))
            
            # Busca hashes das denúncias para log
            hashes_query = f"""
                SELECT hash_denuncia FROM denuncias 
                WHERE id = ANY($1)
            """
            hashes = db_manager.execute_query_sync(hashes_query, report_ids) if db_manager else []
            
            # Exclui em ordem (relacionamentos primeiro)
            placeholders = ','.join([f'${i+1}' for i in range(len(report_ids))])
            
            # Votos
            db_manager.execute_command_sync(f"""
                DELETE FROM votos_guardioes WHERE id_denuncia IN ({placeholders})
            """, *report_ids)
            
            # Mensagens capturadas
            db_manager.execute_command_sync(f"""
                DELETE FROM mensagens_capturadas WHERE id_denuncia IN ({placeholders})
            """, *report_ids)
            
            # Mensagens de guardiões (se existir)
            table_exists_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mensagens_guardioes'
                )
            """
            table_exists = db_manager.execute_scalar_sync(table_exists_query)
            
            if table_exists:
                db_manager.execute_command_sync(f"""
                    DELETE FROM mensagens_guardioes WHERE id_denuncia IN ({placeholders})
                """, *report_ids)
            
            # Denúncias
            db_manager.execute_command_sync(f"""
                DELETE FROM denuncias WHERE id IN ({placeholders})
            """, *report_ids)
            
            hash_list = [h['hash_denuncia'] for h in hashes]
            flash(f'{len(report_ids)} denúncias excluídas com sucesso: {", ".join(hash_list[:5])}{"..." if len(hash_list) > 5 else ""}', 'success')
            logger.info(f"{len(report_ids)} denúncias excluídas em massa pelo admin: {hash_list}")
            
            return redirect(url_for('admin_reports_list'))
            
        except Exception as e:
            logger.error(f"Erro na exclusão em massa: {e}")
            flash(f'Erro na exclusão em massa: {e}', 'error')
            return redirect(url_for('admin_reports_list'))
    
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
                       cs.canal_log, cs.duracao_intimidou, cs.duracao_grave,
                       sp.data_inicio AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo' as data_inicio_br,
                       sp.data_fim AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo' as data_fim_br
                FROM servidores_premium sp
                LEFT JOIN configuracoes_servidor cs ON sp.id_servidor = cs.id_servidor
                ORDER BY sp.data_fim DESC
            """) if db_manager else []
            
            return render_template('admin/premium_list.html', servers=premium_servers)
            
        except Exception as e:
            logger.error(f"Erro ao listar premium: {e}")
            return f"<h2>Erro: {e}</h2><a href='/admin/dashboard'>← Voltar</a>"
    
    @app.route('/admin/premium/add', methods=['GET', 'POST'])
    @admin_required_simple
    def admin_premium_add():
        """Adicionar servidor premium"""
        if request.method == 'GET':
            return render_template('admin/premium_add.html')
        
        try:
            from datetime import datetime, timedelta
            
            # Pega dados do formulário
            server_id = request.form.get('server_id', type=int)
            duration_type = request.form.get('duration_type')
            duration_value = request.form.get('duration_value', type=int)
            custom_end_date = request.form.get('custom_end_date')
            reason = request.form.get('reason', '').strip()
            
            # Debug - log dos dados recebidos
            logger.info(f"Dados recebidos no formulário: server_id={server_id}, duration_type={duration_type}, duration_value={duration_value}, custom_end_date={custom_end_date}")
            
            if not server_id:
                flash('ID do servidor é obrigatório.', 'error')
                return redirect(url_for('admin_premium_add'))
            
            if not duration_type:
                flash('Tipo de duração é obrigatório. Selecione uma opção de duração.', 'error')
                return redirect(url_for('admin_premium_add'))
            
            # Calcula data de fim
            if duration_type == 'custom' and custom_end_date:
                try:
                    # Parse da data customizada (assume horário de Brasília)
                    data_fim = datetime.strptime(custom_end_date, '%Y-%m-%dT%H:%M')
                    
                    # Converte para UTC (adiciona 3 horas pois Brasília é UTC-3)
                    from datetime import timezone, timedelta as td
                    brasilia_tz = timezone(td(hours=-3))
                    data_fim = data_fim.replace(tzinfo=brasilia_tz).astimezone(timezone.utc).replace(tzinfo=None)
                    
                    # Verifica se a data não é no passado
                    if data_fim <= datetime.utcnow():
                        flash('A data de expiração deve ser no futuro.', 'error')
                        return redirect(url_for('admin_premium_add'))
                        
                except ValueError:
                    flash('Data customizada inválida.', 'error')
                    return redirect(url_for('admin_premium_add'))
            elif duration_type in ['days', 'weeks', 'months', 'years']:
                if not duration_value or duration_value <= 0:
                    flash(f'Valor de duração inválido para {duration_type}. Tente selecionar a opção novamente.', 'error')
                    return redirect(url_for('admin_premium_add'))
                
                if duration_type == 'days':
                    data_fim = datetime.utcnow() + timedelta(days=duration_value)
                elif duration_type == 'weeks':
                    data_fim = datetime.utcnow() + timedelta(weeks=duration_value)
                elif duration_type == 'months':
                    data_fim = datetime.utcnow() + timedelta(days=duration_value * 30)
                elif duration_type == 'years':
                    data_fim = datetime.utcnow() + timedelta(days=duration_value * 365)
            else:
                flash(f'Tipo de duração inválido: {duration_type}. Selecione uma opção válida.', 'error')
                return redirect(url_for('admin_premium_add'))
            
            # Verifica se o servidor já é premium
            existing_query = """
                SELECT * FROM servidores_premium WHERE id_servidor = $1
            """
            existing = db_manager.execute_one_sync(existing_query, server_id)
            
            if existing:
                # Atualiza servidor existente
                update_query = """
                    UPDATE servidores_premium 
                    SET data_inicio = NOW(), data_fim = $1 
                    WHERE id_servidor = $2
                """
                db_manager.execute_command_sync(update_query, data_fim, server_id)
                action = "atualizado"
            else:
                # Adiciona novo servidor premium
                insert_query = """
                    INSERT INTO servidores_premium (id_servidor, data_inicio, data_fim)
                    VALUES ($1, NOW(), $2)
                """
                db_manager.execute_command_sync(insert_query, server_id, data_fim)
                action = "adicionado"
            
            # Cria configuração padrão se não existir
            config_exists = db_manager.execute_scalar_sync("""
                SELECT EXISTS(SELECT 1 FROM configuracoes_servidor WHERE id_servidor = $1)
            """, server_id)
            
            if not config_exists:
                config_query = """
                    INSERT INTO configuracoes_servidor (id_servidor, duracao_intimidou, duracao_intimidou_grave, duracao_grave, duracao_grave_4plus)
                    VALUES ($1, 1, 6, 12, 24)
                """
                db_manager.execute_command_sync(config_query, server_id)
            
            # Log da ação
            log_message = f"Servidor {server_id} {action} como premium até {data_fim.strftime('%d/%m/%Y %H:%M')}"
            if reason:
                log_message += f". Motivo: {reason}"
            
            logger.info(f"[ADMIN] {log_message}")
            
            flash(f'Servidor {server_id} {action} como premium com sucesso!', 'success')
            return redirect(url_for('admin_premium_list'))
            
        except Exception as e:
            logger.error(f"Erro ao adicionar servidor premium: {e}")
            flash(f'Erro ao adicionar servidor premium: {e}', 'error')
            return redirect(url_for('admin_premium_add'))
    
    @app.route('/admin/premium/<int:server_id>/extend', methods=['POST'])
    @admin_required_simple
    def admin_premium_extend(server_id):
        """Estender tempo de servidor premium"""
        try:
            from datetime import datetime, timedelta
            
            duration_type = request.form.get('duration_type')
            duration_value = request.form.get('duration_value', type=int)
            reason = request.form.get('reason', '').strip()
            
            if not duration_type or not duration_value:
                flash('Duração é obrigatória.', 'error')
                return redirect(url_for('admin_premium_list'))
            
            # Busca servidor atual
            server_query = """
                SELECT * FROM servidores_premium WHERE id_servidor = $1
            """
            server = db_manager.execute_one_sync(server_query, server_id)
            
            if not server:
                flash('Servidor premium não encontrado.', 'error')
                return redirect(url_for('admin_premium_list'))
            
            # Calcula nova data de fim (a partir da data atual de fim)
            current_end = server['data_fim']
            if current_end < datetime.utcnow():
                # Se já expirou, estende a partir de agora
                base_date = datetime.utcnow()
            else:
                # Se ainda ativo, estende a partir da data de fim atual
                base_date = current_end
            
            if duration_type == 'days':
                new_end = base_date + timedelta(days=duration_value)
            elif duration_type == 'weeks':
                new_end = base_date + timedelta(weeks=duration_value)
            elif duration_type == 'months':
                new_end = base_date + timedelta(days=duration_value * 30)
            elif duration_type == 'years':
                new_end = base_date + timedelta(days=duration_value * 365)
            else:
                flash('Tipo de duração inválido.', 'error')
                return redirect(url_for('admin_premium_list'))
            
            # Atualiza no banco
            update_query = """
                UPDATE servidores_premium 
                SET data_fim = $1 
                WHERE id_servidor = $2
            """
            db_manager.execute_command_sync(update_query, new_end, server_id)
            
            # Log da ação
            log_message = f"Premium do servidor {server_id} estendido até {new_end.strftime('%d/%m/%Y %H:%M')}"
            if reason:
                log_message += f". Motivo: {reason}"
            
            logger.info(f"[ADMIN] {log_message}")
            
            flash(f'Premium do servidor {server_id} estendido com sucesso!', 'success')
            return redirect(url_for('admin_premium_list'))
            
        except Exception as e:
            logger.error(f"Erro ao estender premium: {e}")
            flash(f'Erro ao estender premium: {e}', 'error')
            return redirect(url_for('admin_premium_list'))
    
    @app.route('/admin/premium/<int:server_id>/remove', methods=['POST'])
    @admin_required_simple
    def admin_premium_remove(server_id):
        """Remover servidor premium"""
        try:
            reason = request.form.get('reason', '').strip()
            
            # Remove servidor premium
            delete_query = """
                DELETE FROM servidores_premium WHERE id_servidor = $1
            """
            result = db_manager.execute_command_sync(delete_query, server_id)
            
            # Remove configurações também
            config_delete_query = """
                DELETE FROM configuracoes_servidor WHERE id_servidor = $1
            """
            db_manager.execute_command_sync(config_delete_query, server_id)
            
            # Log da ação
            log_message = f"Servidor {server_id} removido do premium"
            if reason:
                log_message += f". Motivo: {reason}"
            
            logger.info(f"[ADMIN] {log_message}")
            
            flash(f'Servidor {server_id} removido do premium com sucesso!', 'success')
            return redirect(url_for('admin_premium_list'))
            
        except Exception as e:
            logger.error(f"Erro ao remover premium: {e}")
            flash(f'Erro ao remover premium: {e}', 'error')
            return redirect(url_for('admin_premium_list'))
    
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
