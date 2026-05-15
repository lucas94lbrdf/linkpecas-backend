import uuid
from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    term = Column(String(255), nullable=True)
    vehicle_context = Column(String(255), nullable=True)
    origin = Column(String(50), nullable=False, default="site")  # site, bot_whatsapp, etc.
    results_found = Column(Integer, default=0)

    # Atribuição enriquecida (mesmos campos do ClickEvent — facilita o cross-join)
    source_category = Column(String(50))
    referrer = Column(Text)
    user_agent = Column(Text)
    device = Column(String(50))
    browser = Column(String(50))
    os = Column(String(50))

    city = Column(String(100))
    state = Column(String(50))

    ip_address = Column(String(64))
    ip_hash = Column(String(64))

    created_at = Column(DateTime, server_default=func.now())
