# check_production.py
import os
import mercadopago
from config import Config

def verificar_configuracao_mp():
    print("🔍 Verificando configuração Mercado Pago...")
    
    # Verifica se as variáveis estão configuradas
    access_token = Config.MERCADOPAGO_ACCESS_TOKEN
    
    if not access_token:
        print("❌ MERCADOPAGO_ACCESS_TOKEN não configurado")
        print("   Configure a variável de ambiente MERCADOPAGO_ACCESS_TOKEN")
        return False
    
    # Verifica se é token de produção
    if access_token.startswith('TEST-'):
        print("❌⚠️  ATENÇÃO: Usando token de TESTE em produção!")
        print("   Obtenha credenciais de produção em: https://www.mercadopago.com.br/developers/panel/credentials")
        return False
    
    if not access_token.startswith('APP_USR-'):
        print("❌ Token não parece ser de produção (deve começar com 'APP_USR-')")
        return False
    
    print("✅ Token de produção configurado:", access_token[:20] + "...")
    
    # Testa a conexão
    try:
        sdk = mercadopago.SDK(access_token)
        test_data = {
            "items": [{
                "title": "Teste Conexão Produção",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": 10.0
            }]
        }
        
        result = sdk.preference().create(test_data)
        
        if result and "response" in result:
            response_data = result["response"]
            if "init_point" in response_data:
                print("✅ Conexão com Mercado Pago PRODUÇÃO - OK")
                return True
            else:
                print("❌ Resposta inválida do Mercado Pago")
                if "message" in response_data:
                    print(f"   Erro: {response_data['message']}")
                return False
        else:
            print("❌ Falha na comunicação com Mercado Pago")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar Mercado Pago: {e}")
        return False

def verificar_database():
    print("🔍 Verificando configuração do banco...")
    
    database_url = Config.SQLALCHEMY_DATABASE_URI
    
    if not database_url:
        print("❌ DATABASE_URL não configurado")
        return False
    
    if 'postgresql' in database_url:
        print("✅ Banco PostgreSQL configurado")
        return True
    elif 'sqlite' in database_url:
        print("⚠️  Usando SQLite (apenas desenvolvimento)")
        return True
    else:
        print("❌ Configuração de banco desconhecida")
        return False

def verificar_secret_key():
    print("🔍 Verificando chave secreta...")
    
    secret_key = Config.SECRET_KEY
    
    if not secret_key or secret_key == 'chave-secreta-padrao-mudar-em-producao':
        print("❌ SECRET_KEY não configurada ou é a padrão")
        print("   Gere uma chave com: python -c 'import secrets; print(secrets.token_hex(32))'")
        return False
    
    if len(secret_key) < 32:
        print("❌ SECRET_KEY muito curta (mínimo 32 caracteres)")
        return False
    
    print("✅ SECRET_KEY configurada corretamente")
    return True

def verificar_urls():
    print("🔍 Verificando URLs...")
    
    # Verifica se está no Render
    if os.environ.get('RENDER'):
        site_url = os.environ.get('SITE_URL', '')
        if not site_url:
            print("⚠️  SITE_URL não configurada no Render")
            return False
        print(f"✅ SITE_URL: {site_url}")
        return True
    else:
        print("✅ Ambiente de desenvolvimento")
        return True

def verificar_ambiente():
    print("🔍 Verificando ambiente...")
    
    if os.environ.get('RENDER'):
        print("✅ Ambiente: Render (Produção)")
        return True
    else:
        print("✅ Ambiente: Desenvolvimento Local")
        return True

if __name__ == '__main__':
    print("🚀 VERIFICAÇÃO DE CONFIGURAÇÃO")
    print("=" * 50)
    
    ambiente_ok = verificar_ambiente()
    secret_ok = verificar_secret_key()
    db_ok = verificar_database()
    mp_ok = verificar_configuracao_mp()
    urls_ok = verificar_urls()
    
    print("=" * 50)
    
    todas_verificacoes = all([secret_ok, db_ok, mp_ok, urls_ok])
    
    if todas_verificacoes:
        print("🎉 TUDO CONFIGURADO CORRETAMENTE!")
        if os.environ.get('RENDER'):
            print("✅ Pronto para produção no Render!")
        else:
            print("✅ Pronto para desenvolvimento local!")
    else:
        print("❌ CORRIJA AS CONFIGURAÇÕES ACIMA")
        print("\n📋 PRÓXIMOS PASSOS:")
        
        if not mp_ok:
            print("1. Obtenha credenciais de PRODUÇÃO do Mercado Pago")
            print("   👉 https://www.mercadopago.com.br/developers/panel/credentials")
        
        if not secret_ok:
            print("2. Gere uma SECRET_KEY segura:")
            print("   python -c 'import secrets; print(secrets.token_hex(32))'")
        
        if not db_ok:
            print("3. Configure o DATABASE_URL do Neon")