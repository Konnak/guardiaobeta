"""
Views personalizadas para Django Admin
"""

import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db import connection
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def discord_login(request):
    """View para login via Discord OAuth2"""
    
    # Se já está logado, redireciona para admin
    if request.user.is_authenticated:
        return redirect('/admin/')
    
    # Parâmetros OAuth2 Discord
    client_id = getattr(settings, 'DISCORD_CLIENT_ID', '')
    
    # Usa o domínio correto em vez de localhost
    host = request.get_host()
    if 'localhost' in host or '127.0.0.1' in host:
        host = 'guardiaobeta.discloud.app'
    
    redirect_uri = f"https://{host}/discord-admin/discord-callback/"
    
    # URL de autorização Discord
    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=identify"
    )
    
    context = {
        'discord_auth_url': discord_auth_url,
        'site_title': 'Guardião BETA - Login via Discord'
    }
    
    return render(request, 'guardiao/discord_login.html', context)

def discord_callback(request):
    """Callback do OAuth2 Discord"""
    
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Código de autorização não fornecido.')
        return redirect('/admin/')
    
    try:
        # Usa o domínio correto em vez de localhost
        host = request.get_host()
        if 'localhost' in host or '127.0.0.1' in host:
            host = 'guardiaobeta.discloud.app'
        
        # Troca código por token
        token_data = {
            'client_id': getattr(settings, 'DISCORD_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'DISCORD_CLIENT_SECRET', ''),
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f"https://{host}/discord-admin/discord-callback/"
        }
        
        response = requests.post('https://discord.com/api/oauth2/token', data=token_data)
        
        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info.get('access_token')
            
            # Obtém informações do usuário
            headers = {'Authorization': f'Bearer {access_token}'}
            user_response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                discord_id = user_data.get('id')
                username = user_data.get('username')
                
                # Cria ou obtém usuário Django
                is_admin = _is_authorized_admin(discord_id)
                
                user, created = User.objects.get_or_create(
                    username=f'discord_{discord_id}',
                    defaults={
                        'email': f'{username}@discord.local',
                        'first_name': username,
                        'is_staff': is_admin,
                        'is_superuser': is_admin,
                        'is_active': True
                    }
                )
                
                if not created:
                    user.email = f'{username}@discord.local'
                    user.first_name = username
                    user.is_staff = is_admin
                    user.is_superuser = is_admin
                    user.is_active = True
                    user.save()
                
                # Faz login do usuário
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                logger.info(f"Login Discord bem-sucedido: {username} ({discord_id}) - Admin: {is_admin}")
                
                # Redireciona baseado no tipo de usuário
                if is_admin:
                    return redirect('/admin/')
                else:
                    return redirect('/dashboard/')
            else:
                messages.error(request, 'Erro ao obter informações do usuário Discord.')
                return redirect('/admin/')
        else:
            messages.error(request, 'Erro ao obter token de acesso do Discord.')
            return redirect('/admin/')
            
    except Exception as e:
        logger.error(f"Erro no callback Discord: {e}")
        messages.error(request, 'Erro interno durante autenticação.')
        return redirect('/admin/')

def _is_authorized_admin(discord_id):
    """Verifica se o Discord ID está autorizado como admin"""
    authorized_admins = [
        '1369940071246991380',  # Seu ID Discord
        # Adicione outros IDs aqui conforme necessário
    ]
    
    return str(discord_id) in authorized_admins

# ============================================================================
# VIEWS MIGRADAS DO FLASK
# ============================================================================

def dashboard(request):
    """Dashboard do usuário - migrado do Flask"""
    if not request.user.is_authenticated:
        return redirect('/discord-admin/discord-login/')
    
    try:
        # Extrai Discord ID do username Django
        username = request.user.username
        if not username.startswith('discord_'):
            messages.error(request, 'Usuário não é do Discord.')
            return redirect('/')
        
        discord_id = username.replace('discord_', '')
        
        # Busca dados do usuário no banco
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM usuarios WHERE id_discord = %s", 
                [discord_id]
            )
            db_user = cursor.fetchone()
            
            if not db_user:
                # Usuário não cadastrado
                return render(request, 'guardiao/dashboard.html', {
                    'user': request.user,  # Passa o objeto user do Django
                    'cadastrado': False,
                    'avatar_url': get_user_avatar_url(discord_id, None, None)
                })
            
            # Busca estatísticas do usuário
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = %s) as denuncias_atendidas,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = %s) as total_votos,
                    (SELECT COUNT(*) FROM denuncias WHERE id_denunciante = %s) as denuncias_feitas
            """, [discord_id, discord_id, discord_id])
            
            stats = cursor.fetchone()
            if not stats:
                stats = {'denuncias_atendidas': 0, 'total_votos': 0, 'denuncias_feitas': 0}
            
            # Calcula informações de experiência
            from utils.experience_system import get_experience_rank, get_rank_emoji, format_experience_display
            rank = get_experience_rank(db_user[6])  # índice da experiência
            emoji = get_rank_emoji(rank)
            experience_display = format_experience_display(db_user[6])
            
            # Última atividade
            ultima_atividade = "Nunca"
            if db_user[7]:  # último_voto
                diff = datetime.now() - db_user[7]
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
            
            return render(request, 'guardiao/dashboard.html', {
                'user': request.user,  # Passa o objeto user do Django
                'cadastrado': True,
                'db_user': db_user,
                'stats': stats,
                'rank': rank,
                'emoji': emoji,
                'experience_display': experience_display,
                'ultima_atividade': ultima_atividade,
                'avatar_url': get_user_avatar_url(discord_id, None, None)
            })
            
    except Exception as e:
        logger.error(f"Erro no dashboard: {e}")
        messages.error(request, "Erro ao carregar dashboard.")
        return redirect('/')

def servers(request):
    """Lista de servidores do usuário - migrado do Flask"""
    if not request.user.is_authenticated:
        return redirect('/discord-admin/discord-login/')
    
    try:
        # Extrai Discord ID do username Django
        username = request.user.username
        if not username.startswith('discord_'):
            messages.error(request, 'Usuário não é do Discord.')
            return redirect('/')
        
        discord_id = username.replace('discord_', '')
        
        # Busca servidores do usuário via Discord API
        admin_guilds = get_user_guilds_admin(discord_id)
        
        # Busca informações de premium para cada servidor
        servers_info = []
        for guild in admin_guilds:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM servidores_premium 
                    WHERE id_servidor = %s AND data_fim > NOW()
                """, [int(guild['id'])])
                premium_data = cursor.fetchone()
                
                servers_info.append({
                    'guild': guild,
                    'is_premium': premium_data is not None,
                    'premium_data': premium_data,
                    'icon_url': get_guild_icon_url(guild['id'], guild.get('icon'))
                })
        
        return render(request, 'guardiao/servers.html', {
            'user': request.user,  # Passa o objeto user do Django
            'servers': servers_info,
            'avatar_url': get_user_avatar_url(discord_id, None, None)
        })
        
    except Exception as e:
        logger.error(f"Erro na lista de servidores: {e}")
        messages.error(request, "Erro ao carregar lista de servidores.")
        return redirect('/dashboard/')

