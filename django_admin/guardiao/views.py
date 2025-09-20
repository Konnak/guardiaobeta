"""
Views personalizadas para Django Admin
"""

import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
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
                
                # Verifica se é admin autorizado
                if _is_authorized_admin(discord_id):
                    # Cria ou obtém usuário Django
                    user, created = User.objects.get_or_create(
                        username=f'discord_{discord_id}',
                        defaults={
                            'email': f'{username}@discord.local',
                            'first_name': username,
                            'is_staff': True,
                            'is_superuser': True,
                            'is_active': True
                        }
                    )
                    
                    if not created:
                        user.email = f'{username}@discord.local'
                        user.first_name = username
                        user.is_active = True
                        user.save()
                    
                    # Faz login do usuário
                    login(request, user)
                    logger.info(f"Login Discord bem-sucedido: {username} ({discord_id})")
                    return redirect('/admin/')
                else:
                    messages.error(request, f'Usuário {username} não está autorizado como administrador.')
                    return redirect('/admin/')
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