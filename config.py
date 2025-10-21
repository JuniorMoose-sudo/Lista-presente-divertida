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

    
    # Database - Configuração específica para Neon DB com SSL
    if PRODUCTION:
        # URL fixa do Neon com configurações SSL corretas
        SQLALCHEMY_DATABASE_URI = 'postgresql://neondb_owner:npg_HxOB9K6dlsfp@ep-late-firefly-a430xok0.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
    else:
        # Em desenvolvimento, usa SQLite
        SQLALCHEMY_DATABASE_URI = 'sqlite:///wedding_gifts.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações de conexão do banco otimizadas para Neon
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 1,  # Menor pool para evitar muitas conexões
        'max_overflow': 2,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,  # Verifica conexões antes de usar
        'connect_args': {
            'sslmode': 'require',
            'options': '-c timezone=UTC'
        }
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

    
