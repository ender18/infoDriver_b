from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class DriverAccount(Base):
    __tablename__ = "driver_accounts"

    id                    = Column(Integer, primary_key=True, index=True)
    company_id            = Column(Integer, ForeignKey("companies.id"), nullable=False)
    driver_id             = Column(Integer, nullable=False)
    callsign              = Column(String(50),  nullable=True)
    forename              = Column(String(100), nullable=True)
    surname               = Column(String(100), nullable=True)
    bank_name             = Column(String(150), nullable=True)
    bank_sort_code        = Column(String(100), nullable=True)
    current_balance       = Column(Float, default=0.0)
    outstanding_amount    = Column(Float, default=0.0)
    all_jobs_total        = Column(Float, default=0.0)
    all_jobs_commission   = Column(Float, default=0.0)
    last_processed_api    = Column(DateTime(timezone=True), nullable=True)
    notes                 = Column(Text, nullable=True)
    fetched_at            = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Campos de procesamiento contable
    process_status        = Column(String(20), nullable=True)   # None | 'done' | 'error'
    process_result        = Column(Text, nullable=True)
    process_balance_before = Column(Float, nullable=True)       # saldo re-verificado antes de procesar
    processed_at          = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_driver_accounts_company_id", "company_id"),
        Index("ix_driver_accounts_driver_id", "driver_id"),
    )
