# 📚 Documentação Técnica - Sistema Guardião BETA

## 🏗️ Arquitetura do Sistema

### Visão Geral
O Sistema Guardião BETA é uma aplicação híbrida que combina um bot Discord com uma aplicação web Flask, integrados através de um banco de dados PostgreSQL compartilhado.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Bot Discord   │    │  Aplicação Web  │    │  Banco de Dados │
│   (py-cord)     │◄──►│     (Flask)     │◄──►│  (PostgreSQL)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Componentes Principais

1. **Bot Discord** (`main.py`)
   - Interface principal com usuários
   - Comandos slash e modais
   - Sistema de moderação

2. **Aplicação Web** (`web/`)
   - Painel administrativo
   - OAuth2 Discord
   - Dashboard e estatísticas

3. **Banco de Dados** (`database/`)
   - Armazenamento persistente
   - Pool de conexões assíncrono
   - Migrações automáticas

## 🗄️ Schema do Banco de Dados

### Tabela `usuarios`
```sql
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    id_discord BIGINT UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    nome_completo VARCHAR(200) NOT NULL,
    idade INTEGER NOT NULL CHECK (idade >= 13 AND idade <= 100),
    email VARCHAR(255) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    categoria VARCHAR(50) DEFAULT 'Usuário',
    experiencia INTEGER DEFAULT 0,
    pontos INTEGER DEFAULT 0,
    em_servico BOOLEAN DEFAULT FALSE,
    data_criacao_registro TIMESTAMP DEFAULT NOW(),
    ultimo_turno_inicio TIMESTAMP,
    cooldown_dispensa TIMESTAMP,
    cooldown_inativo TIMESTAMP
);
```

### Tabela `denuncias`
```sql
CREATE TABLE denuncias (
    id SERIAL PRIMARY KEY,
    hash_denuncia VARCHAR(16) UNIQUE NOT NULL,
    id_servidor BIGINT NOT NULL,
    id_canal BIGINT NOT NULL,
    id_denunciante BIGINT NOT NULL,
    id_denunciado BIGINT NOT NULL,
    motivo TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'Pendente',
    resultado_final VARCHAR(20),
    e_premium BOOLEAN DEFAULT FALSE,
    data_criacao TIMESTAMP DEFAULT NOW()
);
```

### Tabela `mensagens_capturadas`
```sql
CREATE TABLE mensagens_capturadas (
    id SERIAL PRIMARY KEY,
    id_denuncia INTEGER REFERENCES denuncias(id) ON DELETE CASCADE,
    id_autor BIGINT NOT NULL,
    conteudo TEXT NOT NULL,
    anexos_urls TEXT,
    timestamp_mensagem TIMESTAMP NOT NULL
);
```

### Tabela `votos_guardioes`
```sql
CREATE TABLE votos_guardioes (
    id SERIAL PRIMARY KEY,
    id_denuncia INTEGER REFERENCES denuncias(id) ON DELETE CASCADE,
    id_guardiao BIGINT NOT NULL,
    voto VARCHAR(20) NOT NULL,
    data_voto TIMESTAMP DEFAULT NOW()
);
```

### Tabela `servidores_premium`
```sql
CREATE TABLE servidores_premium (
    id SERIAL PRIMARY KEY,
    id_servidor BIGINT UNIQUE NOT NULL,
    data_inicio TIMESTAMP DEFAULT NOW(),
    data_fim TIMESTAMP NOT NULL,
    plano VARCHAR(20) DEFAULT 'Premium'
);
```

### Tabela `configuracoes_servidor`
```sql
CREATE TABLE configuracoes_servidor (
    id SERIAL PRIMARY KEY,
    id_servidor BIGINT UNIQUE NOT NULL,
    canal_log BIGINT,
    duracao_intimidou INTEGER DEFAULT 1,
    duracao_grave INTEGER DEFAULT 12,
    duracao_grave_4plus INTEGER DEFAULT 24
);
```

## 🔄 Fluxo de Moderação

### 1. Criação de Denúncia
```
Usuário → /report → Bot captura mensagens → Salva no banco
```

### 2. Distribuição
```
Background Task → Busca denúncias pendentes → Envia para Guardiões
```

### 3. Votação
```
Guardião recebe → Analisa → Vota (OK!/Intimidou/Grave)
```

### 4. Aplicação de Punição
```
5 votos coletados → Determina resultado → Aplica punição → Notifica
```

### 5. Sistema de Apelação
```
Usuário punido → Clica "Apelar" → Denúncia volta para análise
```

## 🎯 Sistema de Experiência

### Cálculo de XP
```python
def calculate_experience_reward(vote_type: str, is_correct: bool = True) -> int:
    base_rewards = {
        "OK!": 10,
        "Intimidou": 15, 
        "Grave": 20
    }
    
    if is_correct:
        return base_rewards.get(vote_type, 5)
    else:
        return base_rewards.get(vote_type, 5) // 2
```

### Progressão de Ranks
- **51 ranks** únicos
- **XP total**: 0 a 250,000+
- **Emojis únicos** para cada rank
- **Progresso visual** com porcentagem

## 🔐 Sistema de Autenticação

### OAuth2 Discord Flow
1. **Redirect**: Usuário clica em "Login com Discord"
2. **Authorization**: Discord autoriza aplicação
3. **Callback**: Discord retorna código de autorização
4. **Token Exchange**: Aplicação troca código por token
5. **User Info**: Busca informações do usuário
6. **Session**: Cria sessão local

