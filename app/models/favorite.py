import uuid
from sqlalchemy import Column, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "ad_id", name="uq_user_ad_favorite"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ad_id = Column(UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
