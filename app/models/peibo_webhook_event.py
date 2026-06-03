from sqlalchemy import Column, Integer, String, Numeric, DateTime, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class PeiboWebhookEvent(Base):
    __tablename__ = "peibo_webhook_events"

    id                   = Column(Integer, primary_key=True, index=True)
    peibo_transaction_id = Column(Integer, ForeignKey("peibo_transactions.id"), nullable=True)
    tracking_code        = Column(String(100), nullable=True)

    status               = Column(String(50),     nullable=True)
    type                 = Column(String(20),      nullable=True)
    concept              = Column(String(255),     nullable=True)
    reference            = Column(String(100),     nullable=True)
    amount               = Column(Numeric(12, 2),  nullable=True)
    date_time            = Column(DateTime(timezone=True), nullable=True)
    refund_reason_code   = Column(Integer,         nullable=True)

    beneficiary_account  = Column(String(30),  nullable=True)
    originator_account   = Column(String(30),  nullable=True)
    originator_bank      = Column(String(10),  nullable=True)
    originator_name      = Column(String(200), nullable=True)
    originator_tax_id    = Column(String(20),  nullable=True)

    raw_payload          = Column(JSON, nullable=True)
    received_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_pwe_peibo_transaction_id", "peibo_transaction_id"),
        Index("ix_pwe_tracking_code",        "tracking_code"),
        Index("ix_pwe_received_at",          "received_at"),
    )
