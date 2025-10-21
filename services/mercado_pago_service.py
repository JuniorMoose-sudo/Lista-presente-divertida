import mercadopago
from config import Config

class MercadoPagoService:
    def __init__(self):
        self.sdk = mercadopago.SDK(Config.MERCADOPAGO_ACCESS_TOKEN)
    
    def criar_preferencia_pagamento(self, contribuicao, presente, base_url):
        """Cria uma preferência de pagamento no Mercado Pago (modo sandbox incluído)."""
        
        # URLs para sandbox (teste)
        success_url = f"{base_url}/obrigado?contribuicao_id={contribuicao.id}"
        failure_url = f"{base_url}/erro?contribuicao_id={contribuicao.id}"
        pending_url = f"{base_url}/pendente?contribuicao_id={contribuicao.id}"
        
        print(f"🔗 URLs configuradas (SANDBOX):")
        print(f"   Success: {success_url}")
        print(f"   Failure: {failure_url}")
        print(f"   Pending: {pending_url}")
        
        preference_data = {
            "items": [
                {
                    "title": f"Presente: {presente.nome}",
                    "description": f"Contribuição para {presente.descricao}",
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
                "success": success_url,
                "failure": failure_url,
                "pending": pending_url
            },
            # 🔥 REMOVIDO auto_return — não funciona bem em sandbox
            "notification_url": (
                f"{base_url}/webhook/mercadopago"
                if not base_url.startswith("http://127.0.0.1")
                else "https://example.com/webhook/mercadopago"
                ),
            "external_reference": str(contribuicao.id),
            "statement_descriptor": "PresenteCasamento"
        }
        
        try:
            print(f"🎯 Enviando para Mercado Pago (SANDBOX)...")
            
            preference_response = self.sdk.preference().create(preference_data)
            
            print(f"📦 Resposta COMPLETA do Mercado Pago: {preference_response}")
            
            if not preference_response or "response" not in preference_response:
                print("❌ Resposta inválida do Mercado Pago")
                return None
                
            response_data = preference_response["response"]
            print(f"🔍 Response data: {response_data}")
            
            # Verifica se houve erro
            if "status" in response_data and response_data["status"] >= 400:
                print(f"❌ Erro do Mercado Pago: {response_data.get('message', 'Erro desconhecido')}")
                return None
            
            # 🔥 Usa sandbox_init_point em ambiente de teste
            if "sandbox_init_point" in response_data:
                print("✅ Usando sandbox_init_point (modo teste)")
                response_data["init_point"] = response_data["sandbox_init_point"]
                return response_data
            elif "init_point" in response_data:
                print("✅ Usando init_point (modo produção)")
                return response_data
            else:
                print(f"❌ Nenhum init_point encontrado. Campos disponíveis: {list(response_data.keys())}")
                return None
                
        except Exception as e:
            print(f"💥 Erro ao criar preferência: {e}")
            import traceback
            traceback.print_exc()
            return None
