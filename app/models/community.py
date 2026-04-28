import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Table, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

# Tabela de Associação Many-to-Many
ad_communities = Table(
    "ad_communities",
    Base.metadata,
    Column("ad_id", UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"), primary_key=True),
    Column("community_id", UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True),
)

class Community(Base):
    __tablename__ = "communities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relacionamento Many-to-Many com Ad
    ads = relationship("Ad", secondary=ad_communities, back_populates="communities")
