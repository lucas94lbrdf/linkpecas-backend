import os
from typing import Optional
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.db.session import SessionLocal
from app.models.user import User
from app.utils.activity import log_activity

# ==========================================================
# CONFIG
# ==========================================================

SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_ME_NOW")
ALGORITHM = "HS256"
ACCESS_EXPIRE_MINUTES = 60
REFRESH_EXPIRE_DAYS = 30

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dependency para o banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================================
# SCHEMAS
# ==========================================================

class RegisterSchema(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "seller"
    phone: Optional[str] = None
    document: Optional[str] = None

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class RefreshSchema(BaseModel):
    refresh_token: str

# ==========================================================
# HELPERS
# ==========================================================

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str):
    if not password_hash: return False
    return pwd_context.verify(password, password_hash)

def create_access_token(data: dict):
    payload = data.copy()
    payload["type"] = "access"
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    payload = data.copy()
    payload["type"] = "refresh"
    payload["exp"] = datetime.utcnow() + timedelta(days=REFRESH_EXPIRE_DAYS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

def generate_auth_response(user: User):
    access = create_access_token({
        "sub": user.email,
        "user_id": str(user.id),
        "role": user.role
    })
    refresh = create_refresh_token({
        "sub": user.email,
        "user_id": str(user.id)
    })
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "plan": user.plan,
            "shop_logo": user.shop_logo,
            "shop_name": user.shop_name,
            "shop_description": user.shop_description
        }
    }

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = decode_token(token)
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    return user
def get_admin_user(
    user: User = Depends(get_current_user)
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return user

# ==========================================================
# ROUTES
# ==========================================================

from app.services.email_service import send_welcome_email, send_password_recovery
import uuid

@router.post("/register")
async def register(request: Request, data: RegisterSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "E-mail já cadastrado")

    # Validação de Documento (CPF/CNPJ) para Lojistas
    if data.role == "seller" and data.document:
        doc = "".join(filter(str.isdigit, data.document))
        if len(doc) not in [11, 14]:
            raise HTTPException(400, "Documento inválido. Deve ter 11 (CPF) ou 14 (CNPJ) dígitos.")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        phone=data.phone,
        document=data.document
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_activity(db, request, "USER_REGISTER", "user", str(user.id),
                 f"Novo usuário: {user.email}", user.id)

    # Dispara email de boas vindas
    send_welcome_email(user.email, user.name)

    return generate_auth_response(user)

class ForgotPasswordSchema(BaseModel):
    email: str

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        # Aqui no futuro você pode gerar um token real no banco. Por enquanto enviamos um link fictício seguro para o frontend.
        reset_token = str(uuid.uuid4())
        reset_link = f"http://localhost:5173/reset-password?token={reset_token}"
        send_password_recovery(user.email, user.name, reset_link)
    
    # Retorna sucesso mesmo se não existir para não expor quais emails estão cadastrados
    return {"message": "Se o e-mail existir, você receberá um link de recuperação."}

@router.post("/login")
async def login(request: Request, data: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha inválidos")

    log_activity(db, request, "USER_LOGIN", "user", str(user.id),
                 f"Login: {user.email}", user.id)

    return generate_auth_response(user)

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "plan": user.plan,
        "shop_logo": user.shop_logo,
        "shop_name": user.shop_name,
        "shop_description": user.shop_description
    }

@router.patch("/me")
async def update_profile(
    data: dict, 
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if "name" in data: user.name = data["name"]
    if "shop_name" in data: user.shop_name = data["shop_name"]
    if "shop_description" in data: user.shop_description = data["shop_description"]
    if "shop_logo" in data: user.shop_logo = data["shop_logo"]
    
    db.commit()
    return {"message": "Perfil atualizado com sucesso"}

@router.delete("/me")
async def delete_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.delete(user)
    db.commit()
    return {"message": "Conta removida com sucesso"}