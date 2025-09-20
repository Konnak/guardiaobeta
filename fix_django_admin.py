#!/usr/bin/env python3
"""
Script para corrigir Django Admin - criar superusuário e verificar configurações
Execute este script no servidor Discloud
"""

import os
import sys
import subprocess

def fix_django_admin():
    """Corrige Django Admin criando superusuário"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        os.chdir(django_dir)
        
        print("🛠️ Corrigindo Django Admin...")
        
        # 1. Executa migrações
        print("📊 Executando migrações...")
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--run-syncdb'], 
                      check=True, capture_output=True, text=True)
        print("✅ Migrações executadas")
        
        # 2. Cria superusuário
        print("👑 Criando superusuário...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User
import os

# Remove superusuários existentes
User.objects.filter(is_superuser=True).delete()
print("🗑️ Superusuários antigos removidos")

# Cria novo superusuário
user = User.objects.create_superuser(
    username="admin",
    email="admin@guardiaobeta.com", 
    password="admin123"
)
print(f"✅ Superusuário criado: {user.username}")
print(f"📧 Email: {user.email}")
print(f"🔑 Senha: admin123")
print(f"✅ Ativo: {user.is_active}")
print(f"👑 Superusuário: {user.is_superuser}")

# Verifica se foi criado corretamente
users = User.objects.filter(is_superuser=True)
print(f"📊 Total de superusuários: {users.count()}")
for u in users:
    print(f"   - {u.username} ({u.email})")
'''
        ], check=True)
        
        # 3. Verifica configurações
        print("\n🔍 Verificando configurações...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.conf import settings
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"CSRF_TRUSTED_ORIGINS: {getattr(settings, \"CSRF_TRUSTED_ORIGINS\", \"Não configurado\")}")
print(f"DEBUG: {settings.DEBUG}")
'''
        ], check=True)
        
        print("\n🎉 Django Admin corrigido com sucesso!")
        print("🔑 Credenciais:")
        print("   Usuário: admin")
        print("   Senha: admin123")
        print("\n🌐 Acesse: https://guardiaobeta.discloud.app/admin")
        
    except Exception as e:
        print(f"❌ Erro ao corrigir Django Admin: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_django_admin()
