#!/usr/bin/env python3
"""
Script para testar cookies Django Admin
Execute este script no servidor Discloud
"""

import os
import sys
import subprocess

def test_cookies():
    """Testa configurações de cookies Django"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        os.chdir(django_dir)
        
        print("🍪 Testando configurações de cookies Django...")
        
        # 1. Verifica configurações de cookies
        print("\n🔧 Verificando configurações de cookies...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.conf import settings
print(f"CSRF_COOKIE_DOMAIN: {getattr(settings, 'CSRF_COOKIE_DOMAIN', 'Não configurado')}")
print(f"SESSION_COOKIE_DOMAIN: {getattr(settings, 'SESSION_COOKIE_DOMAIN', 'Não configurado')}")
print(f"CSRF_COOKIE_SECURE: {getattr(settings, 'CSRF_COOKIE_SECURE', 'Não configurado')}")
print(f"SESSION_COOKIE_SECURE: {getattr(settings, 'SESSION_COOKIE_SECURE', 'Não configurado')}")
print(f"CSRF_COOKIE_SAMESITE: {getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Não configurado')}")
print(f"SESSION_COOKIE_SAMESITE: {getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Não configurado')}")
'''
        ], check=True)
        
        # 2. Testa criação de sessão
        print("\n🔐 Testando criação de sessão...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.sessions.backends.db import SessionStore

# Testa autenticação
user = authenticate(username="admin", password="admin123")
if user:
    print(f"✅ Usuário autenticado: {user.username}")
    
    # Cria sessão
    session = SessionStore()
    session['user_id'] = user.id
    session.save()
    print(f"✅ Sessão criada: {session.session_key}")
    
    # Verifica sessões existentes
    sessions = Session.objects.all()
    print(f"📊 Total de sessões: {sessions.count()}")
    for s in sessions[:3]:  # Mostra apenas 3
        print(f"   - {s.session_key} | {s.expire_date}")
else:
    print("❌ Falha na autenticação")
'''
        ], check=True)
        
        print("\n🎉 Teste de cookies concluído!")
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cookies()
