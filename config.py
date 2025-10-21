import os
from datetime import datetime

class Config:
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta-padrao-mudar-em-producao')
    
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