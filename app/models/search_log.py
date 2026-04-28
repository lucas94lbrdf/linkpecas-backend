import uuid
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base

class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    term = Column(String(255), nullable=True) # Pode ser nulo se for busca só por veículo
    vehicle_context = Column(String(255), nullable=True) # Ex: "Volkswagen Gol 2020"
    origin = Column(String(50), nullable=False, default="site") # 'site', 'bot_whatsapp', etc
    results_found = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
