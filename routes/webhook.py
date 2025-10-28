import os
import logging
import requests
import re
import hmac
import hashlib
import time
from flask import Blueprint, request, jsonify
from database import db
from models.contribuicao import Contribuicao
from models.presente import Presente
from config import Config
from services.mercado_pago_service import MercadoPagoService, with_retry

webhook_bp = Blueprint("webhook", __name__, url_prefix="/webhook")

ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
MERCADOPAGO_WEBHOOK_SECRET = Config.MERCADOPAGO_WEBHOOK_SECRET

logger = logging.getLogger("routes.webhook")
logger.setLevel(logging.INFO)

# 🔹 Correção: garantir que exista handler de logs (evita erro no Render)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

# 🔹 Aviso se token estiver ausente
if not ACCESS_TOKEN:
    logger.error("❌ MERCADOPAGO_ACCESS_TOKEN não encontrado nas variáveis de ambiente.")


# ==========================================================
# 🔐 Verificação da assinatura do webhook
# ==========================================================
def verify_webhook_signature(request_data, data=None):
    """Verifica a assinatura do webhook do Mercado Pago"""
    if not MERCADOPAGO_WEBHOOK_SECRET:
        logger.warning("⚠ Chave do webhook não configurada — aceitando todas as requisições.")
        return True  # evita bloqueio caso variável não esteja definida

    signature_header = request.headers.get("X-Hub-Signature")

    topic = None
    type_event = None
    if data:
        topic = data.get("topic") or request.args.get("topic")
        type_event = data.get("type")

    # 🔸 Mercado Pago não envia assinatura em merchant_order
    if not signature_header:
        if "merchant_order" in (topic or "") or "merchant_order" in (type_event or ""):
            logger.info("🟢 Webhook merchant_order recebido sem assinatura (permitido).")
            return True
        logger.warning("⚠ Header de assinatura ausente — requisição rejeitada.")
        return False

    # 🔸 Extrair assinatura sem o prefixo "sha256="
    if signature_header.startswith("sha256="):
        try:
            signature_header = signature_header.split("sha256=")[1]
        except IndexError:
            logger.warning("⚠ Erro ao extrair assinatura SHA256 do header.")
            return False

    # 🔸 Calcular assinatura esperada com corpo bruto da requisição
    try:
        computed_signature = hmac.new(
            bytes(MERCADOPAGO_WEBHOOK_SECRET, "utf-8"),
            msg=request_data,
            digestmod=hashlib.sha256
        ).hexdigest()
    except Exception as e:
        logger.error(f"❌ Erro ao calcular assinatura: {e}", exc_info=True)
        return False

    # 🔸 Comparação segura
    is_valid = hmac.compare_digest(computed_signature, signature_header)

    if not is_valid:
        logger.warning(f"⚠ Assinatura inválida. Esperado: {computed_signature}, Recebido: {signature_header}")
    else:
        logger.info("✅ Assinatura válida confirmada.")

    return is_valid


# ==========================================================
# 🧩 Extrair ID da ordem
# ==========================================================
def extract_order_id(resource_url):
    """Extrai o ID da ordem a partir da URL completa ou ID direto"""
    if not resource_url:
        return None
    match = re.search(r"/merchant_orders/(\d+)", str(resource_url))
    return match.group(1) if match else str(resource_url)


# ==========================================================
# 🔄 Processamento do webhook (com retry)
# ==========================================================
@with_retry(max_retries=3, delay=1)
def process_webhook_with_retry(data, raw_data):
    """Processa webhook com retry em caso de falha"""
    topic = data.get("topic") or request.args.get("topic")
    type_event = data.get("type")

    # 🔹 Validação da assinatura
    if not verify_webhook_signature(raw_data, data):
        logger.warning("⚠ Assinatura inválida no webhook.")
        return jsonify({"status": "invalid signature"}), 403

    # 🔹 Log amigável
    if "merchant_order" in (topic or "") or "merchant_order" in (type_event or ""):
        logger.info(f"📦 MERCHANT ORDER webhook recebido: {data}")
    else:
        logger.info(f"💳 PAYMENT webhook recebido: {data}")

    return process_webhook_data(data)


