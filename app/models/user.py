
import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)

    role = Column(String(30), default="seller")
    status = Column(String(30), default="active")
    plan = Column(String(30), default="free")
    
    phone = Column(String(20), nullable=True)
    document = Column(String(20), nullable=True)

    email_verified = Column(Boolean, default=False)

    # Stripe
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(30), nullable=True)  # active, canceled, past_due, etc.

    # Perfil da Loja (Premium)
    shop_name = Column(String(255), nullable=True)
    shop_slug = Column(String(255), nullable=True, unique=True)
    shop_description = Column(String(500), nullable=True)
    shop_location = Column(String(255), nullable=True)
    shop_logo = Column(String(500), nullable=True)

    created_at = Column(DateTime, server_default=func.now())