# 🛡️ Sistema Guardião BETA

Sistema de moderação comunitária inteligente e anônima para Discord, desenvolvido em Python com Flask e integração completa via OAuth2.

## 🚀 Características Principais

### 🤖 Bot Discord
- **Moderação Comunitária**: Sistema baseado em votação de Guardiões treinados
- **Comandos Slash**: Interface moderna com `/cadastro`, `/formguardiao`, `/stats`, `/report`, `/turno`
- **Sistema de Experiência**: 51 ranks de Novato até Guardião Eterno
- **Moderação Anônima**: Identidades dos Guardiões protegidas
- **Punições Automáticas**: Mute e ban baseados em votação
- **Sistema de Apelação**: Revisão de punições

### 🌐 Aplicação Web
- **OAuth2 Discord**: Login seguro com Discord
- **Dashboard Completo**: Estatísticas e gráficos em tempo real
- **Painel de Servidor**: Controle total para administradores
- **Sistema Premium**: Planos pagos com recursos exclusivos
- **Design Responsivo**: Funciona em desktop e mobile
- **Dark Mode**: Suporte automático ao modo escuro

## 📋 Tecnologias Utilizadas

### Backend
- **Python 3.10+**: Linguagem principal
- **py-cord**: Biblioteca do Discord Bot
- **Flask**: Framework web
- **PostgreSQL**: Banco de dados
- **asyncpg**: Driver assíncrono PostgreSQL
- **SQLAlchemy**: ORM para banco de dados
- **Alembic**: Migrações de schema

### Frontend
- **Bootstrap 5**: Framework CSS
- **Chart.js**: Gráficos interativos
- **JavaScript ES6+**: Funcionalidades dinâmicas
- **HTML5/CSS3**: Estrutura e estilos

### Deploy
- **Discloud**: Hospedagem do bot e web app
- **GitHub**: Controle de versão
- **Docker**: Containerização (opcional)

## 🛠️ Instalação e Configuração

### 1. Clone o Repositório
```bash
git clone https://github.com/Konnak/guardiaobeta.git
cd guardiaobeta
```

### 2. Instale as Dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto:

```env
# Discord Bot
DISCORD_CLIENT_ID=seu_client_id
DISCORD_CLIENT_SECRET=seu_client_secret
DISCORD_TOKEN=seu_bot_token

# PostgreSQL Database
POSTGRES_DB=guardiaobeta
POSTGRES_USER=seu_usuario
POSTGRES_PASSWORD=sua_senha
POSTGRES_HOST=seu_host
POSTGRES_PORT=5432

# Web Application
WEB_PORT=8080
FLASK_SECRET_KEY=sua_chave_secreta

# Bot Configuration
BOT_PREFIX=!
```

### 4. Configure o Banco de Dados
Execute o script SQL para criar as tabelas:
```bash
psql -h seu_host -U seu_usuario -d guardiaobeta -f database/init_schema.sql
```

### 5. Execute o Sistema
```bash
python main.py
```

## 📊 Estrutura do Projeto

```
guardiaobeta/
├── main.py                 # Arquivo principal
├── config.py              # Configurações
├── requirements.txt       # Dependências Python
├── discloud.config       # Configuração Discloud
├── .env                  # Variáveis de ambiente
├── .gitignore           # Arquivos ignorados pelo Git
│
├── cogs/                # Comandos do bot Discord
│   ├── cadastro.py      # Sistema de cadastro
│   ├── guardiao.py      # Sistema de Guardiões
│   ├── stats.py         # Estatísticas do usuário
│   └── moderacao.py     # Sistema de moderação
│
├── database/            # Banco de dados
│   ├── connection.py    # Conexão PostgreSQL
│   ├── models.py        # Modelos SQLAlchemy
│   └── init_schema.sql  # Schema inicial
│
├── utils/               # Utilitários
│   └── experience_system.py  # Sistema de experiência
│
└── web/                 # Aplicação web
    ├── auth.py          # OAuth2 Discord
    ├── routes.py        # Rotas Flask
    ├── templates/       # Templates HTML
    │   ├── base.html
    │   ├── index.html
    │   ├── dashboard.html
    │   ├── server_panel.html
    │   ├── premium.html
    │   └── servers.html
    └── static/          # Arquivos estáticos
        ├── css/
        ├── js/
        └── img/
```

## 🎮 Comandos do Bot

### Comandos Básicos
- `/cadastro` - Registra usuário no sistema
- `/stats` - Mostra estatísticas do usuário
- `/report <usuário> <motivo>` - Denuncia violação

### Comandos de Guardião
- `/formguardiao` - Treinamento para ser Guardião
- `/turno` - Inicia/termina turno de serviço

## 🌟 Sistema de Experiência

O sistema possui **51 ranks** únicos:

### Ranks Iniciais (0-1000 XP)
- **Novato** (0-100) 🌱
- **Aprendiz** (101-200) 📚
- **Iniciante** (201-300) 🎯
- **Recruta** (301-400) ⚔️
- **Principiante** (401-600) 🏃
- **Observador** (601-800) 👁️
- **Vigia** (801-1000) 🛡️

### Ranks Avançados (1000+ XP)
- **Aspirante** até **Guardião Eterno** (250000+ XP)

## 💰 Sistema Premium

### Plano Gratuito
- Moderação básica
- Até 5 Guardiões simultâneos
- Sistema de votação padrão

### Plano Premium (R$ 5/mês)
- Prioridade máxima na análise
- Configurações personalizadas
- Canal de log personalizado
- Estatísticas avançadas
- Suporte prioritário

### Plano Enterprise (R$ 20/mês)
- Múltiplos servidores
- API personalizada
- Suporte 24/7
- Integrações customizadas

## 🔧 Deploy na Discloud

### 1. Configure o discloud.config
```
NAME=GuardiaoBETA
MAIN=main.py
TYPE=bot
RAM=512
VERSION=latest
APT=tools
START=python main.py
```

### 2. Faça Upload
```bash
# Compacte o projeto (exceto .env e __pycache__)
zip -r guardiaobeta.zip . -x "*.env" "*__pycache__*" "*.pyc" ".git/*"

# Faça upload via painel Discloud
```

### 3. Configure o Banco
Execute o SQL no painel PostgreSQL da Discloud:
```sql
-- Execute o conteúdo de database/init_schema.sql
```

## 🧪 Testes

Execute os testes do sistema:
```bash
python main.py --test
```

## 📈 Monitoramento

### Logs
- Logs salvos em `guardiaobeta.log`
- Logs também exibidos no console

### Estatísticas
- Acesse `/api/bot/status` para status do bot
- Acesse `/api/stats` para estatísticas gerais

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🆘 Suporte

- **Discord**: Entre no servidor oficial
- **GitHub Issues**: Reporte bugs e sugestões
- **Email**: contato@guardiaobeta.com

## 🙏 Agradecimentos

- Comunidade Discord por feedback e sugestões
- Desenvolvedores das bibliotecas utilizadas
- Todos os Guardiões que testaram o sistema

---

**Sistema Guardião BETA** - Moderação comunitária inteligente para Discord 🛡️
