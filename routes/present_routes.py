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


# --- Criar contribuição (nova rota) ---
@present_bp.route('/api/contribuir', methods=['POST'])
def criar_contribuicao():
    try:
        data = request.get_json()
        print(f"📨 Dados recebidos: {data}")  # DEBUG

        # Validação básica
        if not data or not all(k in data for k in ['presente_id', 'nome', 'email', 'valor']):
            return jsonify({
                'success': False,
                'error': 'Dados incompletos'
            }), 400

        presente = Presente.query.get(data['presente_id'])
        if not presente:
            return jsonify({
                'success': False,
                'error': 'Presente não encontrado'
            }), 404

        valor_contribuicao = float(data['valor'])
        if valor_contribuicao <= 0:
            return jsonify({
                'success': False,
                'error': 'Valor deve ser maior que zero'
            }), 400

        # Cria a contribuição
        contribuicao = Contribuicao(
            presente_id=presente.id,
            nome_contribuinte=data['nome'],
            email_contribuinte=data['email'],
            valor=valor_contribuicao,
            mensagem=data.get('mensagem', ''),
            status='pendente'
        )

        db.session.add(contribuicao)
        db.session.commit()

        print(f"✅ Contribuição criada: {contribuicao.id}")  # DEBUG

        # Cria preferência no Mercado Pago
        mp_service = MercadoPagoService()
        base_url = request.host_url.rstrip('/')
        preference = mp_service.criar_preferencia_pagamento(contribuicao, presente, base_url)

        print(f"🎯 Preference response: {preference}")  # DEBUG

        if not preference or "init_point" not in preference:
            error_msg = "Erro ao gerar link de pagamento com Mercado Pago"
            print(f"❌ {error_msg}")

            db.session.delete(contribuicao)
            db.session.commit()

            return jsonify({
                'success': False,
                'error': error_msg
            }), 500

        # Atualiza ID do pagamento
        contribuicao.payment_id = preference.get('id')
        db.session.commit()

        return jsonify({
            'success': True,
            'payment_url': preference['init_point'],
            'contribuicao_id': contribuicao.id
        })

    except Exception as e:
        db.session.rollback()
        print(f"💥 Erro geral: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
