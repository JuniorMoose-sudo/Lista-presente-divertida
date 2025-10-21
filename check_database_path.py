# check_database_path.py
import os
from app import create_app
from config import Config

print("🔍 Verificando configurações de banco...")
print(f"SQLALCHEMY_DATABASE_URI: {Config.SQLALCHEMY_DATABASE_URI}")

app = create_app()
with app.app_context():
    from database import db
    print(f"Database URL: {db.engine.url}")
    
# Lista arquivos .db no diretório
print("\n📁 Arquivos .db no diretório:")
for file in os.listdir('.'):
    if file.endswith('.db'):
        print(f"   {file} - Tamanho: {os.path.getsize(file)} bytes")