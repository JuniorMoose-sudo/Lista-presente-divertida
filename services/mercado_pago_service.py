import mercadopago
from config import Config
import os


class MercadoPagoService:
    def __init__(self):
        """Inicializa o SDK do Mercado Pago com o Access Token de produção."""
        access_token = Config.MERCADOPAGO_ACCESS_TOKEN
        if not access_token:
            raise ValueError("❌ MERCADOPAGO_ACCESS_TOKEN não configurado no ambiente.")
        
        self.sdk = mercadopago.SDK(access_token)

    # ============================================================
    # 💳 CRIAÇÃO DE PREFERÊNCIA DE PAGAMENTO
    # ============================================================
    def criar_preferencia_pagamento(self, contribuicao, presente, base_url):
        """Cria preferência de pagamento PARA PRODUÇÃO"""

        # ✅ Em produção (Render), força a URL real do site
        if os.environ.get('RENDER') or not base_url.startswith("https://"):
            base_url = Config.SITE_URL.strip("/")

        preference_data = {
            "items": [
                {
                    "id": str(presente.id),
                    "title": f"Presente: {presente.nome}",
                    "description": f"Contribuição para {presente.descricao or 'presente do casamento'}",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": float(contribuicao.valor)
                }
            ],
            "payer": {
                "name": contribuicao.nome_contribuinte,
                "email": contribuicao.email_contribuinte
            },
            "back_urls": {
                "success": f"{base_url}/obrigado",
                "failure": f"{base_url}/erro",
                "pending": f"{base_url}/pendente"
            },
            "auto_return": "approved",  # ✅ Retorna automaticamente após o pagamento
            "notification_url": f"{base_url}/webhook/mercadopago",  # ✅ Webhook
            "external_reference": str(contribuicao.id),
            "statement_descriptor": "PresenteCasamento",
            "binary_mode": True,  # ✅ Evita pagamentos pendentes
            "expires": False
        }

        try:
            print(f"🎯 Criando preferência PRODUÇÃO para R$ {contribuicao.valor} - {contribuicao.nome_contribuinte}")

            preference_response = self.sdk.preference().create(preference_data)

            if not preference_response or "response" not in preference_response:
                print("❌ Resposta inválida do Mercado Pago")
                return None

            response_data = preference_response["response"]

            # Log detalhado (somente fora do Render)
            if not os.environ.get('RENDER'):
                print("📦 Resposta completa do Mercado Pago:")
                print(response_data)

            # Verifica erros HTTP comuns
            if response_data.get("status") in [400, 401, 403, 404]:
                error_msg = response_data.get("message", "Erro desconhecido")
                print(f"❌ Erro Mercado Pago: {error_msg}")
                return None

            # Retorna link de pagamento
            if "init_point" in response_data:
                print("✅ Link de pagamento gerado com sucesso")
                print(f"🔗 URL: {response_data['init_point']}")
                return response_data
            else:
                print(f"❌ init_point não encontrado. Campos retornados: {list(response_data.keys())}")
                return None

        except Exception as e:
            print(f"💥 Erro ao criar preferência de pagamento: {e}")
            return None

    # ============================================================
    # 📬 PROCESSAMENTO DE WEBHOOK
    # ============================================================
    def processar_webhook(self, data):
        """Processa webhook do Mercado Pago"""
        try:
            if data.get("type") == "payment":
                payment_id = data.get("data", {}).get("id")

                if not payment_id:
                    print("⚠️ Webhook recebido sem payment_id.")
                    return None

                payment_info = self.sdk.payment().get(payment_id)

                if payment_info and "response" in payment_info:
                    payment = payment_info["response"]

                    print(f"📬 Pagamento recebido via webhook: {payment_id} - Status: {payment.get('status')}")
                    return {
                        "contribuicao_id": payment.get("external_reference"),
                        "payment_id": payment_id,
                        "status": payment.get("status"),
                        "status_detail": payment.get("status_detail")
                    }

            print("⚠️ Webhook ignorado (não é tipo 'payment').")
            return None

        except Exception as e:
            print(f"💥 Erro ao processar webhook: {e}")
            return None

    # ============================================================
    # 🔎 VERIFICAÇÃO DE PAGAMENTO
    # ============================================================
    def verificar_pagamento(self, payment_id):
        """Verifica o status de um pagamento específico"""
        try:
            payment_info = self.sdk.payment().get(payment_id)

            if payment_info and "response" in payment_info:
                print(f"🔍 Verificação de pagamento {payment_id} obtida com sucesso.")
                return payment_info["response"]

            print(f"⚠️ Pagamento {payment_id} não encontrado.")
            return None

        except Exception as e:
            print(f"💥 Erro ao verificar pagamento: {e}")
            return None
