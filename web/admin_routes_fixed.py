"""
Rotas Admin Fixas - Sistema Guardião BETA
Versão sem dependências do banco de dados para teste
"""

import logging

logger = logging.getLogger(__name__)

def setup_admin_routes_fixed(app):
    """Configura rotas admin sem dependências do banco de dados"""
    
    @app.route('/admin-fixed')
    def admin_fixed():
        """Rota admin fixa para teste"""
        try:
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Admin Fixo - Sistema Guardião</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }
                    .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .header { background: linear-gradient(135deg, #27ae60, #2ecc71); color: white; padding: 25px; border-radius: 8px; margin-bottom: 30px; }
                    .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    .btn { background: #3498db; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 5px; }
                    .btn:hover { background: #2980b9; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✅ Admin Fixo Funcionando!</h1>
                        <p>Sistema Guardião BETA - Rota sem dependências</p>
                    </div>
                    
                    <div class="success">
                        <h3>🎉 SUCESSO!</h3>
                        <p>A rota admin está funcionando perfeitamente sem dependências do banco de dados.</p>
                        <p><strong>Problema identificado:</strong> A importação do <code>db_manager</code> está causando falha no carregamento das rotas.</p>
                    </div>
                    
                    <div style="margin-top: 30px;">
                        <h3>🔧 Próximos Passos:</h3>
                        <ul>
                            <li>✅ Rota admin funcionando</li>
                            <li>🔧 Corrigir importação do db_manager</li>
                            <li>🔧 Implementar funcionalidades do banco</li>
                            <li>🔧 Adicionar verificações de segurança</li>
                        </ul>
                        
                        <div style="margin-top: 30px;">
                            <a href="/dashboard" class="btn">📊 Dashboard</a>
                            <a href="/admin-simple" class="btn">🔧 Admin Simples</a>
                            <a href="/" class="btn">🏠 Início</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
        except Exception as e:
            logger.error(f"Erro na rota admin fixa: {e}")
            return f"Erro: {e}"
