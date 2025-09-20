#!/usr/bin/env python3
"""
Script para verificar e criar superusuário Django Admin
"""

import os
import sys
import subprocess

def check_and_create_superuser():
    """Verifica e cria superusuário se necessário"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        os.chdir(django_dir)
        
        print("🔍 Verificando superusuários existentes...")
        
        # Lista todos os superusuários
        result = subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User
superusers = User.objects.filter(is_superuser=True)
if superusers:
    print("=== SUPERUSUÁRIOS EXISTENTES ===")
    for user in superusers:
        print(f"Usuário: {user.username}")
        print(f"Email: {user.email}")
        print(f"Ativo: {user.is_active}")
        print(f"Criado: {user.date_joined}")
        print("---")
else:
    print("❌ Nenhum superusuário encontrado!")
    print("🛠️ Criando superusuário...")
    user = User.objects.create_superuser("admin", "admin@guardiaobeta.com", "admin123")
    print(f"✅ Superusuário criado: {user.username}")
'''
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Erro:", result.stderr)
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    check_and_create_superuser()
