from flask import Blueprint, jsonify, request
from database import db
from models.presente import Presente
from models.contribuicao import Contribuicao
from services.mercado_pago_service import MercadoPagoService

payment_bp = Blueprint('pagamentos', __name__)

@payment_bp.route('/api/contribuir', methods=['POST'])
def criar_contribuicao():
    try:
        data = request.get_json()
        print(f"📨 Dados recebidos: {data}")
        
        # --- Validações básicas ---
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
        
        # Verifica se o valor é válido
        if valor_contribuicao <= 0:
            return jsonify({
                'success': False,
                'error': 'Valor deve ser maior que zero'
            }), 400
        
        # --- Cria a contribuição ---
        contribuicao = Contribuicao(
            presente_id=presente.id,
            nome_contribuinte=data['nome'],
            email_contribuinte=data['email'],
            valor=valor_contribuicao,
            mensagem=data.get('mensagem', ''),
            status='pendente',
            metodo_pagamento=data.get('metodo_pagamento', 'cartao')
        )
        
        db.session.add(contribuicao)
        db.session.commit()
        
        print(f"✅ Contribuição criada: {contribuicao.id} - Método: {contribuicao.metodo_pagamento}")
        
        # --- PROCESSAMENTO PIX ---
        if data.get('metodo_pagamento') == 'pix':
            print("🎯 Processando PIX...")
            
            # Para PIX, marcamos como aprovado automaticamente
            contribuicao.status = 'aprovado'
            presente.valor_arrecadado += valor_contribuicao
            db.session.commit()
            
            return jsonify({
                'success': True,
                'metodo': 'pix',
                'contribuicao_id': contribuicao.id,
                'message': 'Contribuição registrada com sucesso!'
            })
        
        # --- PROCESSAMENTO MERCADO PAGO (CARTÃO) ---
        else:
            print("🎯 Processando Mercado Pago...")
            mp_service = MercadoPagoService()
            base_url = request.host_url.rstrip('/')
            preference = mp_service.criar_preferencia_pagamento(contribuicao, presente, base_url)
            
            if not preference or "init_point" not in preference:
                error_msg = "Erro ao gerar link de pagamento com Mercado Pago"
                print(f"❌ {error_msg}")
                
                # Remove a contribuição se falhou
                db.session.delete(contribuicao)
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
            
            # Atualiza com ID do pagamento
            contribuicao.payment_id = preference.get('id')
            db.session.commit()
            
            return jsonify({
                'success': True,
                'payment_url': preference['init_point'],
                'contribuicao_id': contribuicao.id,
                'metodo': 'cartao'
            })
        
    except Exception as e:
        db.session.rollback()
        print(f"💥 Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@payment_bp.route('/webhook/mercadopago', methods=['POST'])
def webhook_mercadopago():
    try:
        data = request.get_json()
        mp_service = MercadoPagoService()
        resultado = mp_service.processar_webhook(data)
        
        if resultado:
            contribuicao = Contribuicao.query.get(resultado['contribuicao_id'])
            if contribuicao:
                status_mp = resultado['status']
                if status_mp == 'approved':
                    contribuicao.status = 'aprovado'
                    # Atualiza valor arrecadado
                    presente = contribuicao.presente
                    presente.valor_arrecadado += contribuicao.valor
                elif status_mp in ['cancelled', 'rejected']:
                    contribuicao.status = 'cancelado'
                
                db.session.commit()
                print(f"✅ Webhook processado - Contribuição {contribuicao.id}: {status_mp}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Erro no webhook: {e}")
        return jsonify({'success': False}), 500

@payment_bp.route('/obrigado')
def obrigado():
    contribuicao_id = request.args.get('contribuicao_id', '')
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Obrigado!</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background: linear-gradient(135deg, #ff6b6b, #4ecdc4); min-height: 100vh; display: flex; align-items: center; }}
        </style>
    </head>
    <body>
        <div class="container text-center text-white">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="bg-dark bg-opacity-50 rounded p-5">
                        <h1 class="display-4">🎉 Obrigado!</h1>
                        <p class="lead">Sua contribuição foi processada com sucesso.</p>
                        <p>Muito obrigado por fazer parte do nosso sonho!</p>
                        <a href="/" class="btn btn-primary btn-lg mt-3">Voltar para a Lista de Presentes</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@payment_bp.route('/erro')
def erro():
    contribuicao_id = request.args.get('contribuicao_id', '')
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Erro no Pagamento</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background: linear-gradient(135deg, #ff6b6b, #dc3545); min-height: 100vh; display: flex; align-items: center; }}
        </style>
    </head>
    <body>
        <div class="container text-center text-white">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="bg-dark bg-opacity-50 rounded p-5">
                        <h1 class="display-4">❌ Erro no Pagamento</h1>
                        <p class="lead">Houve um problema ao processar seu pagamento.</p>
                        <p>Por favor, tente novamente ou entre em contato conosco.</p>
                        <a href="/" class="btn btn-primary btn-lg mt-3">Tentar Novamente</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@payment_bp.route('/pendente')
def pendente():
    contribuicao_id = request.args.get('contribuicao_id', '')
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pagamento Pendente</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background: linear-gradient(135deg, #ffd166, #ff9e00); min-height: 100vh; display: flex; align-items: center; }}
        </style>
    </head>
    <body>
        <div class="container text-center text-dark">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="bg-light bg-opacity-75 rounded p-5">
                        <h1 class="display-4">⏳ Pagamento Pendente</h1>
                        <p class="lead">Seu pagamento está sendo processado.</p>
                        <p>Você receberá uma confirmação por email em breve.</p>
                        <a href="/" class="btn btn-primary btn-lg mt-3">Voltar para a Lista de Presentes</a>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@payment_bp.route('/api/test-mp-credentials')
def test_mp_credentials():
    try:
        from services.mercado_pago_service import MercadoPagoService
        mp_service = MercadoPagoService()
        
        test_data = {
            "items": [
                {
                    "title": "Teste",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": 10.0
                }
            ]
        }
        
        result = mp_service.sdk.preference().create(test_data)
        
        return jsonify({
            'success': True,
            'message': 'Credenciais OK',
            'response_keys': list(result.get('response', {}).keys()) if result else []
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500