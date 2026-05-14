from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, Numeric
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
    payment_status       = Column(String(20),  nullable=True)
    peibo_transaction_id = Column(String(100), nullable=True)
    peibo_tracking_code  = Column(String(100), nullable=True, index=True)
    peibo_paid_at        = Column(DateTime(timezone=True), nullable=True)

    # Webhook Peibo
    webhook_status              = Column(String(50),     nullable=True)
    webhook_transaction_id      = Column(String(100),    nullable=True)
    webhook_date_time           = Column(DateTime(timezone=True), nullable=True)
    webhook_concept             = Column(String(255),    nullable=True)
    webhook_reference           = Column(String(100),    nullable=True)
    webhook_amount              = Column(Numeric(12, 2), nullable=True)
    webhook_beneficiary_account = Column(String(30),     nullable=True)
    webhook_originator_account  = Column(String(30),     nullable=True)
    webhook_originator_bank     = Column(String(10),     nullable=True)
    webhook_originator_name     = Column(String(200),    nullable=True)
    webhook_originator_tax_id   = Column(String(20),     nullable=True)
    webhook_type                = Column(String(20),     nullable=True)
    webhook_refund_reason_code  = Column(Integer,        nullable=True)
    webhook_received_at         = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_dah_session_id",    "session_id"),
        Index("ix_dah_company_id",    "company_id"),
        Index("ix_dah_driver_id",     "driver_id"),
    )
