#!/usr/bin/env python3
"""
Teste simples para verificar se as rotas estão sendo registradas
SEM dependências do banco de dados
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask
    
    # Cria app Flask de teste
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    
    print("🔍 Testando carregamento das rotas SEM dependências...")
    
    # Define rotas diretamente para teste
    @app.route('/admin')
    def admin_dashboard():
        return "Rota admin funcionando!"
    
    @app.route('/admin-test')
    def admin_test():
        return "Rota admin test funcionando!"
    
    print("✅ Rotas definidas diretamente")
    
    # Verifica se as rotas foram registradas
    with app.app_context():
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        admin_routes = [rule for rule in rules if '/admin' in rule]
        
        print(f"📋 Total de rotas: {len(rules)}")
        print(f"📋 Rotas admin: {len(admin_routes)}")
        
        for route in admin_routes:
            print(f"  ✅ {route}")
            
        if '/admin' in rules:
            print("✅ Rota /admin encontrada!")
        else:
            print("❌ Rota /admin NÃO encontrada!")
            
        # Testa se a rota responde
        with app.test_client() as client:
            response = client.get('/admin')
            print(f"📊 Status da resposta /admin: {response.status_code}")
            if response.status_code == 200:
                print("✅ Rota /admin responde corretamente!")
            else:
                print(f"❌ Rota /admin retornou erro: {response.status_code}")
                
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
