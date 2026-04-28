from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()

class ShopUpdateSchema(BaseModel):
    name: str = None
    slug: str = None
    description: str = None
    phone: str = None
    website: str = None
    location: str = None
    logo: str = None

@router.get("/me")
def get_my_shop(db: Session = Depends(get_db)):
    # Mock do usuário logado (usando o primeiro do banco para teste)
    user = db.query(User).first()
    
    if not user:
        raise HTTPException(404, "User not found")
    
    # Bloqueia se não for premium
    if user.plan != "premium":
        raise HTTPException(403, "Acesso exclusivo para assinantes PREMIUM. Faça o upgrade para ter sua própria loja!")

    return {
        "id": str(user.id),
        "name": user.shop_name or "Minha Loja",
        "slug": user.shop_slug or "minha-loja",
        "description": user.shop_description or "",
        "phone": user.phone or "",
        "website": "",
        "location": user.shop_location or "São Paulo, SP",
        "logo": user.shop_logo or "",
        "plan": user.plan
    }

@router.put("/me")
def update_my_shop(data: ShopUpdateSchema, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Bloqueia se não for premium
    if user.plan != "premium":
        raise HTTPException(403, "Acesso exclusivo para assinantes PREMIUM.")

    if data.name: user.shop_name = data.name
    if data.slug: user.shop_slug = data.slug
    if data.description: user.shop_description = data.description
    if data.location: user.shop_location = data.location
    if data.logo: user.shop_logo = data.logo
    
    db.commit()
    return {"status": "success"}
