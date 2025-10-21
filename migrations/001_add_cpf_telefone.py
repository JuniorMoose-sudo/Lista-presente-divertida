"""
Simple migration script: add cpf_contribuinte and telefone_contribuinte to contribuições
Usage: python migrations/001_add_cpf_telefone.py
This script is intentionally simple and targets SQLite used in the project.
"""
import sqlite3
import os

DB_PATH = 'wedding_gifts.db'

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Banco não encontrado em {DB_PATH}. Rode migrate_db.py ou crie o banco primeiro.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        table = 'contribuicoes'

        # Verifica se a tabela existe
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cur.fetchone():
            print(f"❌ Tabela '{table}' não encontrada no banco. Verifique o esquema.")
            return

        changes = []
        if not column_exists(conn, table, 'cpf_contribuinte'):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN cpf_contribuinte VARCHAR(20)")
            changes.append('cpf_contribuinte')

        if not column_exists(conn, table, 'telefone_contribuinte'):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN telefone_contribuinte VARCHAR(30)")
            changes.append('telefone_contribuinte')

        conn.commit()

        if changes:
            print(f"✅ Colunas adicionadas: {', '.join(changes)}")
        else:
            print("ℹ️ Colunas já existentes. Nenhuma alteração feita.")

    except Exception as e:
        print(f"💥 Erro: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
