import uuid
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class LinkCheck(Base):
    __tablename__ = "link_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_id = Column(UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True)
    external_url = Column(String(1000), nullable=False)
    marketplace = Column(String(50), nullable=False) # mercadolivre, olx, shopee, generic
    
    http_status = Column(Integer, nullable=True)
    is_available = Column(Boolean, nullable=False, default=True)
    signals_json = Column(JSONB, nullable=True)
    
    price_found = Column(Float, nullable=True)
    price_previous = Column(Float, nullable=True)
    
    error_message = Column(Text, nullable=True)
    check_duration_ms = Column(Integer, nullable=True)
    
    checked_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
