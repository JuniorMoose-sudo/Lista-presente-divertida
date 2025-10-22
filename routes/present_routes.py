from flask import Blueprint, jsonify, request
from database import db
from models.presente import Presente
from models.contribuicao import Contribuicao
from services.mercado_pago_service import MercadoPagoService

present_bp = Blueprint('presentes', __name__)

# --- Listar todos os presentes ---
@present_bp.route('/api/presentes', methods=['GET'])
def listar_presentes():
    try:
        presentes = Presente.query.filter_by(ativo=True).all()
        return jsonify({
            'success': True,
            'presentes': [p.to_dict() for p in presentes]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# --- Obter presente por ID ---
@present_bp.route('/api/presentes/<int:presente_id>', methods=['GET'])
def obter_presente(presente_id):
    try:
        presente = Presente.query.get_or_404(presente_id)
        return jsonify({
            'success': True,
            'presente': presente.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404


# Nota: a rota `/api/contribuir` foi movida para `routes/payment_routes.py`.
# Removida aqui para evitar duplicação de endpoints.
