import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    plan_id = Column(UUID(as_uuid=True), nullable=True)  # FK para plans.id (sem mapeamento ORM)

    gateway = Column(String(50), nullable=True)                    # "stripe"
    gateway_subscription_id = Column(String(255), nullable=True)   # sub_xxx

    status = Column(String(30), nullable=True)                     # active, canceled, past_due

    started_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