# ==========================================================
# 🌐 Rota principal do Webhook
# ==========================================================
@webhook_bp.route("/mercadopago", methods=["POST"])
def mercadopago_webhook():
    try:
        raw_data = request.data  # corpo bruto da requisição
        data = request.get_json(force=True)

        logger.info(f"📩 Webhook recebido: {data}")
        return process_webhook_with_retry(data, raw_data)

    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao processar webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ==========================================================
# ⚙️ Processamento dos dados do webhook
# ==========================================================
def process_webhook_data(data):
    """Processa os dados do webhook e direciona para o handler correto"""
    payment_id = None
    topic = None
    action = None

    if "type" in data and "data" in data:
        topic = data["type"]
        action = data.get("action")
        payment_id = data["data"].get("id")
    else:
        topic = data.get("topic") or request.args.get("topic")
        payment_id = data.get("resource") or request.args.get("id") or data.get("id")

    if not topic or not payment_id:
        logger.warning("⚠ Webhook sem topic/type ou id.")
        return jsonify({"status": "ignored"}), 200

    if "payment" in (topic or "") or "payment" in (action or ""):
        return handle_payment(payment_id)

    elif "merchant_order" in (topic or "") or "merchant_order" in (action or ""):
        order_id = extract_order_id(payment_id)
        return handle_merchant_order(order_id)

    else:
        logger.warning(f"⚠ Tipo de webhook desconhecido: topic={topic}, action={action}")
        return jsonify({"status": "ignored"}), 200


# ==========================================================
# 💳 Handler: Pagamento
# ==========================================================
@with_retry(max_retries=3, delay=1)
def handle_payment(payment_id):
    """Busca informações de pagamento e atualiza contribuição"""
    try:
        mp_service = MercadoPagoService()
        payment_info = mp_service.consultar_pagamento(payment_id)

        if not payment_info or not payment_info.get("response"):
            logger.warning(f"⚠ Falha ao buscar pagamento {payment_id}")
            return jsonify({"status": "payment_not_found"}), 200

        payment = payment_info.get("response", {})
        logger.info(f"💰 Pagamento recebido: {payment}")

        contribuicao = Contribuicao.query.filter_by(payment_id=str(payment_id)).first()
        if not contribuicao:
            metadata = payment.get("metadata") or {}
            contrib_id = metadata.get("contribuicao_id")
            if contrib_id:
                contribuicao = Contribuicao.query.get(contrib_id)

        if not contribuicao:
            logger.warning(f"⚠ Contribuição para pagamento {payment_id} não encontrada.")
            return jsonify({"status": "not_found"}), 404

        status = payment.get("status", "")
        if contribuicao.status == status:
            logger.info(f"ℹ Contribuição {contribuicao.id} já está no status '{status}', ignorando.")
            return jsonify({"status": "already_processed"}), 200

        contribuicao.status = status

        # 🔹 Atualiza o valor arrecadado se o pagamento for aprovado
        if status == "approved":
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


# ==========================================================
# 📦 Handler: Merchant Order
# ==========================================================
@with_retry(max_retries=3, delay=1)
def handle_merchant_order(order_id):
    """Busca informações do pedido (merchant order)"""
    try:
        mp_service = MercadoPagoService()
        order_info = mp_service.consultar_merchant_order(order_id)

        if not order_info or not order_info.get("response"):
            logger.warning(f"⚠ Falha ao buscar merchant_order {order_id}")
            return jsonify({"status": "merchant_order_not_found"}), 200

        order = order_info.get("response", {})
        logger.info(f"📦 Merchant order recebida: {order}")

        payments = order.get("payments", [])
        if not payments:
            logger.info("ℹ Nenhum pagamento ainda associado à ordem.")
            return jsonify({"status": "pending"}), 200

        payment_id = payments[0].get("id")
        if payment_id:
            return handle_payment(payment_id)

        return jsonify({"status": "no_payment_found"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao processar merchant_order {order_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
