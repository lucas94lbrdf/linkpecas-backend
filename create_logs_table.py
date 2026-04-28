from app.db.session import SessionLocal
from sqlalchemy import text

def create_activity_logs_table():
    db = SessionLocal()
    try:
        print("Criando tabela 'activity_logs'...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(id),
                action VARCHAR(100) NOT NULL,
                entity_type VARCHAR(50),
                entity_id VARCHAR(100),
                details TEXT,
                ip_address VARCHAR(50),
                user_agent TEXT,
                http_method VARCHAR(10),
                device VARCHAR(20),
                location VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()

        # Adiciona colunas se a tabela já existia sem elas
        for col, definition in [
            ("http_method", "VARCHAR(10)"),
            ("device", "VARCHAR(20)"),
            ("location", "VARCHAR(200)"),
        ]:
            try:
                db.execute(text(
                    f"ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS {col} {definition}"
                ))
                db.commit()
            except Exception:
                db.rollback()

        print("Tabela 'activity_logs' pronta! ✅")
    except Exception as e:
        print(f"Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_activity_logs_table()
