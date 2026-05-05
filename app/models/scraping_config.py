import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from app.db.base import Base

class ScrapingConfig(Base):
    __tablename__ = "scraping_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    marketplace = Column(String(50), unique=True, nullable=False)
    base_url_pattern = Column(String(255), nullable=True)
    
    selectors_json = Column(JSONB, nullable=True)
    rate_limit_per_minute = Column(Integer, default=60)
    requires_headless = Column(Boolean, default=False)
    user_agent_pool = Column(ARRAY(String), nullable=True)
    
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())
