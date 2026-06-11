from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    address = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    email = Column(String(150), nullable=True)
    phone = Column(String(30), nullable=True)

    # Datos de conexión Autocab (Azure)
    api_base_url          = Column(Text,        nullable=False)
    api_subscription_key  = Column(String(255), nullable=False)

    # Datos de conexión Peibo (pagos)
    peibo_customer_key       = Column(String(255), nullable=True)
    peibo_api_key            = Column(String(255), nullable=True)
    peibo_originator_account = Column(String(30),  nullable=True)

    # Reglas de validación configurables por empresa
    validation_config = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    def __repr__(self):
        return f"<Company {self.name}>"
