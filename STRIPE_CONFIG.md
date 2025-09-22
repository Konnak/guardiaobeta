# Configuração do Stripe

## ⚠️ IMPORTANTE: Configure seu arquivo .env

Crie um arquivo `.env` na raiz do projeto com as seguintes configurações:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_CLIENT_SECRET=your_client_secret_here

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=guardiao_beta
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password

# Flask Configuration
FLASK_SECRET_KEY=your_flask_secret_key_here

# Stripe Configuration (TEST KEYS) - SUBSTITUA PELAS SUAS CHAVES
STRIPE_PUBLISHABLE_KEY=pk_test_51S9yfE...sua_chave_publicavel_aqui
STRIPE_SECRET_KEY=sk_test_51S9yfE...sua_chave_secreta_aqui
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Environment
ENVIRONMENT=development
```

## 🚀 Como Testar

1. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

2. **Configure o .env** com as chaves acima

3. **Teste os pagamentos:**
   - Acesse `/premium`
   - Escolha um plano
   - Use cartão de teste: `4242 4242 4242 4242`
   - CVV: `123`
   - Data: qualquer data futura

## 📝 Cartões de Teste Stripe

- **Sucesso**: `4242 4242 4242 4242`
- **Falha**: `4000 0000 0000 0002`
- **3D Secure**: `4000 0000 0000 3220`

## 🔗 Webhook (Opcional para teste)

Para receber webhooks em desenvolvimento, use ngrok:
```bash
ngrok http 8080
# Use a URL gerada como webhook endpoint no Stripe
```

## ✅ Status

- [x] Chaves de teste configuradas
- [x] Dependências instaladas
- [x] Rotas de pagamento criadas
- [x] Página premium redesenhada
- [ ] Webhook configurado (opcional)
