from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from config import Config
from database import db, init_db
from routes import register_routes
from models.presente import Presente
from security import init_security, cache, logger
from production import init_production, validate_request_json
import os
import time

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Registra tempo de início para uptime
    app.start_time = time.time()
    
    # Inicializa banco de dados
    init_db(app)
    
    # Inicializa segurança (CORS, Rate Limit, Cache)
    init_security(app)
    
    # Inicializa configurações de produção se necessário
    if Config.PRODUCTION:
        init_production(app)
    
    # Registra rotas
    register_routes(app)
    
    # Rota principal
    @app.route('/')
    @cache.cached(timeout=300)  # Cache por 5 minutos
    def index():
        try:
            presentes = Presente.query.filter_by(ativo=True).all()  # Corrigido: usa 'ativo'
            logger.info("presentes_carregados", quantidade=len(presentes))
            return render_template('index.html', 
                                 presentes=presentes,
                                 noivo_nome=Config.NOIVO_NOME,
                                 data_casamento=Config.DATA_CASAMENTO)
        except Exception as e:
            print(f"💥 Erro na rota principal: {e}")
            return "Erro ao carregar a página"
    
    # Health check para Render
    @app.route('/health')
    def health():
        try:
            # Testa conexão com o banco
            Presente.query.first()
            return jsonify({
                'status': 'healthy', 
                'database': 'connected',
                'environment': 'production' if os.environ.get('RENDER') else 'development',
                'uptime': f"{time.time() - app.start_time:.2f}s"
            })
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    
    # Rota de status da API
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'status': 'online',
            'service': 'wedding-gift-app',
            'version': '1.0.0',
            'payment_methods': ['pix']
        })
    
    return app

app = create_app()

# Inicializa/atualiza os presentes automaticamente
if os.environ.get('RENDER'):
    print("🚀 Inicializando no ambiente Render e atualizando presentes...")
    try:
        from init_db import init_sample_data
        with app.app_context():
            init_sample_data()
            print("✅ Dados de exemplo inicializados com sucesso!")
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
else:
    print("💻 Inicializando localmente...")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = not bool(os.environ.get('RENDER'))
    app.run(host='0.0.0.0', port=port, debug=debug)