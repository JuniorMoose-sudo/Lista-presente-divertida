import os
import mercadopago
from config import Config

class MercadoPagoService:
    def __init__(self):
        """Inicializa o SDK do Mercado Pago"""
        access_token = Config.MERCADOPAGO_ACCESS_TOKEN
        if not access_token:
            raise ValueError("⚠️ MERCADOPAGO_ACCESS_TOKEN não configurado corretamente.")
        self.sdk = mercadopago.SDK(access_token)

    def criar_preferencia_pagamento(self, contribuicao, presente, base_url):
        """Cria uma preferência de pagamento no Mercado Pago"""
        try:
            valor_formatado = f"{float(contribuicao.valor):.2f}"
            nome_comprador = contribuicao.nome_contribuinte

            print(f"🎯 Criando preferência PRODUÇÃO para R$ {valor_formatado} - {nome_comprador}")

            # Corrige a base_url automaticamente se estiver incorreta
            if os.environ.get("RENDER") or not base_url.startswith("https://"):
                base_url = Config.SITE_URL.strip("/")

            print(f"🌐 [DEBUG] Base URL usada: {base_url}")

            back_urls = {
                "success": f"{base_url}/obrigado?contribuicao_id={contribuicao.id}",
                "failure": f"{base_url}/erro?contribuicao_id={contribuicao.id}",
                "pending": f"{base_url}/pendente?contribuicao_id={contribuicao.id}"
            }

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
                    "name": contribuicao.nome_contribuinte,
                    "email": contribuicao.email_contribuinte
                },
                "back_urls": back_urls,
                "auto_return": "approved",
                "notification_url": f"{base_url}/webhook/mercadopago",
                "metadata": {
                    "contribuicao_id": contribuicao.id,
                    "presente_id": presente.id
                }
            }

            preference_response = self.sdk.preference().create(preference_data)
            response = preference_response.get("response", {})

            print(f"🎯 Response Mercado Pago: {response}")

            if "init_point" not in response:
                print(f"❌ Erro Mercado Pago: {response.get('message', 'Erro desconhecido')}")
                return None

            print(f"✅ Link de pagamento gerado: {response['init_point']}")
            return response

        except Exception as e:
            print(f"❌ Erro ao gerar preferência de pagamento: {e}")
            import traceback
            traceback.print_exc()
            return None

    def processar_webhook(self, data):
        """Processa os webhooks enviados pelo Mercado Pago"""
        try:
            print(f"📩 Webhook recebido: {data}")
            event_type = data.get("type")
            if event_type != "payment":
                print("⚠️ Webhook ignorado: não é do tipo 'payment'")
                return None

            payment_id = data.get("data", {}).get("id")
            if not payment_id:
                print("❌ Webhook sem ID de pagamento")
                return None

            payment_info = self.sdk.payment().get(payment_id)
            payment = payment_info.get("response", {})
            print(f"💳 Pagamento consultado: {payment}")

            metadata = payment.get("metadata", {})
            contribuicao_id = metadata.get("contribuicao_id")

            return {
                "contribuicao_id": contribuicao_id,
                "status": payment.get("status")
            }

        except Exception as e:
            print(f"💥 Erro ao processar webhook: {e}")
            import traceback
            traceback.print_exc()
            return None

    def testar_credenciais(self):
        """Cria uma preferência de teste para validar o token"""
        try:
            preference_data = {
                "items": [
                    {"title": "Teste de credenciais", "quantity": 1, "currency_id": "BRL", "unit_price": 1.00}
                ],
                "back_urls": {
                    "success": f"{Config.SITE_URL}/teste-sucesso",
                    "failure": f"{Config.SITE_URL}/teste-falha",
                    "pending": f"{Config.SITE_URL}/teste-pendente"
                },
                "auto_return": "approved"
            }

            response = self.sdk.preference().create(preference_data)
            print(f"🧩 Teste de credenciais Mercado Pago -> {response}")
            return response

        except Exception as e:
            print(f"❌ Erro ao testar credenciais do Mercado Pago: {e}")
            return None
