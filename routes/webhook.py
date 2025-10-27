import os
import logging
import requests
import re
from flask import Blueprint, request, jsonify
from database import db
from models.contribuicao import Contribuicao
from models.presente import Presente
from routes.payment_routes import verify_webhook_signature
from services.mercado_pago_service import MercadoPagoService

webhook_bp = Blueprint("webhook", __name__, url_prefix="/webhook")

ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")

# Validação do ACCESS_TOKEN
if not ACCESS_TOKEN:
    logger = logging.getLogger("routes.webhook")
    logger.error("❌ MERCADOPAGO_ACCESS_TOKEN não encontrado nas variáveis de ambiente.")

logger = logging.getLogger("routes.webhook")
logger.setLevel(logging.INFO)

def extract_order_id(resource_url):
    """Extrai o ID da ordem a partir da URL completa ou ID direto"""
    if not resource_url:
        return None
    match = re.search(r'/merchant_orders/(\d+)', resource_url)
    return match.group(1) if match else str(resource_url)

@webhook_bp.route("/mercadopago", methods=["POST"])
def mercadopago_webhook():
    try:
        raw_data = request.data.decode('utf-8')
        signature = request.headers.get('X-Hub-Signature', '')
        
        # Extract the hexdigest if the signature is in the format "sha256=hexdigest"
        if signature.startswith('sha256='):
            signature = signature[7:]  # Remove "sha256=" prefix

        if not verify_webhook_signature(raw_data, signature):
            logger.warning(f"⚠ Assinatura inválida no webhook. Dados recebidos: {raw_data}")
            return jsonify({"status": "invalid signature"}), 403

        data = request.get_json(force=True)
        logger.info(f"📩 Webhook recebido: {data}")

        # Suporte completo aos formatos antigo e novo do Mercado Pago
        payment_id = None
        topic = None
        action = None

        # Formato novo (2023+): {"type": "payment", "action": "payment.created", "data": {"id": "123"}}
        if "type" in data and "data" in data:
            topic = data["type"]
            action = data.get("action")
            payment_id = data["data"].get("id")
        
        # Formato antigo: {"topic": "payment", "resource": "123"} ou parâmetros URL
        else:
            topic = data.get("topic") or request.args.get("topic")
            payment_id = data.get("resource") or request.args.get("id") or data.get("id")

        if not topic or not payment_id:
            logger.warning("❌ Webhook sem topic/type ou id")
            return jsonify({"status": "ignored"}), 200

        # Detecção melhorada de eventos de pagamento
        # Formato antigo: topic="payment"
        # Formato novo: type="payment" ou action="payment.created"
        if "payment" in (topic or "") or "payment" in (action or ""):
            return handle_payment(payment_id)
        
        # Detecção de merchant_order
        elif "merchant_order" in (topic or "") or "merchant_order" in (action or ""):
            order_id = extract_order_id(payment_id)
            return handle_merchant_order(order_id)

        else:
            logger.warning(f"⚠ Tipo de webhook desconhecido: topic={topic}, action={action}")
            return jsonify({"status": "ignored"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao processar webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def handle_payment(payment_id):
    """Busca informações de pagamento e atualiza contribuição"""
    try:
        # Busca dados atualizados do pagamento usando o SDK
        mp_service = MercadoPagoService()
        payment_info = mp_service.sdk.payment().get(payment_id)
        
        if not payment_info or not payment_info.get('response'):
            logger.warning(f"⚠ Falha ao buscar pagamento {payment_id}")
            return jsonify({"status": "payment_not_found"}), 200

        payment = payment_info.get("response", {})
        logger.info(f"💰 Pagamento recebido: {payment}")

        # Tenta encontrar a contribuição pelo payment_id
        contribuicao = Contribuicao.query.filter_by(payment_id=str(payment_id)).first()
        
        # Se não encontrar pelo payment_id, tenta pelos metadados
        if not contribuicao:
            metadata = payment.get("metadata") or {}
            contrib_id = metadata.get("contribuicao_id")
            if contrib_id:
                contribuicao = Contribuicao.query.get(contrib_id)

        if not contribuicao:
            logger.warning(f"⚠ Contribuição para pagamento {payment_id} não encontrada")
            return jsonify({"status": "not found"}), 404

        # Verifica se o status já está atualizado (idempotência)
        status = payment.get("status", "")
        if contribuicao.status == status:
            logger.info(f"ℹ Contribuição {contribuicao.id} já está no status '{status}', ignorando atualização.")
            return jsonify({"status": "already_processed"}), 200
            
        # Atualiza status conforme o Mercado Pago
        contribuicao.status = status
        
        # Se aprovado, atualiza o valor arrecadado do presente
        if status == 'approved':
            presente = Presente.query.get(contribuicao.presente_id)
            if presente:
                presente.valor_arrecadado = float(presente.valor_arrecadado or 0) + float(contribuicao.valor)
                logger.info(f"💰 Valor arrecadado atualizado para {presente.valor_arrecadado}")

        db.session.commit()
        logger.info(f"✅ Contribuição {contribuicao.id} atualizada para '{status}'")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao processar pagamento {payment_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def handle_merchant_order(order_id):
    """Busca informações do pedido (merchant order)"""
    try:
        mp_service = MercadoPagoService()
        order_info = mp_service.sdk.merchant_order().get(order_id)
        
        if not order_info or not order_info.get('response'):
            logger.warning(f"⚠ Falha ao buscar merchant_order {order_id}")
            return jsonify({"status": "merchant_order_not_found"}), 200

        order = order_info.get("response", {})
        logger.info(f"📦 Merchant order recebida: {order}")

        payments = order.get("payments", [])
        if not payments:
            logger.info("ℹ Nenhum pagamento ainda associado à ordem.")
            return jsonify({"status": "pending"}), 200

        # Pega o primeiro pagamento vinculado
        payment_id = payments[0].get("id")
        if payment_id:
            return handle_payment(payment_id)

        return jsonify({"status": "no_payment_found"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao processar merchant_order {order_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500