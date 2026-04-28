
import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Numeric,
    DateTime,
    ForeignKey,
    Boolean,
    BigInteger,
    JSON,
    Integer,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Ad(Base):
    __tablename__ = "ads"
    __table_args__ = (
        CheckConstraint(
            "year_start IS NULL OR year_start >= 1900",
            name="ck_ads_year_start_min",
        ),
        CheckConstraint(
            "year_end IS NULL OR year_end >= year_start",
            name="ck_ads_year_end_gte_year_start",
        ),
        Index(
            "ix_ads_vehicle_lookup",
            "manufacturer_id",
            "model_id",
            "year_start",
            "year_end",
            "status",
        ),
        Index("ix_ads_is_universal_status", "is_universal", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    short_code = Column(String(20), unique=True)

    description = Column(Text)

    price = Column(Numeric(12,2))
    old_price = Column(Numeric(12,2), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    category = Column(String(100), nullable=True) # Fallback / Categoria texto livre
    image_url = Column(Text, nullable=True)
    image_urls = Column(JSON, nullable=True)
    external_url = Column(Text, nullable=False)
    condition = Column(String(20), default="new") # new, used
    warranty = Column(String(100), nullable=True)
    free_shipping = Column(Boolean, default=False)

    marketplace = Column(String(80))
    city = Column(String(150), nullable=True)
    state = Column(String(150), nullable=True)

    is_universal = Column(Boolean, nullable=False, default=True, server_default=func.true())
    manufacturer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    year_start = Column(Integer, nullable=True)
    year_end = Column(Integer, nullable=True)
    engine = Column(String(80), nullable=True)

    marketplace_options = Column(JSON, nullable=True, default=list)
    group_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    status = Column(String(30), default="active")
    is_featured = Column(Boolean, default=False)

    views_count = Column(BigInteger, default=0)
    clicks_count = Column(BigInteger, default=0)
    unique_clicks = Column(BigInteger, default=0)
    
    average_rating = Column(Numeric(3,2), default=0.00)
    rating_count = Column(Integer, default=0)
    score = Column(Numeric(10,2), default=0.00)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    expires_at = Column(DateTime, nullable=True)

    # Relacionamento Many-to-Many com Community
    communities = relationship("Community", secondary="ad_communities", back_populates="ads")
