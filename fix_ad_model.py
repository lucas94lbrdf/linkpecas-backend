from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE ads ADD COLUMN image_urls JSON;"))
    db.commit()
    print("image_urls column added.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