def server_panel(request, server_id):
    """Painel de controle do servidor - migrado do Flask"""
    if not request.user.is_authenticated:
        return redirect('/discord-admin/discord-login/')
    
    try:
        # Extrai Discord ID do username Django
        username = request.user.username
        if not username.startswith('discord_'):
            messages.error(request, 'Usuário não é do Discord.')
            return redirect('/')
        
        discord_id = username.replace('discord_', '')
        
        # Verifica se o usuário é admin do servidor
        admin_guilds = get_user_guilds_admin(discord_id)
        guild = None
        
        for admin_guild in admin_guilds:
            if int(admin_guild['id']) == server_id:
                guild = admin_guild
                break
        
        if not guild:
            messages.error(request, "Você não tem permissão para acessar este servidor.")
            return redirect('/servers/')
        
        # Busca estatísticas do servidor
        server_stats = get_server_stats(server_id)
        
        # Verifica se é servidor premium
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM servidores_premium 
                WHERE id_servidor = %s AND data_fim > NOW()
            """, [server_id])
            premium_data = cursor.fetchone()
            is_premium = premium_data is not None
            
            # Busca configurações do servidor (se premium)
            server_config = None
            if is_premium:
                cursor.execute("""
                    SELECT * FROM configuracoes_servidor 
                    WHERE id_servidor = %s
                """, [server_id])
                server_config = cursor.fetchone()
        
        return render(request, 'guardiao/server_panel.html', {
            'user': request.user,  # Passa o objeto user do Django
            'guild': guild,
            'server_id': server_id,
            'stats': server_stats,
            'is_premium': is_premium,
            'premium_data': premium_data,
            'server_config': server_config,
            'guild_icon_url': get_guild_icon_url(str(server_id), guild.get('icon')),
            'avatar_url': get_user_avatar_url(discord_id, None, None)
        })
        
    except Exception as e:
        logger.error(f"Erro no painel do servidor: {e}")
        messages.error(request, "Erro ao carregar painel do servidor.")
        return redirect('/servers/')

def premium(request):
    """Página de informações sobre premium - migrado do Flask"""
    try:
        return render(request, 'guardiao/premium.html', {
            'bot_invite_url': get_bot_invite_url()
        })
        
    except Exception as e:
        logger.error(f"Erro na página premium: {e}")
        return render(request, 'guardiao/premium.html', {
            'bot_invite_url': get_bot_invite_url()
        })

# ============================================================================
# API ENDPOINTS MIGRADOS DO FLASK
# ============================================================================

@csrf_exempt
def api_user_stats(request):
    """API para estatísticas do usuário - migrado do Flask"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)
    
    try:
        # Extrai Discord ID do username Django
        username = request.user.username
        if not username.startswith('discord_'):
            return JsonResponse({'error': 'Usuário não é do Discord'}, status=400)
        
        discord_id = username.replace('discord_', '')
        
        # Estatísticas básicas
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = %s) as denuncias_atendidas,
                    (SELECT COUNT(*) FROM denuncias WHERE id_denunciante = %s) as denuncias_feitas,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = %s AND voto = 'OK!') as votos_ok,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = %s AND voto = 'Intimidou') as votos_intimidou,
                    (SELECT COUNT(*) FROM votos_guardioes WHERE id_guardiao = %s AND voto = 'Grave') as votos_grave
            """, [discord_id, discord_id, discord_id, discord_id, discord_id])
            
            stats = cursor.fetchone()
            
            # Gráfico de atividade (últimos 30 dias)
            cursor.execute("""
                SELECT DATE(data_voto) as data, COUNT(*) as votos
                FROM votos_guardioes 
                WHERE id_guardiao = %s 
                AND data_voto >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(data_voto)
                ORDER BY data
            """, [discord_id])
            activity = cursor.fetchall()
            
            return JsonResponse({
                'stats': stats if stats else {},
                'activity': activity
            })
            
    except Exception as e:
        logger.error(f"Erro na API de estatísticas do usuário: {e}")
        return JsonResponse({'error': 'Erro interno'}, status=500)

@csrf_exempt
def api_server_stats(request, server_id):
    """API para estatísticas do servidor - migrado do Flask"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)
    
    try:
        # Verifica permissões
        username = request.user.username
        if not username.startswith('discord_'):
            return JsonResponse({'error': 'Usuário não é do Discord'}, status=400)
        
        discord_id = username.replace('discord_', '')
        admin_guilds = get_user_guilds_admin(discord_id)
        has_permission = any(int(guild['id']) == server_id for guild in admin_guilds)
        
        if not has_permission:
            return JsonResponse({'error': 'Sem permissão'}, status=403)
        
        # Busca estatísticas
        stats = get_server_stats(server_id)
        return JsonResponse(stats)
        
    except Exception as e:
        logger.error(f"Erro na API de estatísticas: {e}")
        return JsonResponse({'error': 'Erro interno'}, status=500)

