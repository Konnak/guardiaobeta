#!/usr/bin/env python
"""
Script para criar usuário admin padrão
"""

import os
import sys
import django
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

# Configura Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'guardiao_admin.settings')
django.setup()

from django.contrib.auth.models import User

def create_admin_user():
    """Cria usuário admin padrão"""
    username = 'admin'
    password = 'admin123'
    email = 'admin@guardiao.local'
    
    # Verifica se usuário já existe
    if User.objects.filter(username=username).exists():
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        print(f"✅ Usuário '{username}' atualizado com sucesso!")
    else:
        # Cria novo usuário
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        print(f"✅ Usuário '{username}' criado com sucesso!")
    
    print(f"📝 Credenciais:")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    print(f"   Email: {email}")
    print(f"   Staff: {user.is_staff}")
    print(f"   Superuser: {user.is_superuser}")
    print(f"   Active: {user.is_active}")

if __name__ == '__main__':
    create_admin_user()
