# init_db.py - Versão para Neon/Render
from app import create_app
from database import db
from models.presente import Presente
import os

def init_sample_data():
    app = create_app()
    
    with app.app_context():
        # NO RENDER: Não drope o banco, apenas crie tabelas se não existirem
        db.create_all()
        
        # Verifica se já existem presentes para não duplicar
        if Presente.query.count() == 0:
            print("📦 Criando dados iniciais...")
            
            # Dados de exemplo ATUALIZADOS - use URLs absolutas para imagens
            sample_presentes = [
                Presente(
                    nome="Só para dizer que não dei nada",
                    descricao="",
                    valor_total=10000.00,
                    ativo=True,
                    imagem_url="/static/images/julios.png"
                ),
                Presente(
                    nome="Para o noivo estar coberto de razão",
                    descricao="",
                    valor_total=2500.00,
                    ativo=True,
                    imagem_url="/static/images/cobertor.png"
                ),
                Presente(
                    nome="Dei o MELHOR presente",
                    descricao="",
                    valor_total=3000.00,
                    ativo=True,
                    imagem_url="/static/images/melhor.png"
                ),
                Presente(
                    nome="Ajude a pagar o Casamento",
                    descricao="",
                    valor_total=500.00,
                    ativo=True,
                    imagem_url="/static/images/ajude.png"
                ),
                Presente(
                    nome="Pagar a paciência da noiva",
                    descricao="",
                    valor_total=500.00,
                    ativo=True,
                    imagem_url="/static/images/paciencia.png"
                ),
                Presente(
                    nome="Deus tocou seu coração",
                    descricao="",
                    valor_total=500.00,
                    ativo=True,
                    imagem_url="/static/images/sourica.png"
                ),
                Presente(
                    nome="Taxa para não jogar o buquê no seu par",
                    descricao="",
                    valor_total=500.00,
                    ativo=True,
                    imagem_url="/static/images/buque.png"
                )
            ]
            
            for presente in sample_presentes:
                db.session.add(presente)
            
            db.session.commit()
            print("✅ Dados de exemplo criados com sucesso!")
            print(f"📦 Foram criados {len(sample_presentes)} presentes")
        else:
            count = Presente.query.count()
            print(f"📊 Banco já contém {count} presentes")

if __name__ == '__main__':
    init_sample_data()