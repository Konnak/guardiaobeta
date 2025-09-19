"""
Configuração de teste para desenvolvimento local
Usa SQLite em memória para testes rápidos
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Credenciais do Bot Discord (necessárias para testes)
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "123456789")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "test_secret")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "test_token")

# Configurações de teste (SQLite em memória)
POSTGRES_DB = ":memory:"  # SQLite em memória
POSTGRES_USER = "test"
POSTGRES_PASSWORD = "test"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432

# Configurações da Aplicação Web
WEB_PORT = os.getenv("WEB_PORT", 8080)
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "test-secret-key")

# Outras configurações
BOT_PREFIX = "!"

# Configurações específicas para testes
TEST_MODE = True
DEBUG = True
