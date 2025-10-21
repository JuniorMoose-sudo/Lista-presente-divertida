"""
Utilitários e configurações específicas para ambiente de produção.
Inclui compressão, healthchecks e proteções de segurança.
"""
from flask import request, current_app
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix
import functools
import bleach
import time
from security import logger

# Configuração de compressão
compress = Compress()

def init_production(app):
    """Inicializa configurações de produção"""
    # Suporte a proxy (importante para HTTPS no Render)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    
    # Ativa compressão gzip
    compress.init_app(app)
    
    # Headers de segurança
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self' https:; img-src 'self' https: data:; style-src 'self' https: 'unsafe-inline'; script-src 'self' https: 'unsafe-inline'"
        return response
    
    # Healthcheck mais robusto
    @app.route('/healthz')
    def healthcheck():
        checks = {
            'database': check_database(),
            'mercadopago': check_mercadopago(),
            'memory': check_memory(),
            'uptime': get_uptime()
        }
        
        status = 200 if all(v['status'] == 'ok' for v in checks.values()) else 503
        return {'status': 'healthy' if status == 200 else 'unhealthy', 'checks': checks}, status

def sanitize_input(data):
    """Sanitiza input do usuário para prevenir XSS"""
    if isinstance(data, str):
        return bleach.clean(data, strip=True)
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(i) for i in data]
    return data

def validate_request_json():
    """Decorator para validar e sanitizar JSON requests"""
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return {'error': 'Content-Type must be application/json'}, 400
            
            try:
                data = request.get_json()
                sanitized = sanitize_input(data)
                request._cached_json = (sanitized, True)  # Replace request.json with sanitized version
                return f(*args, **kwargs)
            except Exception as e:
                logger.error("invalid_json", error=str(e))
                return {'error': 'Invalid JSON format'}, 400
        return wrapper
    return decorator

def check_database():
    """Verifica conexão com banco de dados"""
    from database import db
    try:
        db.session.execute('SELECT 1')
        return {'status': 'ok', 'latency_ms': 0}  # TODO: Add latency measurement
    except Exception as e:
        logger.error("database_check_failed", error=str(e))
        return {'status': 'error', 'error': str(e)}

def check_mercadopago():
    """Verifica integração com Mercado Pago"""
    from services.mercado_pago_service import MercadoPagoService
    try:
        mp = MercadoPagoService()
        result = mp.testar_credenciais()
        return {'status': 'ok' if result else 'error'}
    except Exception as e:
        logger.error("mercadopago_check_failed", error=str(e))
        return {'status': 'error', 'error': str(e)}

def check_memory():
    """Verifica uso de memória"""
    import psutil
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'status': 'ok',
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024
        }
    except Exception as e:
        logger.error("memory_check_failed", error=str(e))
        return {'status': 'error', 'error': str(e)}

def get_uptime():
    """Retorna uptime da aplicação"""
    import time
    try:
        uptime = time.time() - current_app.start_time
        return {
            'status': 'ok',
            'uptime_seconds': int(uptime)
        }
    except Exception as e:
        logger.error("uptime_check_failed", error=str(e))
        return {'status': 'error', 'error': str(e)}