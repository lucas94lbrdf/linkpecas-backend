import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.marketplace import Marketplace
from app.routes.api.auth import get_current_user
from app.models.user import User

router = APIRouter()


class MarketplaceSchema(BaseModel):
    name: str
    slug: str
    icon_url: Optional[str] = None


class MarketplaceUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: Optional[bool] = None


def check_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores")
    return user


def serialize_mp(mp: Marketplace):
    return {
        "id": str(mp.id),
        "name": mp.name,
        "slug": mp.slug,
        "icon_url": mp.icon_url,
        "is_active": mp.is_active,
    }


@router.get("/")
def list_marketplaces(db: Session = Depends(get_db)):
    """Lista todos os marketplaces cadastrados."""
    return [serialize_mp(mp) for mp in db.query(Marketplace).all()]


@router.post("/")
def create_marketplace(
    data: MarketplaceSchema,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
):
    """Cadastra um novo marketplace (Admin)."""
    existing = db.query(Marketplace).filter(Marketplace.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug já cadastrado")

    mp = Marketplace(
        id=uuid.uuid4(),
        name=data.name,
        slug=data.slug,
        icon_url=data.icon_url,
    )
    db.add(mp)
    db.commit()
    db.refresh(mp)
    return serialize_mp(mp)


@router.put("/{mp_id}")
def update_marketplace(
    mp_id: str,
    data: MarketplaceUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
):
    """Atualiza um marketplace (Admin)."""
    mp = db.query(Marketplace).filter(Marketplace.id == mp_id).first()
    if not mp:
        raise HTTPException(status_code=404, detail="Marketplace não encontrado")

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(mp, field, value)

    db.commit()
    db.refresh(mp)
    return serialize_mp(mp)


@router.delete("/{mp_id}")
def delete_marketplace(
    mp_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
):
    """Remove um marketplace (Admin)."""
    mp = db.query(Marketplace).filter(Marketplace.id == mp_id).first()
    if not mp:
        raise HTTPException(status_code=404, detail="Marketplace não encontrado")

    db.delete(mp)
    db.commit()
    return {"message": "Marketplace removido com sucesso"}
