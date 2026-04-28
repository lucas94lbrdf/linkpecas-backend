import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.community import Community
from app.models.ad import Ad
from app.routes.api.auth import get_current_user
from app.models.user import User

router = APIRouter()


class CommunitySchema(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    image_url: Optional[str] = None


class CommunityUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    image_url: Optional[str] = None


def check_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores")
    return user


def serialize_community(c: Community):
    return {
        "id": str(c.id),
        "name": c.name,
        "slug": c.slug,
        "description": c.description,
        "avatar_url": c.avatar_url,
        "banner_url": c.banner_url,
        "image_url": c.image_url,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "ads_count": len(c.ads) if c.ads else 0,
    }


@router.get("/")
def list_communities(db: Session = Depends(get_db)):
    """Retorna a lista de todas as comunidades disponíveis."""
    communities = db.query(Community).all()
    return [serialize_community(c) for c in communities]


@router.get("/{community_id}")
def get_community(community_id: str, db: Session = Depends(get_db)):
    """Retorna os dados de uma comunidade específica."""
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Comunidade não encontrada")
    return serialize_community(community)


@router.get("/{community_id}/ads")
def get_community_ads(community_id: str, db: Session = Depends(get_db)):
    """Retorna todos os anúncios vinculados àquela comunidade."""
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Comunidade não encontrada")
    return community.ads


@router.post("/")
def create_community(
    data: CommunitySchema,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
):
    """Cria uma nova comunidade (Admin)."""
    existing = db.query(Community).filter(Community.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug já cadastrado")

    community = Community(
        id=uuid.uuid4(),
        name=data.name,
        slug=data.slug,
        description=data.description,
        avatar_url=data.avatar_url,
        banner_url=data.banner_url,
        image_url=data.image_url or data.avatar_url,
    )
    db.add(community)
    db.commit()
    db.refresh(community)
    return serialize_community(community)


@router.put("/{community_id}")
def update_community(
    community_id: str,
    data: CommunityUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
):
    """Atualiza uma comunidade (Admin)."""
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Comunidade não encontrada")

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(community, field, value)

    db.commit()
    db.refresh(community)
    return serialize_community(community)


@router.delete("/{community_id}")
def delete_community(
    community_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin),
):
    """Remove uma comunidade (Admin)."""
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Comunidade não encontrada")

    db.delete(community)
    db.commit()
    return {"message": "Comunidade removida com sucesso"}
