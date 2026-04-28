import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class AdCompatibility(Base):
    __tablename__ = "ad_compatibilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_id = Column(UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True)

    manufacturer_id = Column(UUID(as_uuid=True), ForeignKey("manufacturers.id", ondelete="SET NULL"), nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("vehicle_models.id", ondelete="SET NULL"), nullable=True)

    year_start = Column(Integer, nullable=True)
    year_end   = Column(Integer, nullable=True)
    engine     = Column(String(80), nullable=True)
    note       = Column(String(255), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
