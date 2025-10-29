from flask import Blueprint, jsonify, request, render_template
from database import db
from models.presente import Presente
from models.contribuicao import Contribuicao
from security import limiter, logger
from config import Config
import hmac
import hashlib
import time
import functools

present_bp = Blueprint('present', __name__)

def verify_webhook_signature(data, signature):
    """Verifica a assinatura do webhook (mantido para futuras implementações)"""
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

# Serviço de validação simplificado
class ValidationService:
    @staticmethod
    def validar_contribuicao(presente_id, valor, email):
        """Valida dados da contribuição"""
        errors = []
        
        # Valida presente
        presente = Presente.query.get(presente_id)
        if not presente:
            errors.append('Presente não encontrado')
            return errors
            
        if not presente.ativo:
            errors.append('Este presente não está mais disponível')
            
        # Valida valor (APENAS valor positivo)
        try:
            valor_float = float(str(valor).replace(',', '.'))
            if valor_float <= 0:
                errors.append('Valor deve ser maior que zero')
            # REMOVIDO: Verificação de valor máximo
        except (ValueError, TypeError):
            errors.append('Valor inválido')
            
        # Valida email básico
        if '@' not in email or '.' not in email:
            errors.append('Email inválido')
            
        return errors
    
    @staticmethod
    def validar_presente_disponivel(presente_id):
        """Verifica se o presente está disponível"""
        presente = Presente.query.get(presente_id)
        if not presente:
            return False, 'Presente não encontrado'
            
        if not presente.ativo:  # CORRIGIDO: active → ativo
            return False, 'Presente não está mais disponível'
            
        return True, None
    
    @staticmethod
    def verificar_valor_maximo_diario(email):
        """Verifica limite diário por email"""
        # Implementação simplificada - sempre retorna False (sem limite)
        return False

@present_bp.route('/')
def index():
    """Página principal com lista de presentes"""
    presentes = Presente.query.filter_by(ativo=True).all()
    return render_template('index.html', presentes=presentes)


@present_bp.route('/api/presentes')
def get_presents():
    """API para obter lista de presentes"""
    try:
        presents = Presente.query.filter_by(ativo=True).all()
        presents_data = []
        for presente in presentes:
            presents_data.append({
                'id': presente.id,
                'nome': presente.nome,
                'descricao': presente.descricao,
                'valor_total': float(presente.valor_total),
                'imagem_url': presente.imagem_url,
                'ativo': presente.ativo  # CORRIGIDO: active → ativo
            })
        return jsonify({'success': True, 'presents': presents_data})
    except Exception as e:
        logger.error("error_getting_presents", error=str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

@present_bp.route('/api/contribuir', methods=['POST'])
@limiter.limit("10/minute")
def criar_contribuicao():
    """Processa contribuição via PIX"""
    try:
        data = request.get_json()
        logger.info("contribution_request_received", data=data)
        
        # Validações básicas
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

        try:
            # Trata valor com vírgula ou ponto
            valor_str = str(data['valor']).replace(',', '.')
            valor_contribuicao = float(valor_str)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Valor inválido'
            }), 400

        # Verifica se o valor é válido
        if valor_contribuicao <= 0:
            return jsonify({
                'success': False,
                'error': 'Valor deve ser maior que zero'
            }), 400

        # Prepara dados pessoais
        cpf_raw = data.get('cpf', '')
        if isinstance(cpf_raw, str):
            cpf_raw = cpf_raw.replace('.', '').replace('-', '').strip()
        telefone_raw = data.get('telefone', '')

        # Cria a contribuição
        contribuicao = Contribuicao(
            presente_id=presente.id,
            nome_contribuinte=data['nome'],
            email_contribuinte=data['email'],
            cpf_contribuinte=cpf_raw,
            telefone_contribuinte=telefone_raw,
            valor=valor_contribuicao,
            mensagem=data.get('mensagem', ''),
            status='aprovado',  # PIX é aprovado automaticamente
            metodo_pagamento='pix'
        )

        db.session.add(contribuicao)
        
        # Atualiza valor arrecadado do presente
        presente.valor_arrecadado = float(presente.valor_arrecadado or 0) + valor_contribuicao
        
        db.session.commit()
        
        logger.info("contribution_created", 
                   contribuicao_id=contribuicao.id,
                   valor=valor_contribuicao,
                   metodo='pix')
        
        return jsonify({
            'success': True,
            'contribuicao_id': contribuicao.id,
            'message': 'Contribuição registrada com sucesso via PIX!'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error("contribution_error", error=str(e))
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor'
        }), 500

@present_bp.route('/obrigado')
def obrigado():
    """Página de agradecimento"""
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

@present_bp.route('/erro')
def erro():
    """Página de erro"""
    return """
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