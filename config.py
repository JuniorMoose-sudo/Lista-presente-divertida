import os
from datetime import datetime
import logging.config

class Config:
    # Ambiente
    PRODUCTION = os.getenv("FLASK_ENV") == "production" or os.getenv("PRODUCTION") == "1"
    
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta-padrao-mudar-em-producao')
    if PRODUCTION and SECRET_KEY == 'chave-secreta-padrao-mudar-em-producao':
        raise ValueError("⚠️ SECRET_KEY padrão detectada em produção!")
    
    # CORS e Rate Limiting
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    RATE_LIMIT_APP = os.environ.get('RATE_LIMIT_APP', '100/hour')  # Limite global
    RATE_LIMIT_PAYMENT = os.environ.get('RATE_LIMIT_PAYMENT', '10/minute')  # Limite pagamentos
    
    # Cache
    CACHE_TYPE = 'simple'  # Usando cache simples em memória
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutos
    
    # Mercado Pago
    MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
    MERCADOPAGO_WEBHOOK_SECRET = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET")
    MERCADOPAGO_WEBHOOK_URL = os.environ.get('MERCADOPAGO_WEBHOOK_URL')
    
    if PRODUCTION:
        if not MERCADOPAGO_ACCESS_TOKEN:
            raise ValueError("⚠️ MERCADOPAGO_ACCESS_TOKEN não configurado em produção!")
        if not MERCADOPAGO_WEBHOOK_SECRET:
            raise ValueError("⚠️ MERCADOPAGO_WEBHOOK_SECRET não configurado em produção!")
        if not MERCADOPAGO_WEBHOOK_URL:
            raise ValueError("⚠️ MERCADOPAGO_WEBHOOK_URL não configurado em produção!")
            
    # URL do site
    SITE_URL = os.environ.get('SITE_URL', 'https://lista-presente-divertida.onrender.com')

    
    # Database
    if PRODUCTION:
        # Usa DATABASE_URL do ambiente (pode conter sslmode conforme o provedor)
        SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    else:
        # Em desenvolvimento, usa SQLite local sem ssl
        SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///lista_casamento.db")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Engine options: somente aplicar SSL em produção
    if PRODUCTION:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 1,
            'max_overflow': 2,
            'pool_timeout': 30,
            'pool_recycle': 1800,
            'pool_pre_ping': True,
            'connect_args': {
                'sslmode': 'require',
                'options': '-c timezone=UTC'
            }
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True
        }
    
    # Configurações do Casal
    NOIVO_NOME = "Junior & Karol"
    
    # Configurações de Logging
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    }
    DATA_CASAMENTO = "24 de Janeiro de 2026"
    
    # Logging
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'json': {
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default' if not PRODUCTION else 'json',
                'level': 'INFO'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'app.log',
                'maxBytes': 1024 * 1024,  # 1 MB
                'backupCount': 3,
                'formatter': 'json',
                'level': 'INFO'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file'] if PRODUCTION else ['console']
        }
    }

    
