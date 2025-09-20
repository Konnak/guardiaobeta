"""
Sistema de Autenticação OAuth2 Discord - Sistema Guardião BETA
Implementa login e callback para autenticação via Discord
"""

import os
import logging
import aiohttp
from flask import Flask, session, redirect, request, url_for, flash, jsonify
from urllib.parse import urlencode
import secrets
from datetime import datetime, timedelta
from database.connection import db_manager
from config import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, FLASK_SECRET_KEY
import time

# Cache simples para evitar rate limits
_token_cache = {}
_cache_ttl = 300  # 5 minutos
_rate_limit_until = 0  # Timestamp até quando o rate limit está ativo

def is_rate_limited():
    """Verifica se estamos em rate limit"""
    return time.time() < _rate_limit_until

def set_rate_limit(duration_seconds=60):
    """Define rate limit por um período"""
    global _rate_limit_until
    _rate_limit_until = time.time() + duration_seconds
    logger.warning(f"Rate limit ativado por {duration_seconds} segundos")

# Configuração de logging
logger = logging.getLogger(__name__)

# URLs do Discord OAuth2
DISCORD_OAUTH2_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_BASE = "https://discord.com/api/v10"

# Scopes necessários para o OAuth2
OAUTH2_SCOPES = [
    "identify",  # Obter informações básicas do usuário
    "guilds"     # Obter lista de servidores do usuário
]

# Permissões do bot para convite
BOT_PERMISSIONS = [
    "manage_messages",    # Gerenciar mensagens
    "moderate_members",   # Moderar membros (timeout)
    "ban_members",        # Banir membros
    "view_channel",       # Ver canais
    "send_messages",      # Enviar mensagens
    "embed_links",        # Enviar embeds
    "attach_files",       # Anexar arquivos
    "read_message_history" # Ler histórico de mensagens
]


