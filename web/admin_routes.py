"""
Rotas Admin - Sistema Guardião BETA
Rotas separadas para teste
"""

import logging
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from database.connection import db_manager

logger = logging.getLogger(__name__)

def setup_admin_routes(app):
    """Configura rotas admin separadas para teste"""
    
    @app.route('/admin-test-simple')
    def admin_test_simple():
        """Teste simples de rota admin"""
        return "<h1>✅ Rota Admin Funcionando!</h1>"
    
    @app.route('/admin-simple')
    def admin_simple():
        """Painel admin simplificado"""
        try:
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Painel Admin</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
                    .content { margin: 20px 0; }
                    .btn { background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🛡️ Painel Administrativo</h1>
                        <p>Sistema Guardião BETA</p>
                    </div>
                    <div class="content">
                        <h2>✅ Painel Admin Funcionando!</h2>
                        <p>As rotas admin estão sendo registradas corretamente.</p>
                        <a href="/dashboard" class="btn">Voltar ao Dashboard</a>
                    </div>
                </div>
            </body>
            </html>
            """
        except Exception as e:
            logger.error(f"Erro no painel admin simples: {e}")
            return f"Erro: {e}"
