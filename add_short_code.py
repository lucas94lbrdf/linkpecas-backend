from app.db.session import SessionLocal
from sqlalchemy import text
import random
import string

def generate_short_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def update_schema_short_code():
    db = SessionLocal()
    try:
        print("Adicionando coluna 'short_code' na tabela 'ads'...")
        db.execute(text("ALTER TABLE ads ADD COLUMN IF NOT EXISTS short_code VARCHAR(20) UNIQUE"))
        db.commit()
        print("Coluna adicionada! ✅")
    except Exception as e:
        print(f"Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_schema_short_code()
