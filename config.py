import os
from datetime import datetime
import logging.config

class Config:
    # Ambiente
    PRODUCTION = bool(os.environ.get('RENDER', False))
    
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta-padrao-mudar-em-producao')
    if PRODUCTION and SECRET_KEY == 'chave-secreta-padrao-mudar-em-producao':
        raise ValueError("⚠️ SECRET_KEY padrão detectada em produção!")
    
    # CORS e Rate Limiting
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    RATE_LIMIT_APP = os.environ.get('RATE_LIMIT_APP', '100/hour')  # Limite global
    RATE_LIMIT_PAYMENT = os.environ.get('RATE_LIMIT_PAYMENT', '10/minute')  # Limite pagamentos
    
    # Cache
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')  # 'simple' ou 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutos
    
    # Mercado Pago
    MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
    MERCADOPAGO_WEBHOOK_SECRET = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET")
    
    if PRODUCTION:
        if not MERCADOPAGO_ACCESS_TOKEN:
            raise ValueError("⚠️ MERCADOPAGO_ACCESS_TOKEN não configurado em produção!")
        if not MERCADOPAGO_WEBHOOK_SECRET:
            raise ValueError("⚠️ MERCADOPAGO_WEBHOOK_SECRET não configurado em produção!")
    # URL do site
    SITE_URL = os.environ.get('SITE_URL', 'https://lista-presente-divertida.onrender.com')

    
    # Database - Render usa DATABASE_URL, converte para PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///wedding_gifts.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mercado Pago
    MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN', '')
    MERCADOPAGO_WEBHOOK_URL = os.environ.get('MERCADOPAGO_WEBHOOK_URL', '')
    
    # Configurações do Casal
    NOIVO_NOME = "Junior & Karol"
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

    
