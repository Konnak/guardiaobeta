#!/usr/bin/env python3
"""
Script para iniciar o Django Admin Panel do Sistema Guardião BETA
"""

import os
import sys
import subprocess
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_django_admin():
    """Inicia o Django Admin Panel"""
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
            logger.info("Instalando Django...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'Django>=4.2.0', 'psycopg2-binary>=2.9.0'], check=True)
        
        # Executa migrações
        logger.info("Executando migrações...")
        subprocess.run([sys.executable, 'manage.py', 'makemigrations'], check=True)
        subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)
        
        # Verifica se existe superusuário
        logger.info("Verificando superusuário...")
        try:
            result = subprocess.run([sys.executable, 'manage.py', 'shell', '-c', 'from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).count())'], 
                                  capture_output=True, text=True, check=True)
            if result.stdout.strip() == '0':
                logger.info("Criando superusuário...")
                subprocess.run([sys.executable, 'manage.py', 'createsuperuser', '--noinput', '--username', 'admin', '--email', 'admin@guardiaobeta.com'], 
                              check=True)
                # Define senha padrão
                subprocess.run([sys.executable, 'manage.py', 'shell', '-c', 
                              'from django.contrib.auth.models import User; u = User.objects.get(username="admin"); u.set_password("admin123"); u.save()'], 
                              check=True)
                logger.info("Superusuário criado: admin / admin123")
        except Exception as e:
            logger.warning(f"Erro ao verificar/criar superusuário: {e}")
        
        # Inicia o servidor Django
        logger.info("Iniciando Django Admin Panel na porta 8001...")
        logger.info("Acesse: http://localhost:8001/admin/")
        logger.info("Usuário: admin / Senha: admin123")
        
        subprocess.run([sys.executable, 'manage.py', 'runserver', '0.0.0.0:8001'], check=True)
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao executar comando: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro ao iniciar Django Admin: {e}")
        return False

if __name__ == "__main__":
    success = start_django_admin()
    sys.exit(0 if success else 1)
