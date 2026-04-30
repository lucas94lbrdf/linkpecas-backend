import hashlib
from app.db.session import SessionLocal
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    pwd_sha256 = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(pwd_sha256)

def create_admin():
    db = SessionLocal()
    try:
        # Verifica se já existe
        admin = db.query(User).filter(User.email == "admin@automarket.com").first()
        if admin:
            print("Admin ja existe!")
            return

        new_admin = User(
            name="Administrador Master",
            email="admin@linkpecas.com",
            password_hash=hash_password("admin123"),
            role="admin",
            status="active",
            email_verified=True
        )
        db.add(new_admin)
        db.commit()
        print("Admin criado com sucesso!")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