@csrf_exempt
def api_server_denuncias(request, server_id):
    """API para denúncias do servidor - migrado do Flask"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Não autenticado'}, status=401)
    
    try:
        # Verifica permissões
        username = request.user.username
        if not username.startswith('discord_'):
            return JsonResponse({'error': 'Usuário não é do Discord'}, status=400)
        
        discord_id = username.replace('discord_', '')
        admin_guilds = get_user_guilds_admin(discord_id)
        has_permission = any(int(guild['id']) == server_id for guild in admin_guilds)
        
        if not has_permission:
            return JsonResponse({'error': 'Sem permissão'}, status=403)
        
        # Parâmetros de filtro
        page = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 20)
        status = request.GET.get('status', None)
        periodo = request.GET.get('periodo', '30')  # dias
        
        # Calcula offset
        offset = (int(page) - 1) * int(per_page)
        
        # Query base
        where_conditions = ["id_servidor = %s"]
        params = [server_id]
        
        # Filtro por status
        if status:
            where_conditions.append("status = %s")
            params.append(status)
        
        # Filtro por período
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
            LIMIT {per_page} OFFSET {offset}
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            denuncias = cursor.fetchall()
            
            # Conta total para paginação
            count_query = f"""
                SELECT COUNT(*) FROM denuncias d
                WHERE {' AND '.join(where_conditions)}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
        
        return JsonResponse({
            'denuncias': denuncias,
            'total': total,
            'page': int(page),
            'per_page': int(per_page),
            'pages': (total + int(per_page) - 1) // int(per_page)
        })
        
    except Exception as e:
        logger.error(f"Erro na API de denúncias: {e}")
        return JsonResponse({'error': 'Erro interno'}, status=500)

