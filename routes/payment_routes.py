from flask import Blueprint, jsonify, request
from database import db
from models.presente import Presente
from models.contribuicao import Contribuicao
from services.mercado_pago_service import MercadoPagoService
from security import limiter, logger
from config import Config
import hmac
import hashlib
import time
import functools

payment_bp = Blueprint('pagamentos', __name__)

def verify_webhook_signature(data, signature):
    """Verifica a assinatura do webhook do Mercado Pago"""
    if not Config.MERCADOPAGO_WEBHOOK_SECRET:
        logger.warning("webhook_secret_missing", message="Chave do webhook não configurada")
        return True  # Aceita se não configurado
        
    calculated = hmac.new(
        Config.MERCADOPAGO_WEBHOOK_SECRET.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated, signature)

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
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e)
                    )
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            logger.error(
                "max_retries_reached",
                function=func.__name__,
                error=str(last_error)
            )
            raise last_error
        return wrapper
    return decorator

from services.validation_service import ValidationService

@payment_bp.route('/api/contribuir', methods=['POST'])
@limiter.limit("10/minute")  # Limite de 10 tentativas por minuto por IP
def criar_contribuicao():
    try:
        data = request.get_json()
        logger.info("contribution_request_received", data=data)
        
        # --- Validações básicas ---
        if not data or not all(k in data for k in ['presente_id', 'nome', 'email', 'valor', 'cpf']):
            return jsonify({
                'success': False,
                'error': 'Dados incompletos'
            }), 400
            
        # Validações de negócio
        validation_errors = ValidationService.validar_contribuicao(
            data['presente_id'],
            data['valor'],
            data['email']
        )
        
        if validation_errors:
            logger.warning("contribution_validation_failed", 
                         errors=validation_errors,
                         email=data['email'])
            return jsonify({
                'success': False,
                'error': validation_errors[0],
                'all_errors': validation_errors
            }), 422
            
        # Verifica limite diário
        if ValidationService.verificar_valor_maximo_diario(data['email']):
            logger.warning("daily_limit_exceeded", email=data['email'])
            return jsonify({
                'success': False,
                'error': 'Limite diário de contribuições excedido'
            }), 429
            
        # Verifica disponibilidade do presente
        disponivel, erro = ValidationService.validar_presente_disponivel(data['presente_id'])
        if not disponivel:
            logger.warning("present_unavailable", 
                         presente_id=data['presente_id'],
                         error=erro)
            return jsonify({
                'success': False,
                'error': erro
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
@with_retry(max_retries=3, delay=2)  # Retry com backoff exponencial
def webhook_mercadopago():
    """Webhook para produção - com validações e retry"""
    try:
        logger.info("webhook_received", source="mercadopago")
        
        # Validação de assinatura
        signature = request.headers.get('X-Hub-Signature')
        if signature:
            data = request.get_data(as_text=True)
            if not verify_webhook_signature(data, signature):
                logger.error("webhook_invalid_signature")
                return jsonify({'success': False, 'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        if not data:
            logger.error("webhook_no_data")
            return jsonify({'success': False, 'error': 'No data'}), 400
        
        # Processa o webhook com retry
        mp_service = MercadoPagoService()
        resultado = mp_service.processar_webhook(data)
        
        if not resultado:
            logger.error("webhook_processing_failed")
            return jsonify({'success': False, 'error': 'Failed to process webhook'}), 422
            
        contribuicao = Contribuicao.query.get(resultado['contribuicao_id'])
        if not contribuicao:
            logger.error(
                "webhook_contribuicao_not_found",
                contribuicao_id=resultado.get('contribuicao_id')
            )
            return jsonify({'success': False, 'error': 'Contribution not found'}), 404
        
        status_mp = resultado['status']
        logger.info(
            "webhook_updating_status",
            contribuicao_id=contribuicao.id,
            old_status=contribuicao.status,
            new_status=status_mp
        )
        
        # Processamento dos diferentes status
        if status_mp == 'approved':
            contribuicao.status = 'aprovado'
            presente = contribuicao.presente
            valor_anterior = float(presente.valor_arrecadado)
            presente.valor_arrecadado += float(contribuicao.valor)
            
            logger.info(
                "payment_approved",
                contribuicao_id=contribuicao.id,
                valor=float(contribuicao.valor),
                presente_id=presente.id,
                valor_anterior=valor_anterior,
                valor_atual=float(presente.valor_arrecadado)
            )
        elif status_mp in ['cancelled', 'rejected']:
            contribuicao.status = 'cancelado'
            logger.info(
                "payment_cancelled",
                contribuicao_id=contribuicao.id,
                reason=status_mp
            )
        elif status_mp == 'in_process':
            contribuicao.status = 'pendente'
            logger.info(
                "payment_pending",
                contribuicao_id=contribuicao.id
            )
        elif status_mp == 'refunded':
            contribuicao.status = 'reembolsado'
            logger.info(
                "payment_refunded",
                contribuicao_id=contribuicao.id
            )
            print(f"↩️ Pagamento reembolsado")
        
        db.session.commit()
        print(f"✅ Webhook processado com sucesso")
        return jsonify({'success': True})
    except Exception as e:
        print(f"💥 Erro no webhook: {e}")
        import traceback
        traceback.print_exc()
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