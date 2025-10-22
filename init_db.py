# init_db.py - Atualização segura de presentes
from app import create_app
from database import db
from models.presente import Presente

def init_sample_data():
    app = create_app()
    
    with app.app_context():
        # Cria as tabelas se não existirem
        db.create_all()
        
        # Dados de exemplo atualizados
        sample_presentes = [
            {
                "nome": "Só para dizer que não dei nada",
                "descricao": "",
                "valor_total": 100.00,
                "ativo": True,
                "imagem_url": "/static/images/julios.png"
            },
            {
                "nome": "Para o noivo estar coberto de razão",
                "descricao": "",
                "valor_total": 80.00,
                "ativo": True,
                "imagem_url": "/static/images/cobertor.png"
            },
            {
                "nome": "Dei o MELHOR presente",
                "descricao": "",
                "valor_total": 300.00,
                "ativo": True,
                "imagem_url": "/static/images/melhor.png"
            },
            {
                "nome": "Ajude a pagar o Casamento",
                "descricao": "",
                "valor_total": 250.00,
                "ativo": True,
                "imagem_url": "/static/images/ajude.png"
            },
            {
                "nome": "Pagar a paciência da noiva",
                "descricao": "",
                "valor_total": 80.00,
                "ativo": True,
                "imagem_url": "/static/images/paciencia.png"
            },
            {
                "nome": "Deus tocou seu coração",
                "descricao": "",
                "valor_total": 100.00,
                "ativo": True,
                "imagem_url": "/static/images/sourica.png"
            },
            {
                "nome": "Taxa para não jogar o buquê para o seu par",
                "descricao": "",
                "valor_total": 120.00,
                "ativo": True,
                "imagem_url": "/static/images/buque.png"
            }
        ]
        
        atualizados = 0
        adicionados = 0

        for p_data in sample_presentes:
            presente = Presente.query.filter_by(nome=p_data['nome']).first()
            if presente:
                # Atualiza os campos existentes
                presente.descricao = p_data['descricao']
                presente.valor_total = p_data['valor_total']
                presente.ativo = p_data['ativo']
                presente.imagem_url = p_data['imagem_url']
                atualizados += 1
            else:
                # Cria novo presente
                novo_presente = Presente(**p_data)
                db.session.add(novo_presente)
                adicionados += 1

        db.session.commit()
        print(f"✅ Atualizados: {atualizados}, Adicionados: {adicionados}")
