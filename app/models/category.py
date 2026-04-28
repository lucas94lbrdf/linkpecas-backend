import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    icon = Column(String(50), nullable=True) # Lucide icon name
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