### Scopes Necessários
- `identify`: Informações básicas do usuário
- `guilds`: Lista de servidores do usuário

### Permissões do Bot
```python
BOT_PERMISSIONS = [
    "manage_messages",    # Gerenciar mensagens
    "moderate_members",   # Moderar membros (timeout)
    "ban_members",        # Banir membros
    "view_channel",       # Ver canais
    "send_messages",      # Enviar mensagens
    "embed_links",        # Enviar embeds
    "attach_files",       # Anexar arquivos
    "read_message_history" # Ler histórico
]
```

## 🎨 Interface Web

### Tecnologias Frontend
- **Bootstrap 5**: Framework CSS responsivo
- **Chart.js**: Gráficos interativos
- **JavaScript ES6+**: Funcionalidades dinâmicas
- **CSS Custom Properties**: Sistema de design consistente

### Estrutura de Templates
```
templates/
├── base.html          # Template base
├── index.html         # Página inicial
├── dashboard.html     # Dashboard do usuário
├── server_panel.html  # Painel de servidor
├── premium.html       # Página premium
└── servers.html       # Lista de servidores
```

### Sistema de Componentes
- **Cards**: Informações organizadas
- **Modals**: Janelas de confirmação
- **Alerts**: Mensagens de feedback
- **Charts**: Visualização de dados

## 🔧 Background Tasks

### Task de Distribuição
```python
@tasks.loop(seconds=10)
async def distribution_loop(self):
    # Busca denúncias pendentes
    # Distribui para Guardiões disponíveis
    # Atualiza status para "Em Análise"
```

### Task de Pontos
```python
@tasks.loop(hours=1)
async def points_loop(self):
    # Adiciona pontos para Guardiões em serviço
    # Calcula baseado no tempo de serviço
```

### Task de Inatividade
```python
@tasks.loop(minutes=5)
async def inactivity_check(self):
    # Verifica Guardiões inativos
    # Aplica penalidades
```

## 🚀 Deploy e Configuração

### Variáveis de Ambiente Obrigatórias
```env
# Discord
DISCORD_CLIENT_ID=123456789
DISCORD_CLIENT_SECRET=abcdef123456
DISCORD_TOKEN=Bot token here

# Database
POSTGRES_DB=guardiaobeta
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Web
WEB_PORT=8080
FLASK_SECRET_KEY=secret-key-here
```

### Configuração Discloud
```
NAME=GuardiaoBETA
MAIN=main.py
TYPE=bot
RAM=512
VERSION=latest
APT=tools
START=python main.py
```

## 📊 Monitoramento e Logs

### Níveis de Log
- **INFO**: Operações normais
- **WARNING**: Situações anômalas
- **ERROR**: Erros recuperáveis
- **CRITICAL**: Erros fatais

### Métricas Importantes
- **Uptime**: Tempo de funcionamento
- **Guilds**: Número de servidores
- **Users**: Usuários únicos
- **Reports**: Denúncias processadas
- **Punishments**: Punições aplicadas

## 🔒 Segurança

### Medidas Implementadas
- **Validação de entrada**: Todos os inputs são validados
- **Sanitização**: Dados são sanitizados antes do banco
- **Rate limiting**: Cooldowns em comandos
- **Criptografia**: Senhas e tokens protegidos
- **CSRF Protection**: Tokens CSRF em formulários

### Anonimização
- **Hash único**: Denúncias identificadas por hash
- **Dados anônimos**: Mensagens são anonimizadas
- **Identidades protegidas**: Guardiões permanecem anônimos

## 🧪 Testes

### Testes Automatizados
```python
async def run_tests():
    # Testa conexão com banco
    await db_manager.initialize_pool()
    
    # Testa sistema de experiência
    test_experience_system()
    
    # Testa configurações
    assert DISCORD_TOKEN
    assert DISCORD_CLIENT_ID
```

### Execução
```bash
python main.py --test
```

## 📈 Performance

### Otimizações
- **Pool de conexões**: Conexões reutilizadas
- **Queries otimizadas**: Índices apropriados
- **Cache de sessão**: Dados de usuário em cache
- **Lazy loading**: Carregamento sob demanda

### Limites
- **Denúncias simultâneas**: Máximo por servidor
- **Guardiões por denúncia**: Máximo 5
- **Rate limits**: Cooldowns configuráveis
- **Memory usage**: Monitoramento de RAM

## 🔄 Manutenção

### Backup do Banco
```bash
pg_dump guardiaobeta > backup_$(date +%Y%m%d).sql
```

### Limpeza de Dados
```sql
-- Remove denúncias antigas (mais de 30 dias)
DELETE FROM denuncias WHERE data_criacao < NOW() - INTERVAL '30 days';

-- Remove votos órfãos
DELETE FROM votos_guardioes WHERE id_denuncia NOT IN (SELECT id FROM denuncias);
```

### Atualizações
1. Backup do banco
2. Teste em ambiente de desenvolvimento
3. Deploy gradual
4. Monitoramento pós-deploy

## 📞 Suporte Técnico

### Logs Importantes
- **guardiaobeta.log**: Log principal
- **Database logs**: Logs do PostgreSQL
- **Web server logs**: Logs do Flask

### Troubleshooting
1. Verificar logs de erro
2. Testar conectividade com banco
3. Verificar permissões do bot
4. Validar configurações OAuth2

---

**Documentação Técnica v1.0** - Sistema Guardião BETA 🛡️
