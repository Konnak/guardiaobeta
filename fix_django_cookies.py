#!/usr/bin/env python3
"""
Script para corrigir problemas de cookies do Django Admin
Execute este script no servidor Discloud
"""

import os
import sys
import subprocess

def fix_django_cookies():
    """Corrige problemas de cookies do Django Admin"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        os.chdir(django_dir)
        
        print("🔧 Corrigindo problemas de cookies do Django Admin...")
        
        # 1. Limpa sessões antigas
        print("\n🧹 Limpando sessões antigas...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User

# Limpa todas as sessões
sessions_count = Session.objects.count()
Session.objects.all().delete()
print(f"✅ {sessions_count} sessões antigas removidas")

# Verifica usuários
users = User.objects.all()
print(f"Total de usuários: {users.count()}")
for user in users:
    print(f"  - {user.username} (staff: {user.is_staff}, superuser: {user.is_superuser}, active: {user.is_active})")
'''
        ], check=True)
        
        # 2. Cria superusuário se necessário
        print("\n👤 Criando/verificando superusuário...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User

# Remove usuário admin se existir
try:
    admin_user = User.objects.get(username="admin")
    admin_user.delete()
    print("✅ Usuário admin antigo removido")
except User.DoesNotExist:
    pass

# Cria novo superusuário
admin_user = User.objects.create_superuser(
    username="admin",
    email="admin@guardiaobeta.com",
    password="admin123"
)
print(f"✅ Superusuário admin criado: staff={admin_user.is_staff}, superuser={admin_user.is_superuser}, active={admin_user.is_active}")
'''
        ], check=True)
        
        # 3. Verifica configurações
        print("\n⚙️ Verificando configurações...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.conf import settings

configs = [
    "DEBUG",
    "ALLOWED_HOSTS", 
    "CSRF_COOKIE_DOMAIN",
    "SESSION_COOKIE_DOMAIN",
    "CSRF_COOKIE_SECURE",
    "SESSION_COOKIE_SECURE",
    "CSRF_TRUSTED_ORIGINS"
]

for config in configs:
    value = getattr(settings, config, "Not set")
    print(f"{config}: {value}")
'''
        ], check=True)
        
        print("\n🎉 Correção de cookies concluída!")
        
    except Exception as e:
        print(f"❌ Erro durante correção: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_django_cookies()
