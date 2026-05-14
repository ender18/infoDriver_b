from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class PaymentLog(Base):
    __tablename__ = "payment_log"

    id         = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)
    # refresh_start | refresh_done | process_done | process_error
    # payment_initiated | payment_error | webhook_received | webhook_error
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    driver_id  = Column(Integer, nullable=True)
    session_id = Column(String(36), nullable=True)
    history_id = Column(Integer, ForeignKey("driver_accounts_history.id"), nullable=True)
    payload    = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_payment_log_company_id", "company_id"),
        Index("ix_payment_log_driver_id",  "driver_id"),
        Index("ix_payment_log_session_id", "session_id"),
        Index("ix_payment_log_event_type", "event_type"),
        Index("ix_payment_log_created_at", "created_at"),
    )
