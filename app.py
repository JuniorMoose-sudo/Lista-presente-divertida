from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
from config import Config
from database import db, init_db
from routes import register_routes
from models.presente import Presente
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializa banco de dados
    init_db(app)
    
    # Registra rotas
    register_routes(app)
    
    # Rota principal
    @app.route('/')
    def index():
        try:
            presentes = Presente.query.filter_by(ativo=True).all()
            print(f"🎁 Carregando {len(presentes)} presentes")
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
                'environment': 'production' if os.environ.get('RENDER') else 'development'
            })
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    
    return app

app = create_app()

# Inicialização automática no Render
if os.environ.get('RENDER'):
    print("🚀 Inicializando no ambiente Render...")
    with app.app_context():
        try:
            from init_db import init_sample_data
            init_sample_data()
        except Exception as e:
            print(f"❌ Erro na inicialização: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = not bool(os.environ.get('RENDER'))
    app.run(host='0.0.0.0', port=port, debug=debug)