import uuid
from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Marketplace(Base):
    __tablename__ = "marketplaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), unique=True, nullable=False)
    icon_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Marketplace {self.name}>"
