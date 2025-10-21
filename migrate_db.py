# migrate_db.py
import os
import shutil
from app import create_app
from database import db
from models.presente import Presente

def migrate_database():
    print("🔄 Migrando banco de dados...")
    
    # Caminhos
    old_db = 'instance/wedding_gifts.db'
    new_db = 'wedding_gifts.db'
    
    # Se o banco antigo existe na instance, copia para raiz
    if os.path.exists(old_db):
        shutil.copy2(old_db, new_db)
        print(f"✅ Copiado {old_db} para {new_db}")
    
    # Se o banco novo existe, usa ele
    if os.path.exists(new_db):
        print(f"✅ Usando banco: {new_db}")
        
        app = create_app()
        with app.app_context():
            count = Presente.query.count()
            print(f"📊 Presentes no banco: {count}")
            
            if count == 0:
                print("📦 Criando dados de exemplo...")
                # Adiciona dados se estiver vazio
                sample_presentes = [
                    Presente(nome="Lua de Mel", descricao="Nossa viagem dos sonhos", valor_total=10000, valor_arrecadado=3500),
                    Presente(nome="Móveis", descricao="Sofá para nossa casa", valor_total=2500, valor_arrecadado=1200),
                    Presente(nome="Eletrodomésticos", descricao="Geladeira nova", valor_total=3000, valor_arrecadado=0),
                    Presente(nome="Jantar", descricao="Jantar romântico", valor_total=500, valor_arrecadado=500),
                ]
                for item in sample_presentes:
                    db.session.add(item)
                db.session.commit()
                print("✅ Dados criados!")
    else:
        print("❌ Nenhum banco encontrado")

if __name__ == '__main__':
    migrate_database()