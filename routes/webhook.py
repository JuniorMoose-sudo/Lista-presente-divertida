import os
import logging
import requests
import re
from flask import Blueprint, request, jsonify
from database import db
from models.contribuicao import Contribuicao

webhook_bp = Blueprint("webhook", __name__, url_prefix="/webhook")

ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")

logger = logging.getLogger("routes.webhook")
logger.setLevel(logging.INFO)

def extract_order_id(resource_url):
    """Extrai o ID da ordem a partir da URL completa"""
    match = re.search(r'/merchant_orders/(\d+)', resource_url)
    return match.group(1) if match else resource_url

@webhook_bp.route("/mercadopago", methods=["POST"])
def mercadopago_webhook():
    try:
        data = request.get_json(force=True)
        logger.info(f"📩 Webhook recebido: {data}")

        # Suporte a novo formato do Mercado Pago
        payment_id = None
        topic = None

        if "type" in data and "data" in data:
            topic = data["type"]
            payment_id = data["data"].get("id")
        else:
            topic = data.get("topic") or request.args.get("topic")
            payment_id = data.get("id") or request.args.get("id") or data.get("resource")

        if not topic or not payment_id:
            logger.warning("❌ Webhook sem topic/type ou id")
            return jsonify({"status": "ignored"}), 200

<<<<<<< HEAD
        if "payment" in topic:
            return handle_payment(payment_id)
        elif "merchant_order" in topic:
            order_id = extract_order_id(payment_id)
=======
        # Se for notificação de pagamento
        if topic == "payment":
            return handle_payment(resource)

        # Se for notificação de pedido (merchant_order)
        elif topic == "merchant_order":
            order_id = extract_order_id(resource)
>>>>>>> 4f6147b19ab583a820a177f5700ab4a39c8f9e95
            return handle_merchant_order(order_id)

        else:
            logger.warning("⚠ Tipo de webhook desconhecido ou não suportado")
            return jsonify({"status": "ignored"}), 200

    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def handle_payment(payment_id):
    """Busca informações de pagamento e atualiza contribuição"""
    try:
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            logger.warning(f"⚠ Falha ao buscar pagamento {payment_id}: {r.text}")
            return jsonify({"status": "payment_not_found"}), 200

        payment_info = r.json()
        logger.info(f"💰 Pagamento recebido: {payment_info}")

        contrib_id = payment_info.get("metadata", {}).get("contribuicao_id")
        status = payment_info.get("status")

        if not contrib_id:
            logger.warning("⚠ Pagamento sem contrib_id nos metadados")
            return jsonify({"status": "ignored"}), 200

        contribuicao = Contribuicao.query.get(contrib_id)
        if not contribuicao:
            logger.warning(f"⚠ Contribuição {contrib_id} não encontrada")
            return jsonify({"status": "ignored"}), 200

        # Atualiza status conforme o Mercado Pago
        contribuicao.status_pagamento = status
        db.session.commit()

        logger.info(f"✅ Contribuição {contrib_id} atualizada para '{status}'")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"❌ Erro ao processar pagamento {payment_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def handle_merchant_order(order_id):
    """Busca informações do pedido (merchant order)"""
    try:
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        url = f"https://api.mercadolibre.com/merchant_orders/{order_id}"
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            logger.warning(f"⚠ Falha ao buscar merchant_order {order_id}: {r.text}")
            return jsonify({"status": "merchant_order_not_found"}), 200

        order_info = r.json()
        logger.info(f"📦 Merchant order recebida: {order_info}")

        payments = order_info.get("payments", [])
        if not payments:
            logger.info("ℹ Nenhum pagamento ainda associado à ordem.")
            return jsonify({"status": "pending"}), 200

        # Pega o primeiro pagamento vinculado
        payment_id = payments[0].get("id")
        if payment_id:
            return handle_payment(payment_id)

        return jsonify({"status": "no_payment_found"}), 200

    except Exception as e:
        logger.error(f"❌ Erro ao processar merchant_order {order_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500