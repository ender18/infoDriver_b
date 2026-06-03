from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from app.database import Base


class DriverAccountHistory(Base):
    __tablename__ = "driver_accounts_history"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Datos del conductor
    driver_id           = Column(Integer,    nullable=False)
    callsign            = Column(String(50),  nullable=True)
    forename            = Column(String(100), nullable=True)
    surname             = Column(String(100), nullable=True)
    bank_name           = Column(String(150), nullable=True)
    bank_sort_code      = Column(String(100), nullable=True)
    current_balance     = Column(Float,  nullable=True)
    outstanding_amount  = Column(Float,  nullable=True)
    all_jobs_total      = Column(Float,  nullable=True)
    all_jobs_commission = Column(Float,  nullable=True)
    notes               = Column(Text,   nullable=True)
    fetched_at          = Column(DateTime(timezone=True), nullable=True)

    # Procesamiento Autocab
    process_status         = Column(String(20), nullable=True)
    process_result         = Column(Text,       nullable=True)
    process_balance_before = Column(Float,      nullable=True)
    processed_at           = Column(DateTime(timezone=True), nullable=True)

    # Pago Peibo
    peibo_transaction_id  = Column(Integer, ForeignKey("peibo_transactions.id"), nullable=True)

    __table_args__ = (
        Index("ix_dah_session_id",  "session_id"),
        Index("ix_dah_company_id",  "company_id"),
        Index("ix_dah_driver_id",   "driver_id"),
        Index("ix_dah_peibo_tx",    "peibo_transaction_id"),
    )
