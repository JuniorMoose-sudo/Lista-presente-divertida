import mercadopago
from config import Config
import os

class MercadoPagoService:
    def __init__(self):
        # 🔥 USA ACCESS TOKEN DE PRODUÇÃO
        access_token = Config.MERCADOPAGO_ACCESS_TOKEN
        if not access_token:
            raise ValueError("MERCADOPAGO_ACCESS_TOKEN não configurado")
        
        self.sdk = mercadopago.SDK(access_token)
    
    def criar_preferencia_pagamento(self, contribuicao, presente, base_url):
        """Cria preferência de pagamento PARA PRODUÇÃO"""
        
        # Em produção, usa a URL real do site
        if os.environ.get('RENDER'):
            base_url = Config.SITE_URL
        
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
            "auto_return": "approved",  # ✅ Funciona em produção
            "notification_url": f"{base_url}/webhook/mercadopago",
            "external_reference": str(contribuicao.id),
            "statement_descriptor": "PresenteCasamento",
            "binary_mode": True,  # ✅ Evita pagamentos pendentes
            "expires": False
        }
        
        try:
            print(f"🎯 Criando preferência PRODUÇÃO para R$ {contribuicao.valor}")
            
            preference_response = self.sdk.preference().create(preference_data)
            
            if not preference_response or "response" not in preference_response:
                print("❌ Resposta inválida do Mercado Pago")
                return None
                
            response_data = preference_response["response"]
            
            # Log para debug (não mostrar em produção)
            if not os.environ.get('RENDER'):
                print(f"📦 Resposta MP: {response_data}")
            
            # Verifica erros
            if response_data.get("status") in [400, 401, 403, 404]:
                error_msg = response_data.get("message", "Erro desconhecido")
                print(f"❌ Erro Mercado Pago: {error_msg}")
                return None
            
            # Retorna init_point
            if "init_point" in response_data:
                print("✅ Link de pagamento gerado com sucesso")
                return response_data
            else:
                print(f"❌ init_point não encontrado. Campos: {list(response_data.keys())}")
                return None
                
        except Exception as e:
            print(f"💥 Erro ao criar preferência: {e}")
            return None
    
    def processar_webhook(self, data):
        """Processa webhook PARA PRODUÇÃO"""
        try:
            if data.get("type") == "payment":
                payment_id = data.get("data", {}).get("id")
                
                if not payment_id:
                    return None
                
                # Busca informações do pagamento
                payment_info = self.sdk.payment().get(payment_id)
                
                if payment_info and "response" in payment_info:
                    payment = payment_info["response"]
                    
                    return {
                        "contribuicao_id": payment.get("external_reference"),
                        "payment_id": payment_id,
                        "status": payment.get("status"),
                        "status_detail": payment.get("status_detail")
                    }
            
            return None
            
        except Exception as e:
            print(f"💥 Erro ao processar webhook: {e}")
            return None
    
    def verificar_pagamento(self, payment_id):
        """Verifica status de um pagamento específico"""
        try:
            payment_info = self.sdk.payment().get(payment_id)
            
            if payment_info and "response" in payment_info:
                return payment_info["response"]
            
            return None
            
        except Exception as e:
            print(f"💥 Erro ao verificar pagamento: {e}")
            return None