def setup_auth(app: Flask):
    """Configura o sistema de autenticação no Flask"""
    
    # Configura a chave secreta da sessão
    app.secret_key = FLASK_SECRET_KEY or secrets.token_hex(32)
    
    @app.route('/login')
    def login():
        """Inicia o processo de login OAuth2"""
        try:
            # Verifica se estamos em rate limit
            if is_rate_limited():
                flash("Rate limit ativo. Aguarde alguns minutos antes de tentar novamente.", "warning")
                logger.warning("Tentativa de login bloqueada por rate limit")
                return redirect(url_for('index'))
            
            # Gera um state aleatório para segurança
            state = secrets.token_urlsafe(32)
            session['oauth_state'] = state
            
            # Parâmetros para a URL de autorização
            params = {
                'client_id': DISCORD_CLIENT_ID,
                'redirect_uri': url_for('callback', _external=True),
                'response_type': 'code',
                'scope': ' '.join(OAUTH2_SCOPES),
                'state': state
            }
            
            # URL de autorização
            auth_url = f"{DISCORD_OAUTH2_URL}?{urlencode(params)}"
            
            logger.info(f"Redirecionando para OAuth2: {auth_url}")
            return redirect(auth_url)
            
        except Exception as e:
            logger.error(f"Erro no login OAuth2: {e}")
            flash("Erro ao iniciar o login. Tente novamente.", "error")
            return redirect(url_for('index'))
    
    @app.route('/callback')
    def callback():
        """Processa o callback do OAuth2"""
        try:
            # Verifica se há código de autorização
            code = request.args.get('code')
            state = request.args.get('state')
            
            if not code:
                flash("Código de autorização não fornecido.", "error")
                return redirect(url_for('index'))
            
            # Verifica o state para segurança
            if state != session.get('oauth_state'):
                flash("Estado de segurança inválido.", "error")
                return redirect(url_for('index'))
            
            # Remove o state da sessão
            session.pop('oauth_state', None)
            
            # Troca o código por um token de acesso
            token_data = exchange_code_for_token(code)
            
            if not token_data:
                flash("Rate limit do Discord atingido. Aguarde alguns minutos e tente novamente.", "error")
                logger.warning("Falha ao obter token - possivelmente rate limit")
                return redirect(url_for('index'))
            
            # Obtém informações do usuário
            user_data = get_user_info(token_data['access_token'])
            
            if not user_data:
                flash("Falha ao obter informações do usuário.", "error")
                return redirect(url_for('index'))
            
            # Obtém lista de servidores do usuário (apenas servidores de admin para economizar espaço)
            guilds_data = get_user_guilds(token_data['access_token'])
            admin_guilds = []
            if guilds_data:
                for guild in guilds_data:
                    permissions = int(guild.get('permissions', 0))
                    if permissions & 0x8:  # 0x8 = Administrator permission
                        admin_guilds.append({
                            'id': guild['id'],
                            'name': guild['name'],
                            'icon': guild.get('icon')
                        })
            
            # Salva informações na sessão (otimizada para reduzir tamanho do cookie)
            session['user'] = {
                'id': int(user_data['id']),
                'username': user_data['username'],
                'discriminator': user_data.get('discriminator', '0'),
                'avatar': user_data.get('avatar'),
                'verified': user_data.get('verified', False),
                'admin_guilds': admin_guilds,  # Apenas servidores de admin
                'login_time': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))).isoformat()
            }
            
            # Salva tokens separadamente (não na sessão para segurança)
            session['access_token'] = token_data['access_token']
            session['refresh_token'] = token_data.get('refresh_token')
            
            # Verifica se o usuário está cadastrado no sistema
            user_db = db_manager.execute_one_sync(
                "SELECT * FROM usuarios WHERE id_discord = $1", 
                int(user_data['id'])
            )
            
            if user_db:
                session['user']['cadastrado'] = True
                session['user']['categoria'] = user_db['categoria']
                session['user']['nome_completo'] = user_db['username']
                flash(f"Bem-vindo de volta, {user_db['username']}!", "success")
            else:
                session['user']['cadastrado'] = False
                flash("Login realizado com sucesso! Complete seu cadastro no Discord.", "info")
            
            logger.info(f"Login bem-sucedido para usuário {user_data['username']} ({user_data['id']})")
            
            # Redireciona para o dashboard
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f"Erro no callback OAuth2: {e}")
            flash("Erro durante o login. Tente novamente.", "error")
            return redirect(url_for('index'))
    
    @app.route('/logout')
    def logout():
        """Realiza logout do usuário"""
        try:
            # Limpa a sessão
            session.clear()
            flash("Logout realizado com sucesso!", "success")
            
            logger.info("Logout realizado")
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"Erro no logout: {e}")
            flash("Erro durante o logout.", "error")
            return redirect(url_for('index'))
    
    @app.route('/api/user')
    def api_user():
        """API endpoint para informações do usuário"""
        try:
            if 'user' not in session:
                return jsonify({'error': 'Não autenticado'}), 401
            
            user_data = session['user'].copy()
            
            # Adiciona informações dos tokens se necessário (sem expor os valores)
            user_data['has_access_token'] = bool(session.get('access_token'))
            user_data['has_refresh_token'] = bool(session.get('refresh_token'))
            
            return jsonify(user_data)
            
        except Exception as e:
            logger.error(f"Erro na API do usuário: {e}")
            return jsonify({'error': 'Erro interno'}), 500


def exchange_code_for_token(code: str) -> dict:
    """Troca o código de autorização por um token de acesso com retry automático"""
    import time
    import random
    
    max_retries = 3
    base_delay = 2  # segundos
    
    for attempt in range(max_retries):
        try:
            data = {
                'client_id': DISCORD_CLIENT_ID,
                'client_secret': DISCORD_CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': url_for('callback', _external=True)
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'GuardiãoBETA/1.0'
            }
            
            import requests
            response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                logger.info("Token de acesso obtido com sucesso")
                return token_data
            elif response.status_code == 429:  # Rate limited
                # Ativa rate limit global
                set_rate_limit(300)  # 5 minutos
                if attempt < max_retries - 1:
                    # Backoff exponencial com jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Rate limit atingido. Tentando novamente em {delay:.1f}s (tentativa {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error("Rate limit persistente após múltiplas tentativas")
                    return None
            else:
                error_text = response.text
                logger.error(f"Erro ao obter token: {response.status_code} - {error_text}")
                return None
                        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Timeout na requisição. Tentando novamente em {delay}s")
                time.sleep(delay)
                continue
            else:
                logger.error("Timeout persistente após múltiplas tentativas")
                return None
        except Exception as e:
            logger.error(f"Erro ao trocar código por token: {e}")
            return None
    
    return None


