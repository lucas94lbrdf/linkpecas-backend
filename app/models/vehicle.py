import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class Manufacturer(Base):
    __tablename__ = "manufacturers"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_manufacturers_slug"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    logo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class VehicleModel(Base):
    __tablename__ = "vehicle_models"
    __table_args__ = (
        UniqueConstraint("manufacturer_id", "slug", name="uq_vehicle_models_manufacturer_slug"),
        Index("ix_vehicle_models_manufacturer", "manufacturer_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manufacturer_id = Column(UUID(as_uuid=True), ForeignKey("manufacturers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    vehicle_type = Column(String(50), default="car")
    generation = Column(String(100), nullable=True)   # ex: "MK4", "9N3", "2ª Geração"
    image_url = Column(String(500), nullable=True)    # foto do modelo
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class VehicleYear(Base):
    __tablename__ = "vehicle_years"
    __table_args__ = (
        UniqueConstraint("model_id", "year", name="uq_vehicle_years_model_year"),
        Index("ix_vehicle_years_model", "model_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
