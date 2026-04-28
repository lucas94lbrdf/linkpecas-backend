import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class AdRating(Base):
    __tablename__ = "ad_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "ad_id", name="uq_user_ad_rating"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ad_id = Column(UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=False) # 1 a 5
    comment = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