def get_user_info(access_token: str) -> dict:
    """Obtém informações do usuário do Discord"""
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        import requests
        response = requests.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            logger.info(f"Informações do usuário obtidas: {user_data['username']}")
            return user_data
        else:
            error_text = response.text
            logger.error(f"Erro ao obter informações do usuário: {response.status_code} - {error_text}")
            return None
                    
    except Exception as e:
        logger.error(f"Erro ao obter informações do usuário: {e}")
        return None


def get_user_guilds(access_token: str) -> list:
    """Obtém lista de servidores do usuário"""
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        import requests
        response = requests.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=headers)
        if response.status_code == 200:
            guilds_data = response.json()
            logger.info(f"Lista de servidores obtida: {len(guilds_data)} servidores")
            return guilds_data
        else:
            error_text = response.text
            logger.error(f"Erro ao obter servidores: {response.status_code} - {error_text}")
            return None
                    
    except Exception as e:
        logger.error(f"Erro ao obter servidores: {e}")
        return None


def login_required(f):
    """Decorator para rotas que requerem login"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Você precisa fazer login para acessar esta página.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator para rotas que requerem permissões de administrador"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Você precisa fazer login para acessar esta página.", "warning")
            return redirect(url_for('login'))
        
        user_category = session['user'].get('categoria', '')
        if user_category not in ['Moderador', 'Administrador']:
            flash("Você não tem permissão para acessar esta página.", "error")
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_user_guilds_admin():
    """Obtém servidores onde o usuário é administrador"""
    try:
        if 'user' not in session:
            return []
        
        # Retorna diretamente os servidores de admin já filtrados
        return session['user'].get('admin_guilds', [])
        
    except Exception as e:
        logger.error(f"Erro ao obter servidores de admin: {e}")
        return []


def get_bot_invite_url(guild_id: str = None) -> str:
    """Gera URL de convite do bot com permissões corretas"""
    try:
        # Calcula permissões do bot
        permissions = 0
        for permission in BOT_PERMISSIONS:
            # Mapeia permissões para valores numéricos
            permission_map = {
                "manage_messages": 0x00002000,
                "moderate_members": 0x00000010,
                "ban_members": 0x00000004,
                "view_channel": 0x00000400,
                "send_messages": 0x00000800,
                "embed_links": 0x00004000,
                "attach_files": 0x00008000,
                "read_message_history": 0x00010000
            }
            permissions |= permission_map.get(permission, 0)
        
        # URL base do convite
        base_url = f"https://discord.com/api/oauth2/authorize"
        
        params = {
            'client_id': DISCORD_CLIENT_ID,
            'permissions': str(permissions),
            'scope': 'bot applications.commands'
        }
        
        if guild_id:
            params['guild_id'] = guild_id
        
        return f"{base_url}?{urlencode(params)}"
        
    except Exception as e:
        logger.error(f"Erro ao gerar URL de convite: {e}")
        return "#"


def get_user_avatar_url(user_id: str, avatar_hash: str = None, discriminator: str = "0") -> str:
    """Gera URL do avatar do usuário"""
    try:
        if avatar_hash:
            # Avatar personalizado
            if avatar_hash.startswith('a_'):
                # Avatar animado (GIF)
                return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.gif?size=256"
            else:
                # Avatar estático (PNG)
                return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=256"
        else:
            # Avatar padrão baseado no discriminator
            default_avatar = int(discriminator) % 5
            return f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"
            
    except Exception as e:
        logger.error(f"Erro ao gerar URL do avatar: {e}")
        return "https://cdn.discordapp.com/embed/avatars/0.png"


def get_guild_icon_url(guild_id: str, icon_hash: str = None) -> str:
    """Gera URL do ícone do servidor"""
    try:
        if icon_hash:
            if icon_hash.startswith('a_'):
                # Ícone animado (GIF)
                return f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.gif?size=256"
            else:
                # Ícone estático (PNG)
                return f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png?size=256"
        else:
            # Ícone padrão
            return "https://cdn.discordapp.com/embed/icons/0.png"
            
    except Exception as e:
        logger.error(f"Erro ao gerar URL do ícone: {e}")
        return "https://cdn.discordapp.com/embed/icons/0.png"
