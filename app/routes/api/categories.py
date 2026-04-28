from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryInDB
from app.routes.api.auth import get_current_user
from app.models.user import User

router = APIRouter()

def check_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: apenas administradores podem realizar esta ação"
        )
    return user

@router.get("/", response_model=List[CategoryInDB])
def list_categories(db: Session = Depends(get_db)):
    """Lista todas as categorias (Público)"""
    return db.query(Category).order_by(Category.name).all()

@router.post("/", response_model=CategoryInDB, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate, 
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin)
):
    """Cria uma nova categoria (Admin)"""
    # Verifica se slug já existe
    if db.query(Category).filter(Category.slug == category_in.slug).first():
        raise HTTPException(status_code=400, detail="Slug já está em uso")
    
    category = Category(**category_in.dict())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.put("/{category_id}", response_model=CategoryInDB)
def update_category(
    category_id: UUID,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin)
):
    """Atualiza uma categoria (Admin)"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    update_data = category_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(check_admin)
):
    """Remove uma categoria (Admin)"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    db.delete(category)
    db.commit()
    return None
