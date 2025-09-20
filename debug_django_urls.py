#!/usr/bin/env python3
"""
Script para debugar URLs Django
Execute este script no servidor Discloud
"""

import os
import sys
import subprocess

def debug_django_urls():
    """Debuga problemas de URLs Django"""
    try:
        # Muda para o diretório do Django
        django_dir = os.path.join(os.path.dirname(__file__), 'django_admin')
        os.chdir(django_dir)
        
        print("🔍 Investigando URLs Django...")
        
        # 1. Verifica se as views existem
        print("\n📊 Verificando views...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
import guardiao.views
print(f"Views disponíveis: {dir(guardiao.views)}")
print(f"discord_login: {hasattr(guardiao.views, \"discord_login\")}")
print(f"discord_callback: {hasattr(guardiao.views, \"discord_callback\")}")
'''
        ], check=True)
        
        # 2. Verifica URLs
        print("\n🔗 Verificando URLs...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
from django.urls import get_resolver
from django.conf import settings
import django
django.setup()

resolver = get_resolver()
print(f"URLs principais: {[str(pattern) for pattern in resolver.url_patterns]}")

# Verifica URLs do admin
admin_patterns = None
for pattern in resolver.url_patterns:
    if hasattr(pattern, 'url_patterns'):
        for sub_pattern in pattern.url_patterns:
            if 'admin' in str(sub_pattern):
                print(f"Admin pattern: {sub_pattern}")
                if hasattr(sub_pattern, 'url_patterns'):
                    for admin_sub in sub_pattern.url_patterns:
                        print(f"  Admin sub: {admin_sub}")
'''
        ], check=True)
        
        # 3. Testa importação
        print("\n📦 Testando importações...")
        subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', 
            '''
try:
    from guardiao.views import discord_login, discord_callback
    print("✅ Importação das views bem-sucedida")
    print(f"discord_login: {discord_login}")
    print(f"discord_callback: {discord_callback}")
except Exception as e:
    print(f"❌ Erro na importação: {e}")
'''
        ], check=True)
        
        print("\n🎉 Debug de URLs concluído!")
        
    except Exception as e:
        print(f"❌ Erro durante debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_django_urls()
