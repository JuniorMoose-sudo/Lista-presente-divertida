"""
Configuração do Gunicorn para produção
"""
import multiprocessing
import os

# Configurações do servidor
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
worker_class = 'gthread'
timeout = 120

# Configurações de performance
worker_connections = 1000
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logs
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# SSL (se necessário)
keyfile = os.getenv('SSL_KEYFILE')
certfile = os.getenv('SSL_CERTFILE')

def on_starting(server):
    """Log quando o servidor está iniciando"""
    print("🚀 Iniciando servidor Gunicorn...")

def on_exit(server):
    """Log quando o servidor está finalizando"""
    print("👋 Finalizando servidor Gunicorn...")

def worker_int(worker):
    """Log quando um worker é interrompido"""
    print(f"😴 Worker {worker.pid} interrompido")

def worker_abort(worker):
    """Log quando um worker falha"""
    print(f"💥 Worker {worker.pid} abortado")

def post_fork(server, worker):
    """Configurações após fork do worker"""
    print(f"✨ Worker {worker.pid} iniciado")

    # Configuração do Sentry para cada worker
    if os.getenv('SENTRY_DSN'):
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        
        sentry_sdk.init(
            dsn=os.getenv('SENTRY_DSN'),
            environment=os.getenv('FLASK_ENV', 'production'),
            integrations=[FlaskIntegration()],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
        )