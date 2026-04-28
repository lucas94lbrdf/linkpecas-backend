from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE ads ADD COLUMN free_shipping BOOLEAN DEFAULT FALSE;"))
    db.commit()
    print("free_shipping column added.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
