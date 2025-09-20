#!/usr/bin/env python3
"""
Script para debugar o redirect loop do Django Admin
Execute este script no servidor Discloud
"""

import os
import sys
import subprocess

def debug_django_auth_loop():
    """Debuga o redirect loop do Django Admin"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        os.chdir(django_dir)
        
        print("🔍 Investigando redirect loop do Django Admin...")
        
        # 1. Verifica usuários Django
        print("\n📊 Verificando usuários Django...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User
from django.conf import settings

print(f"DEBUG: {settings.DEBUG}")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"CSRF_COOKIE_DOMAIN: {getattr(settings, \"CSRF_COOKIE_DOMAIN\", \"Not set\")}")
print(f"SESSION_COOKIE_DOMAIN: {getattr(settings, \"SESSION_COOKIE_DOMAIN\", \"Not set\")}")

users = User.objects.all()
print(f"Total de usuários: {users.count()}")
for user in users:
    print(f"  - {user.username} (staff: {user.is_staff}, superuser: {user.is_superuser}, active: {user.is_active})")
'''
        ], check=True)
        
        # 2. Testa autenticação
        print("\n🔐 Testando autenticação...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

# Testa login com admin
user = authenticate(username="admin", password="admin123")
if user:
    print(f"✅ Login admin bem-sucedido: {user.username}")
    print(f"  - is_staff: {user.is_staff}")
    print(f"  - is_superuser: {user.is_superuser}")
    print(f"  - is_active: {user.is_active}")
else:
    print("❌ Login admin falhou")
    
    # Verifica se usuário existe
    try:
        user = User.objects.get(username="admin")
        print(f"Usuário admin existe: staff={user.is_staff}, superuser={user.is_superuser}, active={user.is_active}")
    except User.DoesNotExist:
        print("❌ Usuário admin não existe")
'''
        ], check=True)
        
        # 3. Verifica configurações de sessão
        print("\n🍪 Verificando configurações de sessão...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.conf import settings

session_settings = [
    "SESSION_ENGINE",
    "SESSION_COOKIE_NAME", 
    "SESSION_COOKIE_AGE",
    "SESSION_COOKIE_DOMAIN",
    "SESSION_COOKIE_SECURE",
    "SESSION_COOKIE_HTTPONLY",
    "SESSION_COOKIE_SAMESITE",
    "CSRF_COOKIE_DOMAIN",
    "CSRF_COOKIE_SECURE",
    "CSRF_TRUSTED_ORIGINS"
]

for setting in session_settings:
    value = getattr(settings, setting, "Not set")
    print(f"{setting}: {value}")
'''
        ], check=True)
        
        print("\n🎉 Debug de redirect loop concluído!")
        
    except Exception as e:
        print(f"❌ Erro durante debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_django_auth_loop()
