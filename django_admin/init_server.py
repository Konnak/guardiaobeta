#!/usr/bin/env python
"""
Script de inicialização do servidor Django Admin
Executa automaticamente no servidor
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def init_django_admin():
    """Inicializa o Django Admin no servidor"""
    print("🚀 Inicializando Django Admin no servidor...")
    
    # Diretório do Django Admin
    django_dir = Path(__file__).parent
    
    try:
        # 1. Executa migrações
        print("📊 Executando migrações...")
        result = subprocess.run([
            sys.executable, 'manage.py', 'migrate', '--run-syncdb'
        ], cwd=django_dir, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Migrações executadas com sucesso!")
        else:
            print(f"⚠️ Aviso nas migrações: {result.stderr}")
        
        # 2. Cria usuário admin
        print("👤 Criando usuário admin...")
        result = subprocess.run([
            sys.executable, 'manage.py', 'create_admin'
        ], cwd=django_dir, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Usuário admin criado/atualizado!")
            print(result.stdout)
        else:
            print(f"⚠️ Aviso na criação do admin: {result.stderr}")
        
        # 3. Coleta arquivos estáticos
        print("📁 Coletando arquivos estáticos...")
        result = subprocess.run([
            sys.executable, 'manage.py', 'collectstatic', '--noinput'
        ], cwd=django_dir, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Arquivos estáticos coletados!")
        else:
            print(f"⚠️ Aviso na coleta de estáticos: {result.stderr}")
        
        print("🎉 Django Admin inicializado com sucesso!")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout na inicialização do Django Admin")
        return False
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        return False

if __name__ == '__main__':
    success = init_django_admin()
    if not success:
        sys.exit(1)
