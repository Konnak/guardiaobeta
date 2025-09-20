#!/usr/bin/env python
"""
Script para inicializar o Django Admin do Guardião BETA
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.contrib.auth.models import User

def init_django():
    """Inicializa o Django"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'guardiao_admin.settings')
    django.setup()

def create_superuser():
    """Cria um superusuário para o admin"""
    username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
    email = os.getenv('DJANGO_ADMIN_EMAIL', 'admin@guardiaobeta.com')
    password = os.getenv('DJANGO_ADMIN_PASSWORD', 'guardiao2025')
    
    if User.objects.filter(username=username).exists():
        print(f"✅ Superusuário '{username}' já existe!")
        return
    
    User.objects.create_superuser(username, email, password)
    print(f"✅ Superusuário '{username}' criado com sucesso!")
    print(f"   Email: {email}")
    print(f"   Senha: {password}")

def run_migrations():
    """Executa as migrações"""
    print("🔄 Executando migrações...")
    execute_from_command_line(['manage.py', 'makemigrations'])
    execute_from_command_line(['manage.py', 'migrate'])
    print("✅ Migrações executadas!")

def main():
    """Função principal"""
    print("🛡️ Inicializando Django Admin do Guardião BETA...")
    
    # Inicializa Django
    init_django()
    
    # Executa migrações
    run_migrations()
    
    # Cria superusuário
    create_superuser()
    
    print("\n🎉 Django Admin inicializado com sucesso!")
    print("\n📋 Informações de acesso:")
    print("   URL: http://localhost:8000/admin/")
    print("   Usuário: admin")
    print("   Senha: guardiao2025")
    print("\n🚀 Para iniciar o servidor:")
    print("   python manage.py runserver")

if __name__ == '__main__':
    main()
