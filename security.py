"""
Configurações de segurança centralizadas para a aplicação.
Inclui CORS, Rate Limiting e outras medidas de proteção.
"""
from flask import request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import structlog
import logging.config
from config import Config

# Configuração de Logging
logging.config.dictConfig(Config.LOGGING_CONFIG)
logger = structlog.get_logger()

# Cache
cache = Cache()

# Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[Config.RATE_LIMIT_APP],
    storage_uri="memory://"  # Usando memória local ao invés de Redis
)

def init_security(app):
    """Inicializa todas as configurações de segurança"""
    # CORS
    CORS(app, origins=Config.CORS_ORIGINS)
    
    # Cache
    cache_config = {
        'CACHE_TYPE': Config.CACHE_TYPE,
        'CACHE_DEFAULT_TIMEOUT': Config.CACHE_DEFAULT_TIMEOUT
    }
    if Config.CACHE_TYPE == 'redis':
        cache_config['CACHE_REDIS_URL'] = Config.CACHE_REDIS_URL
    
    cache.init_app(app, config=cache_config)
    
    # Rate Limiter
    limiter.init_app(app)
    
    # Headers de Segurança
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Log de requisições em produção
    if Config.PRODUCTION:
        @app.before_request
        def log_request_info():
            logger.info(
                "request_started",
                path=request.path,
                method=request.method,
                remote_addr=request.remote_addr
            )
        
        @app.after_request
        def log_response_info(response):
            logger.info(
                "request_finished",
                path=request.path,
                method=request.method,
                status=response.status_code
            )
            return response

    logger.info("security_initialized", 
                cors_origins=Config.CORS_ORIGINS,
                cache_type=Config.CACHE_TYPE,
                rate_limit=Config.RATE_LIMIT_APP)
    
    return app