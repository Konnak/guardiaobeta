#!/usr/bin/env python3
"""
Script para inicializar o Django Admin Panel do Sistema Guardião BETA
Executa migrações e cria superusuário automaticamente
"""

import os
import sys
import subprocess
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_django_admin():
    """Inicializa o Django Admin Panel"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        
        if not os.path.exists(django_dir):
            logger.error("Diretório django_admin não encontrado!")
            return False
        
        os.chdir(django_dir)
        logger.info(f"Trabalhando no diretório: {django_dir}")
        
        # Verifica se o Django está instalado
        try:
            import django
            logger.info(f"Django versão: {django.get_version()}")
        except ImportError:
            logger.error("Django não está instalado!")
            return False
        
        # Executa migrações (syncdb para criar tabelas Django)
        logger.info("Executando migrações...")
        try:
            subprocess.run([sys.executable, 'manage.py', 'migrate', '--run-syncdb'], 
                         check=True, capture_output=True, text=True)
            logger.info("Migrações executadas com sucesso")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Erro nas migrações (pode ser normal): {e.stderr}")
        
        # Verifica se existe superusuário
        logger.info("Verificando superusuário...")
        try:
            result = subprocess.run([
                sys.executable, 'manage.py', 'shell', '-c', 
                'from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).count())'
            ], capture_output=True, text=True, check=True)
            
            if result.stdout.strip() == '0':
                logger.info("Criando superusuário...")
                # Cria superusuário
                subprocess.run([
                    sys.executable, 'manage.py', 'shell', '-c',
                    '''
from django.contrib.auth.models import User
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@guardiaobeta.com", "admin123")
    print("Superusuário criado: admin / admin123")
else:
    print("Superusuário já existe")
'''
                ], check=True)
            else:
                logger.info("Superusuário já existe")
                
        except Exception as e:
            logger.warning(f"Erro ao verificar/criar superusuário: {e}")
        
        logger.info("Django Admin Panel inicializado com sucesso!")
        logger.info("Para iniciar: python manage.py runserver 0.0.0.0:8001")
        logger.info("Acesse: http://localhost:8001/admin/")
        logger.info("Usuário: admin / Senha: admin123")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao inicializar Django Admin: {e}")
        return False

if __name__ == "__main__":
    success = init_django_admin()
    sys.exit(0 if success else 1)
