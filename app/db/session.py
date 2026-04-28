import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://lrodrigues:Seleida50@localhost:5432/auto-marketplace"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
