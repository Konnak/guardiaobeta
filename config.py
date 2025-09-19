"""
Configurações do Sistema Guardião BETA
Carrega as variáveis de ambiente e define configurações do sistema
"""

import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do Discord Bot
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Configurações do Banco de Dados PostgreSQL
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

# URL de conexão do banco de dados
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Configurações da Aplicação Web
WEB_PORT = int(os.getenv('WEB_PORT', '8080'))
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

# Configurações do Bot
BOT_PREFIX = os.getenv('BOT_PREFIX', '!')

# Configurações do Sistema
GUARDIAO_MIN_ACCOUNT_AGE_MONTHS = 3
TURN_POINTS_PER_HOUR = 1
MAX_GUARDIANS_PER_REPORT = 10
REQUIRED_VOTES_FOR_DECISION = 5
VOTE_TIMEOUT_MINUTES = 5
DISPENSE_COOLDOWN_MINUTES = 10
INACTIVE_PENALTY_HOURS = 1
PROVA_COOLDOWN_HOURS = 24

# Configurações de Punição
PUNISHMENT_RULES = {
    'ok_majority': 'improcedente',
    'intimidou_3': 1,  # horas de mute
    'intimidou_grave': 6,  # horas de mute
    'grave_3': 12,  # horas de mute
    'grave_4_plus': 24  # horas de ban
}
