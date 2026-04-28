from sqlalchemy import text
from app.db.session import engine

def add_user_columns():
    print("Adicionando colunas 'phone' e 'document' à tabela users...")
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS document VARCHAR(20)"))
            print("Sucesso! Colunas adicionadas.")
    except Exception as e:
        print(f"Erro ao adicionar colunas: {e}")

if __name__ == "__main__":
    add_user_columns()
