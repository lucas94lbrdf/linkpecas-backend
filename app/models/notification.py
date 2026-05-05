import uuid
import json
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Tipo: ad_approved | ad_rejected | ad_expired | new_lead | plan_updated | ad_deactivated
    type = Column(String(50), nullable=False)

    # Payload JSON da notificação
    data_json = Column(Text, nullable=True)

    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    @property
    def data(self):
        if self.data_json:
            try:
                return json.loads(self.data_json)
            except Exception:
                return {}
        return {}
