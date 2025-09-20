#!/usr/bin/env python3
"""
Script para criar superusuário Django Admin no servidor
Execute este script no servidor Discloud
"""

import os
import sys
import subprocess

def create_superuser():
    """Cria superusuário Django Admin"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        os.chdir(django_dir)
        
        print("🛠️ Criando superusuário Django Admin...")
        
        # Comando para criar superusuário
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.auth.models import User
import os

# Remove superusuários existentes (opcional)
User.objects.filter(is_superuser=True).delete()
print("🗑️ Superusuários antigos removidos")

# Cria novo superusuário
user = User.objects.create_superuser(
    username="admin",
    email="admin@guardiaobeta.com", 
    password="admin123"
)
print(f"✅ Superusuário criado com sucesso!")
print(f"📧 Usuário: {user.username}")
print(f"📧 Email: {user.email}")
print(f"🔑 Senha: admin123")
print(f"✅ Ativo: {user.is_active}")
print(f"👑 Superusuário: {user.is_superuser}")
'''
        ], check=True)
        
        print("\n🎉 Superusuário criado com sucesso!")
        print("🔑 Credenciais:")
        print("   Usuário: admin")
        print("   Senha: admin123")
        print("\n🌐 Acesse: https://guardiaobeta.discloud.app/admin")
        
    except Exception as e:
        print(f"❌ Erro ao criar superusuário: {e}")

if __name__ == "__main__":
    create_superuser()
