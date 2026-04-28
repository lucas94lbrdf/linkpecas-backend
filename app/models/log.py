import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(String(100))

    details = Column(Text)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    http_method = Column(String(10))
    device = Column(String(20))
    location = Column(String(200))

    created_at = Column(DateTime, server_default=func.now())
