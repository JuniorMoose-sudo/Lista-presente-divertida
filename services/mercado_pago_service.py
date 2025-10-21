import os
import mercadopago
from config import Config

# Inicializa SDK com o access token do Mercado Pago
sdk = mercadopago.SDK(Config.MERCADOPAGO_ACCESS_TOKEN)

def criar_preferencia_pagamento(presente, contribuicao, base_url):
    """
    Cria uma preferência de pagamento no Mercado Pago
    para o presente e contribuição informados.
    """

    try:
        valor_formatado = f"{float(contribuicao.valor):.2f}"
        nome_comprador = contribuicao.nome

        print(f"🎯 Criando preferência PRODUÇÃO para R$ {valor_formatado} - {nome_comprador}")

        # 🧠 Corrige a base_url automaticamente se estiver incorreta
        if os.environ.get("RENDER") or not base_url.startswith("https://"):
            base_url = Config.SITE_URL.strip("/")

        print(f"🌐 [DEBUG] Base URL recebida: {base_url}")

        # URLs de retorno após o pagamento
        back_urls = {
            "success": f"{base_url}/obrigado",
            "failure": f"{base_url}/erro",
            "pending": f"{base_url}/pendente"
        }

        print(f"🌐 [DEBUG] back_urls: {back_urls}")

        # Dados da preferência
        preference_data = {
            "items": [
                {
                    "title": f"Contribuição: {presente.nome}",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": float(contribuicao.valor)
                }
            ],
            "payer": {
                "name": contribuicao.nome,
                "email": contribuicao.email
            },
            "back_urls": back_urls,
            "auto_return": "approved",
            "notification_url": f"{base_url}/webhook/mercadopago",
            "metadata": {
                "contribuicao_id": contribuicao.id,
                "presente_id": presente.id
            }
        }

        # Envia requisição ao Mercado Pago
        preference_response = sdk.preference().create(preference_data)
        response = preference_response.get("response", {})

        # Log detalhado da resposta
        print(f"🎯 Preference response: {response}")

        # Verifica se foi criada com sucesso
        if "init_point" not in response:
            print(f"❌ Erro Mercado Pago: {response.get('message', 'Erro desconhecido')}")
            return None

        print(f"✅ Link de pagamento gerado com sucesso: {response['init_point']}")
        return response["init_point"]

    except Exception as e:
        print(f"❌ Erro ao gerar link de pagamento com Mercado Pago: {e}")
        return None


def testar_credenciais():
    """
    Cria uma preferência de teste para verificar se as credenciais
    e URLs estão configuradas corretamente.
    """

    try:
        preference_data = {
            "items": [
                {"title": "Teste de credenciais", "quantity": 1, "currency_id": "BRL", "unit_price": 1.00}
            ],
            "back_urls": {
                "success": f"{Config.SITE_URL}/sucesso",
                "failure": f"{Config.SITE_URL}/falha",
                "pending": f"{Config.SITE_URL}/pendente"
            },
            "auto_return": "approved"
        }

        response = sdk.preference().create(preference_data)
        print(f"🧩 Teste de credenciais Mercado Pago -> {response}")
        return response

    except Exception as e:
        print(f"❌ Erro ao testar credenciais do Mercado Pago: {e}")
        return None
