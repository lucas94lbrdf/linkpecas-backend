import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class ClickEvent(Base):
    __tablename__ = "click_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    ad_id = Column(UUID(as_uuid=True), ForeignKey("ads.id"))

    source = Column(String(100))
    subsource = Column(String(150))
    campaign = Column(String(150))
    creative = Column(String(150))

    marketplace = Column(String(100))
    external_url = Column(Text)

    # Atribuição enriquecida
    source_type = Column(String(50))      # 'community', 'site', 'bot'
    source_ref = Column(String(255))      # ID ou nome da referência
    source_category = Column(String(50))  # google, bing, whatsapp, direct, etc.
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))

    referrer = Column(Text)
    user_agent = Column(Text)
    device = Column(String(50))           # mobile, desktop, tablet
    browser = Column(String(50))          # Chrome, Firefox, Safari…
    os = Column(String(50))               # Windows, Android, iOS…

    city = Column(String(100))
    state = Column(String(50))
    country = Column(String(50))

    ip_address = Column(String(64))       # IP em texto (LGPD: pode ser desativado)
    ip_hash = Column(String(255))         # hash anonimizado para agregações

    clicked_at = Column(DateTime, server_default=func.now())