# ============================================================================
# FUNÇÕES UTILITÁRIAS MIGRADAS DO FLASK
# ============================================================================

def get_server_stats(server_id):
    """Busca estatísticas de um servidor - migrado do Flask"""
    try:
        with connection.cursor() as cursor:
            # Estatísticas gerais
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_denuncias,
                    COUNT(CASE WHEN status = 'Finalizada' THEN 1 END) as denuncias_finalizadas,
                    COUNT(CASE WHEN status = 'Pendente' THEN 1 END) as denuncias_pendentes,
                    COUNT(CASE WHEN status = 'Em Análise' THEN 1 END) as denuncias_analise,
                    COUNT(CASE WHEN e_premium = true THEN 1 END) as denuncias_premium
                FROM denuncias 
                WHERE id_servidor = %s
            """, [server_id])
            general_stats = cursor.fetchone()
            
            # Resultados das denúncias
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN resultado_final = 'OK!' THEN 1 END) as improcedentes,
                    COUNT(CASE WHEN resultado_final = 'Intimidou' THEN 1 END) as intimidoes,
                    COUNT(CASE WHEN resultado_final = 'Grave' THEN 1 END) as graves
                FROM denuncias 
                WHERE id_servidor = %s AND status = 'Finalizada'
            """, [server_id])
            results_stats = cursor.fetchone()
            
            # Denúncias por período (últimos 7 dias)
            cursor.execute("""
                SELECT DATE(data_criacao) as data, COUNT(*) as quantidade
                FROM denuncias 
                WHERE id_servidor = %s 
                AND data_criacao >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(data_criacao)
                ORDER BY data
            """, [server_id])
            period_stats = cursor.fetchall()
            
            # Usuários mais denunciados
            cursor.execute("""
                SELECT id_denunciado, COUNT(*) as denuncias_count
                FROM denuncias 
                WHERE id_servidor = %s 
                AND data_criacao >= NOW() - INTERVAL '30 days'
                GROUP BY id_denunciado
                ORDER BY denuncias_count DESC
                LIMIT 10
            """, [server_id])
            top_denunciados = cursor.fetchall()
            
            return {
                'general': general_stats if general_stats else {},
                'results': results_stats if results_stats else {},
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

def get_user_guilds_admin(discord_id):
    """Obtém servidores onde o usuário é admin - migrado do Flask"""
    try:
        # Aqui você implementaria a lógica para buscar servidores do Discord
        # Por enquanto, retorna lista vazia
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar servidores do usuário: {e}")
        return []

def get_bot_invite_url():
    """URL para convidar o bot - migrado do Flask"""
    return "https://discord.com/api/oauth2/authorize?client_id=1418660046610370751&permissions=8&scope=bot"

def get_user_avatar_url(user_id, avatar_hash, discriminator):
    """URL do avatar do usuário - migrado do Flask"""
    if avatar_hash:
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
    else:
        # Avatar padrão baseado no discriminator
        avatar_num = int(discriminator) % 5 if discriminator else 0
        return f"https://cdn.discordapp.com/embed/avatars/{avatar_num}.png"

def get_guild_icon_url(guild_id, icon_hash):
    """URL do ícone do servidor - migrado do Flask"""
    if icon_hash:
        return f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png"
    else:
        return None