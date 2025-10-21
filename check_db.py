# check_db.py
from app import create_app
from database import db
from models.presente import Presente

app = create_app()

with app.app_context():
    # Verifica se a tabela existe e tem dados
    try:
        count = Presente.query.count()
        print(f"📊 Total de presentes no banco: {count}")
        
        if count > 0:
            presentes = Presente.query.all()
            for p in presentes:
                print(f"🎁 {p.nome} - R$ {p.valor_total} - Ativo: {p.ativo}")
        else:
            print("❌ Nenhum presente encontrado no banco!")
            
    except Exception as e:
        print(f"💥 Erro ao acessar banco: {e}")