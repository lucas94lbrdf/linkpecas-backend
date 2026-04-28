from app.db.session import SessionLocal
from sqlalchemy import text

def update_click_events_schema():
    db = SessionLocal()
    try:
        print("Atualizando tabela 'click_events'...")
        db.execute(text("ALTER TABLE click_events ADD COLUMN IF NOT EXISTS device VARCHAR(50)"))
        db.execute(text("ALTER TABLE click_events ADD COLUMN IF NOT EXISTS city VARCHAR(100)"))
        db.execute(text("ALTER TABLE click_events ADD COLUMN IF NOT EXISTS state VARCHAR(50)"))
        db.commit()
        print("Tabela 'click_events' atualizada com sucesso! ✅")
    except Exception as e:
        print(f"Erro ao atualizar click_events: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_click_events_schema()
