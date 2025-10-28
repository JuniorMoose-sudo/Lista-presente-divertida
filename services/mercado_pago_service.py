import os
import logging
import mercadopago
import functools
import time
from config import Config

logger = logging.getLogger(__name__)

def with_retry(max_retries=3, delay=1):
    """Decorator para adicionar retry em funções"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"retry_attempt - function: {func.__name__}, attempt: {attempt + 1}/{max_retries}, error: {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            logger.error(
                f"max_retries_reached - function: {func.__name__}, error: {str(last_error)}"
            )
            raise last_error
        return wrapper
    return decorator

class MercadoPagoService:
    def __init__(self):
        """Inicializa o SDK do Mercado Pago"""
        access_token = Config.MERCADOPAGO_ACCESS_TOKEN
        if not access_token:
            raise ValueError("⚠️ MERCADOPAGO_ACCESS_TOKEN não configurado corretamente.")
        
        # Configuração com timeout e opções de segurança
        self.sdk = mercadopago.SDK(access_token)
        
        # Teste de conexão na inicialização
        try:
            self.testar_credenciais()
            logger.info("SDK do Mercado Pago inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro na inicialização do Mercado Pago: {str(e)}")
            # Não levanta exceção para permitir que a aplicação continue funcionando

    def _limpar_telefone(self, telefone):
        """Remove caracteres especiais do telefone e valida formato"""
        if not telefone:
            raise ValueError("Telefone é obrigatório")
        
        # Remove todos os caracteres não numéricos
        numeros = ''.join(filter(str.isdigit, telefone))
        
        # Valida o tamanho (considerando números BR: 11/10 dígitos com DDD)
        if len(numeros) not in [10, 11]:
            raise ValueError(
                "Telefone inválido. Formato esperado: (XX) XXXX-XXXX ou (XX) 9XXXX-XXXX"
            )
        
        return numeros

    def _validar_cpf(self, cpf):
        """Valida e limpa o CPF"""
        if not cpf:
            raise ValueError("CPF é obrigatório")

        # Remove caracteres especiais
        numeros = ''.join(filter(str.isdigit, cpf))
        
        # Valida tamanho
        if len(numeros) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
            
        # Verifica se todos os dígitos são iguais
        if len(set(numeros)) == 1:
            raise ValueError("CPF inválido")
            
        # Valida dígitos verificadores
        for i in range(9, 11):
            valor = sum((int(numeros[j]) * ((i + 1) - j) for j in range(0, i)))
            digito = ((valor * 10) % 11) % 10
            if int(numeros[i]) != digito:
                raise ValueError("CPF inválido")
                
        return numeros
    
    @with_retry(max_retries=3, delay=1)
    def criar_preferencia_pagamento(self, contribuicao, presente, base_url):
        """Cria uma preferência de pagamento no Mercado Pago"""
        try:
            # Validações de segurança adicionais
            if contribuicao.status != 'pendente':
                logger.error(f"Status de contribuição inválido: contribuicao_id={contribuicao.id} status={contribuicao.status}")
                raise ValueError("Contribuição em estado inválido")

            # Verifica novamente o presente
            if presente.esta_completo:
                logger.error(f"Presente já completamente pago: presente_id={presente.id}")
                raise ValueError("Presente já completamente pago")

            # Verifica valor novamente
            valor_atual = float(contribuicao.valor)
            if valor_atual <= 0 or valor_atual > 10000:
                logger.error(f"Valor inválido para pagamento: valor={valor_atual}")
                raise ValueError("Valor inválido para pagamento")

            valor_formatado = f"{valor_atual:.2f}"
            nome_comprador = contribuicao.nome_contribuinte

            # Valida e limpa CPF e telefone
            try:
                # Normaliza/limpa CPF antes de validar (remove pontos e traços)
                cpf_raw = contribuicao.cpf_contribuinte or ''
                cpf_raw = str(cpf_raw).replace('.', '').replace('-', '').strip()
                cpf_limpo = self._validar_cpf(cpf_raw)
                telefone_limpo = self._limpar_telefone(contribuicao.telefone_contribuinte)
            except ValueError as e:
                logger.error(f"Erro de validação: {str(e)} | contribuicao_id={contribuicao.id}")
                raise ValueError(f"Dados inválidos: {str(e)}")

            print(f"🎯 Criando preferência PRODUÇÃO para R$ {valor_formatado} - {nome_comprador}")

            # Corrige a base_url automaticamente se estiver incorreta
            if not base_url.startswith("https://"):
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
                        # Campos recomendados pelo Mercado Pago para melhorar índice de aprovação
                        # - id: código interno do item (aqui usamos o ID do presente)
                        # - category_id: categoria do item (ajuste conforme necessário)
                        # - description: descrição detalhada do item
                        "id": str(presente.id),
                        "title": f"Contribuição: {presente.nome}",
                        "description": presente.descricao or "Contribuição para presente",
                        "category_id": "wedding_gift",
                        "quantity": 1,
                        "currency_id": "BRL",
                        "unit_price": float(contribuicao.valor)
                    }
                ],
                # External reference permite correlacionar preferência/payment_id com o ID interno
                "external_reference": str(contribuicao.id),
                "payer": {
                    "name": contribuicao.nome_contribuinte,
                    "email": contribuicao.email_contribuinte,
                    # ✅ DADOS REAIS DA PRODUÇÃO (já validados)
                    "identification": {
                        "type": "CPF",
                        "number": cpf_limpo
                    },
                    "phone": {
                        "area_code": telefone_limpo[:2],
                        "number": telefone_limpo[2:]
                    }
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

            # Prefer init_point, mas aceita sandbox_init_point como fallback para debugging/local
            init_point = response.get('init_point') or response.get('sandbox_init_point')

            if not init_point:
                msg = response.get('message') or response
                print(f"❌ Erro Mercado Pago: {msg}")
                logger.error(f"Erro: preferência sem init_point: {response}")
                return None

            # Normalize response to always include init_point key
            response['init_point'] = init_point

            print(f"✅ Link de pagamento gerado: {init_point}")
            return {
                'id': response.get('id'),
                'init_point': init_point,
                'raw': response
            }

        except Exception as e:
            print(f"❌ Erro ao gerar preferência de pagamento: {e}")
            import traceback
            traceback.print_exc()
            return None

    @with_retry(max_retries=3, delay=1)
    def processar_webhook(self, data):
        """Processa os webhooks enviados pelo Mercado Pago (payment e merchant_order)"""
        try:
            print(f"📩 Webhook recebido: {data}")

            # Compatibilidade com o novo formato (a partir de 2023)
            event_type = data.get("type") or data.get("topic")
            action = data.get("action")
            resource_id = None

            # Extrai ID corretamente, independentemente do formato
            if "data" in data and isinstance(data["data"], dict):
                resource_id = data["data"].get("id") or data.get("id")
            else:
                resource_id = data.get("id") or data.get("resource")

            if not resource_id:
                print("❌ Webhook sem ID de recurso")
                return None

            # --- Determina o tipo de evento ---
            if "payment" in (event_type or "") or "payment" in (action or ""):
                print(f"💳 Recebido webhook de pagamento: {resource_id}")
                payment_info = self.sdk.payment().get(resource_id)
                payment = payment_info.get("response", {})
                print(f"💳 Pagamento consultado: {payment}")

                metadata = payment.get("metadata", {})
                contribuicao_id = metadata.get("contribuicao_id")

                return {
                    "contribuicao_id": contribuicao_id,
                    "status": payment.get("status")
                }

            elif "merchant_order" in (event_type or "") or "merchant_order" in (action or ""):
                print(f"📦 Recebido webhook de merchant_order: {resource_id}")
                order_info = self.sdk.merchant_order().get(resource_id)
                order = order_info.get("response", {})
                print(f"📦 Merchant Order consultada: {order}")

                payments = order.get("payments", [])
                if not payments:
                    print("⚠ Nenhum pagamento encontrado na ordem")
                    return None

                # Escolhe o melhor pagamento
                preferred_payment = next((p for p in payments if p.get('status') == 'approved'), None)
                if not preferred_payment:
                    preferred_payment = next((p for p in payments if p.get('status') in ('in_process', 'pending')), None)
                if not preferred_payment:
                    preferred_payment = payments[-1]

                payment_id = preferred_payment.get('id')
                payment_info = self.sdk.payment().get(payment_id)
                payment = payment_info.get("response", {})
                metadata = payment.get("metadata", {})

                return {
                    "contribuicao_id": metadata.get("contribuicao_id"),
                    "status": payment.get("status")
                }

            else:
                print(f"⚠ Tipo de evento desconhecido: {event_type} / {action}")
                return None

        except Exception as e:
            print(f"💥 Erro ao processar webhook: {e}")
            import traceback
            traceback.print_exc()
            return None

    @with_retry(max_retries=2, delay=1)
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

    @with_retry(max_retries=3, delay=1)
    def consultar_pagamento(self, payment_id):
        """Consulta informações de um pagamento específico"""
        try:
            payment_info = self.sdk.payment().get(payment_id)
            return payment_info.get("response", {})
        except Exception as e:
            logger.error(f"Erro ao consultar pagamento {payment_id}: {str(e)}")
            return None

    @with_retry(max_retries=3, delay=1)
    def consultar_merchant_order(self, order_id):
        """Consulta informações de uma merchant order específica"""
        try:
            order_info = self.sdk.merchant_order().get(order_id)
            return order_info.get("response", {})
        except Exception as e:
            logger.error(f"Erro ao consultar merchant_order {order_id}: {str(e)}")
            return None