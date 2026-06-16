from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class PeiboTransaction(Base):
    __tablename__ = "peibo_transactions"

    id             = Column(Integer, primary_key=True, index=True)
    tracking_code  = Column(String(100), nullable=False, unique=True, index=True)
    transaction_id = Column(String(100), nullable=False)

    status         = Column(String(20),     nullable=False, default="pending")
    amount         = Column(Numeric(12, 2), nullable=False)

    company_id     = Column(Integer, ForeignKey("companies.id"), nullable=False)

    source_type    = Column(String(50),  nullable=False)   # driver_payment | invoice | ...
    source_id      = Column(Integer,     nullable=False)   # ID en la tabla fuente

    # Datos del beneficiario (snapshot al momento del pago)
    callsign         = Column(String(50),    nullable=True)
    beneficiary_name = Column(String(100),   nullable=True)
    original_amount  = Column(Numeric(12,2), nullable=True)  # antes de ajuste contadora

    # Auditoría
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=True)
    error_message  = Column(Text,    nullable=True)
    paid_at        = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_pt_company_id", "company_id"),
        Index("ix_pt_source",     "source_type", "source_id"),
        Index("ix_pt_status",     "status"),
        Index("ix_pt_created_at", "created_at"),
    )
