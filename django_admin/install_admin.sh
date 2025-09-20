#!/bin/bash

echo "🛡️ Instalando Django Admin do Guardião BETA..."

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "⚠️ Arquivo .env não encontrado. Criando arquivo de exemplo..."
    cat > .env << EOF
POSTGRES_DB=guardiaobeta
POSTGRES_USER=userguardiaobeta
POSTGRES_PASSWORD=SUA_SENHA_AQUI
POSTGRES_HOST=guardiaobeta
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=django-insecure-guardiao-beta-admin-2025
DEBUG=True
DJANGO_ADMIN_USERNAME=admin
DJANGO_ADMIN_EMAIL=admin@guardiaobeta.com
DJANGO_ADMIN_PASSWORD=guardiao2025
EOF
    echo "✅ Arquivo .env criado! Edite com suas configurações."
fi

# Inicializar Django
echo "🔄 Inicializando Django Admin..."
python init_admin.py

echo ""
echo "🎉 Django Admin instalado com sucesso!"
echo ""
echo "📋 Informações de acesso:"
echo "   URL: http://localhost:8000/admin/"
echo "   Usuário: admin"
echo "   Senha: guardiao2025"
echo ""
echo "🚀 Para iniciar o servidor:"
echo "   python manage.py runserver"
echo ""
echo "📖 Para mais informações, consulte o README.md"
