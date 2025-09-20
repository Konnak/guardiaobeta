# 🛡️ Guardião BETA - Django Admin Panel

Painel administrativo Django para gerenciar o Sistema Guardião BETA.

## 🚀 Funcionalidades

### 📊 Dashboard Principal
- Estatísticas gerais do sistema
- Total de usuários, denúncias e guardiões
- Top guardiões por atividade
- Denúncias recentes

### 👥 Gerenciamento de Usuários
- Visualizar todos os usuários cadastrados
- Filtrar por categoria (Civil, Guardião, Administrador)
- Gerenciar status de serviço
- Resetar cooldowns
- Ver histórico de atividade

### 📋 Gerenciamento de Denúncias
- Listar todas as denúncias
- Filtrar por status (Em Análise, Aprovada, Rejeitada)
- Ver detalhes completos de cada denúncia
- Visualizar mensagens capturadas
- Ver votos dos guardiões
- Aprovar/rejeitar denúncias em lote

### 💬 Mensagens Capturadas
- Visualizar todas as mensagens capturadas
- Filtrar por denúncia
- Ver conteúdo e anexos
- Buscar por conteúdo

### 🗳️ Sistema de Votos
- Visualizar votos dos guardiões
- Ver decisões e justificativas
- Estatísticas de votação

### 📈 Estatísticas Avançadas
- Denúncias por status
- Usuários por categoria
- Top denunciantes
- Gráficos de atividade
- Tendências temporais

## 🔧 Instalação

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente
Crie um arquivo `.env` com:
```env
POSTGRES_DB=guardiaobeta
POSTGRES_USER=userguardiaobeta
POSTGRES_PASSWORD=SUA_SENHA_AQUI
POSTGRES_HOST=guardiaobeta
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
```

### 3. Inicializar o Sistema
```bash
python init_admin.py
```

### 4. Iniciar o Servidor
```bash
python manage.py runserver
```

## 🌐 Acesso

- **URL**: http://localhost:8000/admin/
- **Usuário**: admin
- **Senha**: guardiao2025

## 📱 Funcionalidades do Admin

### Ações em Lote
- **Usuários**: Ativar/desativar serviço, resetar cooldowns
- **Denúncias**: Aprovar/rejeitar em lote, marcar como premium

### Filtros Avançados
- Data de criação
- Status
- Categoria de usuário
- Servidor premium

### Busca Inteligente
- Usuários: por username, email, ID Discord
- Denúncias: por hash, motivo, denunciante
- Mensagens: por conteúdo

### Visualizações Personalizadas
- Dashboard com estatísticas em tempo real
- Página de estatísticas com gráficos
- Detalhes completos de denúncias

## 🔒 Segurança

- Autenticação obrigatória
- Permissões por usuário
- Logs de todas as ações
- Proteção CSRF
- Headers de segurança

## 📊 Integração com o Bot

O Django Admin se conecta diretamente ao banco PostgreSQL usado pelo bot Discord, permitindo:

- Visualizar dados em tempo real
- Gerenciar usuários e denúncias
- Monitorar atividade do sistema
- Ajustar configurações

## 🛠️ Desenvolvimento

### Estrutura do Projeto
```
django_admin/
├── guardiao_admin/          # Configurações do Django
├── guardiao/                # App principal
│   ├── models.py           # Models do banco
│   ├── admin.py            # Configuração do admin
│   ├── views.py            # Views personalizadas
│   └── urls.py             # URLs da app
├── templates/              # Templates HTML
├── static/                 # Arquivos estáticos
└── manage.py              # Script de gerenciamento
```

### Comandos Úteis
```bash
# Criar migrações
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser

# Shell Django
python manage.py shell

# Coletar arquivos estáticos
python manage.py collectstatic
```

## 📞 Suporte

Para suporte ou dúvidas sobre o Django Admin, consulte a documentação do Django ou entre em contato com a equipe de desenvolvimento.
