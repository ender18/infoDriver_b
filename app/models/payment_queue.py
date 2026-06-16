from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class PaymentQueue(Base):
    __tablename__ = "payment_queue"

    id         = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Fuente del pago
    source = Column(String(30), nullable=False)
    # driver_balance | referral_bonus | daily_bonus | first_trips_bonus | spei_transfer | individual

    # Datos del conductor denormalizados (snapshot al momento de encolar)
    driver_id      = Column(Integer,     nullable=True)
    callsign       = Column(String(50),  nullable=True)
    forename       = Column(String(100), nullable=True)
    surname        = Column(String(100), nullable=True)
    bank_name      = Column(String(150), nullable=True)
    bank_sort_code = Column(String(100), nullable=True)

    # Montos
    amount          = Column(Float, nullable=False)   # calculado por el módulo origen
    adjusted_amount = Column(Float, nullable=True)    # ajuste manual de la contadora

    # Notas y referencia al origen
    notes      = Column(Text, nullable=True)
    source_ref = Column(String(255), nullable=True)   # ej. session_id, "semana 2026-06-09/15", etc.

    # Estado: pending | approved | rejected | discarded | paid
    status           = Column(String(20), nullable=False, default="pending", index=True)
    rejection_reason = Column(Text, nullable=True)

    # Auditoría
    queued_by_id   = Column(Integer, ForeignKey("users.id"), nullable=True)
    queued_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at    = Column(DateTime(timezone=True), nullable=True)

    # Enlace Peibo (se llena cuando se ejecuta el pago — fase futura)
    peibo_transaction_id = Column(Integer, ForeignKey("peibo_transactions.id"), nullable=True)

    queued_by   = relationship("User", foreign_keys=[queued_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        Index("ix_pq_company_status", "company_id", "status"),
        Index("ix_pq_queued_at",      "queued_at"),
    )
