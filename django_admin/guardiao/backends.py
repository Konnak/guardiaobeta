"""
Backend de autenticação personalizado para Django Admin
Permite login via Discord OAuth2
"""

import requests
from django.contrib.auth.models import User
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class DiscordAuthBackend:
    """
    Backend de autenticação via Discord
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Autentica usuário tradicional"""
        if username and password:
            try:
                user = User.objects.get(username=username)
                if user.check_password(password) and user.is_active:
                    return user
            except User.DoesNotExist:
                return None
        return None
    
    def authenticate_discord(self, request, discord_token=None, **kwargs):
        """Autentica usuário via token Discord"""
        if not discord_token:
            return None
            
        try:
            # Obtém informações do usuário Discord
            headers = {
                'Authorization': f'Bearer {discord_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                discord_id = user_data.get('id')
                username = user_data.get('username')
                
                # Verifica se é um admin autorizado
                if self._is_authorized_admin(discord_id):
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
                        # Atualiza dados do usuário
                        user.email = f'{username}@discord.local'
                        user.first_name = username
                        user.is_active = True
                        user.save()
                    
                    logger.info(f"Usuário Discord autenticado: {username} ({discord_id})")
                    return user
                else:
                    logger.warning(f"Tentativa de login não autorizada: {username} ({discord_id})")
                    return None
                    
        except Exception as e:
            logger.error(f"Erro na autenticação Discord: {e}")
            return None
    
    def get_user(self, user_id):
        """Obtém usuário por ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    def _is_authorized_admin(self, discord_id):
        """Verifica se o Discord ID está autorizado como admin"""
        # Lista de Discord IDs autorizados (adicione o seu ID aqui)
        authorized_admins = [
            '1369940071246991380',  # Seu ID Discord
            # Adicione outros IDs aqui conforme necessário
        ]
        
        return str(discord_id) in authorized_admins
