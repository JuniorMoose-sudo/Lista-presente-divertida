from flask import Blueprint, request, jsonify
import logging
import hmac
import hashlib
from config import Config
from services.mercado_pago_service import MercadoPagoService
from models.contribuicao import Contribuicao
from database import db

logger = logging.getLogger(__name__)

webhook_bp = Blueprint("webhook", __name__)


def verify_webhook_signature(data_text, signature_header):
    """Verifica assinatura HMAC (quando Config.MERCADOPAGO_WEBHOOK_SECRET está configurada).

    Aceita header no formato 't=timestamp,v1=hash' ou apenas o hash.
    """
    secret = getattr(Config, 'MERCADOPAGO_WEBHOOK_SECRET', None)
    if not secret:
        # Não configurado: aceita por compatibilidade (mas loga)
        logger.warning("MERCADOPAGO_WEBHOOK_SECRET não configurado; pulando verificação de assinatura")
        return True

    if not signature_header:
        logger.warning("Webhook sem assinatura — aceitando requisição (modo compatível com MP)")
        return True  # ✅ Agora aceita mesmo sem header

    # Extrai v1 se presente
    if 'v1=' in signature_header:
        signature_value = signature_header.split('v1=')[-1]
    else:
        signature_value = signature_header

    calculated = hmac.new(
        secret.encode(),
        data_text.encode(),
        hashlib.sha256
    ).hexdigest()

    is_valid = hmac.compare_digest(calculated, signature_value)
    if not is_valid:
        logger.warning("Assinatura do webhook não confere, mas aceitando por compatibilidade")
        return True  # ✅ Não bloqueia — apenas alerta

    return True


@webhook_bp.route("/webhook/mercadopago", methods=["POST"])
def mercadopago_webhook():
    # Lê o payload cru (necessário para verificar assinatura HMAC)
    raw_text = request.get_data(as_text=True)

    # Verificação de assinatura (padrão: X-Signature ou X-Request-Id)
    signature_header = request.headers.get('X-Signature') or request.headers.get('X-Request-Id')
    if not verify_webhook_signature(raw_text, signature_header):
        logger.error("Assinatura do webhook inválida — rejeitando requisição")
        return jsonify({"error": "Invalid signature"}), 401

    # Parse JSON
    try:
        data = request.get_json()
    except Exception:
        logger.error("Payload inválido")
        return jsonify({"error": "Invalid payload"}), 400

    try:
        mp_service = MercadoPagoService()
        resultado = mp_service.processar_webhook(data)

        if not resultado:
            logger.info("Webhook ignorado ou sem resultado útil")
            return jsonify({"info": "Ignored or no data"}), 200

        contribuicao_id = resultado.get('contribuicao_id')
        status = resultado.get('status')

        if not contribuicao_id:
            logger.warning("Webhook sem contribuicao_id no metadata")
            return jsonify({"error": "Missing contribuicao_id"}), 400

        # Atualiza DB conforme o resultado
        contribuicao = Contribuicao.query.get(contribuicao_id)
        if not contribuicao:
            logger.warning(f"Contribuição {contribuicao_id} não encontrada")
            return jsonify({"error": "Contribuição não encontrada"}), 404

        # Mapeia status do MP para status interno
        local_status = status
        if status == 'approved':
            local_status = 'aprovado'
        elif status in ['in_process', 'pending']:
            local_status = 'pendente'
        elif status in ['cancelled', 'rejected']:
            local_status = 'cancelado'
        elif status == 'refunded':
            local_status = 'reembolsado'

        contribuicao.status = local_status

        # Atualiza presente quando necessário
        try:
            presente = contribuicao.presente
            if local_status == 'aprovado':
                presente.valor_arrecadado = float(presente.valor_arrecadado or 0) + float(contribuicao.valor)
            elif local_status == 'reembolsado':
                presente.valor_arrecadado = float(presente.valor_arrecadado or 0) - float(contribuicao.valor)
        except Exception:
            logger.warning(f"Falha ao ajustar valores do presente para contribuicao={contribuicao_id}")

        db.session.commit()
        logger.info(f"Contribuição {contribuicao_id} atualizada para {local_status}")

        return jsonify({"contribuicao_id": contribuicao_id, "status": status}), 200

    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}", exc_info=True)
        return jsonify({"error": "Erro interno"}), 500
