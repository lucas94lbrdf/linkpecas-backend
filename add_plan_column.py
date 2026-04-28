from app.db.session import SessionLocal
from sqlalchemy import text

def update_user_plan_schema():
    db = SessionLocal()
    try:
        print("Adicionando coluna 'plan' na tabela 'users'...")
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(30) DEFAULT 'free'"))
        db.commit()
        print("Coluna 'plan' adicionada com sucesso! ✅")
    except Exception as e:
        print(f"Erro ao atualizar usuários: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_user_plan_schema()
