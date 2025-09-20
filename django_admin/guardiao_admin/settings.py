"""
Django settings for guardiao_admin project.
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório pai ao path para importar config
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

try:
    from config import POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET
except ImportError:
    # Fallback para variáveis de ambiente
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'guardiaobeta')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'userguardiaobeta')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'SUA_SENHA_AQUI')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'guardiaobeta')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '')
    DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', '')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-guardiao-beta-admin-2025')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*', 'guardiaobeta.discloud.app', 'localhost', '127.0.0.1']  # Para produção

# CSRF Trusted Origins - permite o domínio Discloud
CSRF_TRUSTED_ORIGINS = [
    'https://guardiaobeta.discloud.app',
    'http://localhost:8001',
    'http://127.0.0.1:8001',
]

# Configurações de cookies para funcionar com proxy
# Removido domínio específico para funcionar com proxy
CSRF_COOKIE_SECURE = False  # Desabilitado para debug
SESSION_COOKIE_SECURE = False  # Desabilitado para debug
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
# Cookies funcionam melhor sem domínio específico em proxy
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_DOMAIN = None

# Configurações Discord OAuth2
DISCORD_CLIENT_ID = DISCORD_CLIENT_ID
DISCORD_CLIENT_SECRET = DISCORD_CLIENT_SECRET

# Backend de autenticação customizado
AUTHENTICATION_BACKENDS = [
    'guardiao.backends.DiscordAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'guardiao',  # Nossa app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'guardiao_admin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'guardiao_admin.wsgi.application'

# Database - usando o mesmo PostgreSQL do bot
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': POSTGRES_DB,
        'USER': POSTGRES_USER,
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': POSTGRES_HOST,
        'PORT': POSTGRES_PORT,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Admin customization
ADMIN_SITE_HEADER = "Guardião BETA - Painel Administrativo"
ADMIN_SITE_TITLE = "Guardião BETA Admin"
ADMIN_INDEX_TITLE = "Bem-vindo ao Painel de Administração do Guardião BETA"

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'guardiao': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
