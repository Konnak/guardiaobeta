#!/usr/bin/env python3
"""
Script para debugar autenticação Django Admin
Execute este script no servidor Discloud
"""

import os
import sys
import subprocess

def debug_django_auth():
    """Debuga problemas de autenticação Django"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        os.chdir(django_dir)
        
        print("🔍 Investigando problemas de autenticação Django...")
        
        # 1. Verifica se existem usuários
        print("\n📊 Verificando usuários existentes...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User
users = User.objects.all()
print(f"Total de usuários: {users.count()}")
for user in users:
    print(f"  - {user.username} | {user.email} | Super: {user.is_superuser} | Ativo: {user.is_active}")
'''
        ], check=True)
        
        # 2. Verifica configurações de autenticação
        print("\n🔧 Verificando configurações...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.conf import settings
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"CSRF_TRUSTED_ORIGINS: {getattr(settings, \"CSRF_TRUSTED_ORIGINS\", \"Não configurado\")}")
print(f"DEBUG: {settings.DEBUG}")
print(f"SECRET_KEY configurado: {bool(settings.SECRET_KEY)}")
'''
        ], check=True)
        
        # 3. Testa autenticação
        print("\n🔐 Testando autenticação...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

# Testa credenciais
user = authenticate(username="admin", password="admin123")
if user:
    print(f"✅ Autenticação bem-sucedida: {user.username}")
    print(f"   Superusuário: {user.is_superuser}")
    print(f"   Ativo: {user.is_active}")
else:
    print("❌ Falha na autenticação")
    
    # Verifica se usuário existe
    try:
        user = User.objects.get(username="admin")
        print(f"👤 Usuário existe: {user.username}")
        print(f"   Superusuário: {user.is_superuser}")
        print(f"   Ativo: {user.is_active}")
        print(f"   Último login: {user.last_login}")
        
        # Testa senha
        if user.check_password("admin123"):
            print("✅ Senha correta")
        else:
            print("❌ Senha incorreta")
            
    except User.DoesNotExist:
        print("❌ Usuário 'admin' não existe")
'''
        ], check=True)
        
        # 4. Cria superusuário se necessário
        print("\n🛠️ Criando/Corrigindo superusuário...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User

# Remove usuário admin se existir
User.objects.filter(username="admin").delete()
print("🗑️ Usuário admin antigo removido")

# Cria novo superusuário
user = User.objects.create_superuser(
    username="admin",
    email="admin@guardiaobeta.com", 
    password="admin123"
)
print(f"✅ Superusuário criado: {user.username}")
print(f"   Email: {user.email}")
print(f"   Superusuário: {user.is_superuser}")
print(f"   Ativo: {user.is_active}")

# Testa autenticação
from django.contrib.auth import authenticate
auth_user = authenticate(username="admin", password="admin123")
if auth_user:
    print("✅ Autenticação testada com sucesso!")
else:
    print("❌ Falha na autenticação após criação")
'''
        ], check=True)
        
        print("\n🎉 Debug concluído!")
        print("🔑 Credenciais:")
        print("   Usuário: admin")
        print("   Senha: admin123")
        print("\n🌐 Acesse: https://guardiaobeta.discloud.app/admin")
        
    except Exception as e:
        print(f"❌ Erro durante debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_django_auth()
