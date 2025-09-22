#!/usr/bin/env python3
"""
Script de teste para verificar a configuração do Stripe
"""

import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def test_stripe_config():
    """Testa se o Stripe está configurado corretamente"""
    
    print("🧪 Testando configuração do Stripe...")
    print("=" * 50)
    
    # Verificar variáveis de ambiente
    publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
    secret_key = os.getenv('STRIPE_SECRET_KEY')
    
    if not publishable_key:
        print("❌ STRIPE_PUBLISHABLE_KEY não encontrada no .env")
        return False
    
    if not secret_key:
        print("❌ STRIPE_SECRET_KEY não encontrada no .env")
        return False
    
    print(f"✅ STRIPE_PUBLISHABLE_KEY: {publishable_key[:7]}...{publishable_key[-4:]}")
    print(f"✅ STRIPE_SECRET_KEY: {secret_key[:7]}...{secret_key[-4:]}")
    
    # Testar importação do Stripe
    try:
        import stripe
        print(f"✅ Stripe SDK importado com sucesso (versão: {stripe.__version__})")
    except ImportError:
        print("❌ Stripe SDK não instalado. Execute: pip install stripe>=7.8.0")
        return False
    
    # Testar conexão com Stripe
    try:
        stripe.api_key = secret_key
        
        # Fazer uma chamada simples para testar a chave
        account = stripe.Account.retrieve()
        print(f"✅ Conexão com Stripe funcionando!")
        print(f"   - Conta: {account.display_name or 'Sem nome'}")
        print(f"   - País: {account.country}")
        print(f"   - Moeda padrão: {account.default_currency.upper()}")
        
    except stripe.error.AuthenticationError:
        print("❌ Chave secreta inválida")
        return False
    except stripe.error.StripeError as e:
        print(f"❌ Erro do Stripe: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False
    
    # Testar criação de uma sessão de checkout (modo teste)
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': 'Teste - Guardião Premium',
                    },
                    'unit_amount': 990,  # R$ 9,90
                    'recurring': {
                        'interval': 'month'
                    }
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel',
        )
        
        print(f"✅ Sessão de checkout criada com sucesso!")
        print(f"   - ID: {checkout_session.id}")
        print(f"   - URL: {checkout_session.url}")
        
    except Exception as e:
        print(f"❌ Erro ao criar sessão de checkout: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 TODOS OS TESTES PASSARAM!")
    print("\n📝 Próximos passos:")
    print("1. Configure o webhook no Stripe Dashboard")
    print("2. Teste os pagamentos na página /premium")
    print("3. Use cartão de teste: 4242 4242 4242 4242")
    
    return True

if __name__ == "__main__":
    success = test_stripe_config()
    sys.exit(0 if success else 1)
