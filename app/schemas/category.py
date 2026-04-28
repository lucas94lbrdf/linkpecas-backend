from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class CategoryBase(BaseModel):
    name: str
    slug: str
    parent_id: Optional[UUID] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None

class CategoryInDB(CategoryBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
