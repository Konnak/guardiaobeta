#!/usr/bin/env python3
"""
Teste para verificar se as rotas estão sendo registradas corretamente
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
    
    print("🔍 Testando carregamento das rotas...")
    
    # Testa importação das funções
    try:
        from web.routes import setup_routes
        print("✅ Importação de setup_routes OK")
        
        # Tenta configurar as rotas
        setup_routes(app)
        print("✅ setup_routes executado com sucesso")
        
        # Verifica se a rota foi registrada
        with app.app_context():
            rules = [str(rule) for rule in app.url_map.iter_rules()]
            admin_routes = [rule for rule in rules if '/admin' in rule]
            
            print(f"📋 Rotas encontradas: {len(rules)}")
            print(f"📋 Rotas admin encontradas: {len(admin_routes)}")
            
            for route in admin_routes:
                print(f"  - {route}")
                
            if '/admin' in rules:
                print("✅ Rota /admin encontrada!")
            else:
                print("❌ Rota /admin NÃO encontrada!")
                
    except Exception as e:
        print(f"❌ Erro ao carregar rotas: {e}")
        import traceback
        traceback.print_exc()
        
    # Testa rotas admin separadas
    try:
        from web.admin_routes import setup_admin_routes
        print("✅ Importação de setup_admin_routes OK")
        
        setup_admin_routes(app)
        print("✅ setup_admin_routes executado com sucesso")
        
        # Verifica novamente
        with app.app_context():
            rules = [str(rule) for rule in app.url_map.iter_rules()]
            admin_routes = [rule for rule in rules if '/admin' in rule]
            
            print(f"📋 Total de rotas admin após setup_admin_routes: {len(admin_routes)}")
            for route in admin_routes:
                print(f"  - {route}")
                
    except Exception as e:
        print(f"❌ Erro ao carregar rotas admin: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"❌ Erro geral: {e}")
    import traceback
    traceback.print_exc()
