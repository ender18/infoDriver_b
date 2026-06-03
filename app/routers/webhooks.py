from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.peibo_transaction import PeiboTransaction
from app.models.peibo_webhook_event import PeiboWebhookEvent
from app.models.payment_log import PaymentLog

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Mapeo de status PEIBO → nuestro status interno
_STATUS_MAP = {
    "Liquidada":  "success",
    "Devuelta":   "refunded",
    "Rechazada":  "failed",
}


def _log(db: Session, event_type: str, company_id=None, driver_id=None,
         session_id=None, history_id=None, peibo_transaction_id=None, payload=None):
    db.add(PaymentLog(
        event_type=event_type,
        company_id=company_id,
        driver_id=driver_id,
        session_id=session_id,
        history_id=history_id,
        peibo_transaction_id=peibo_transaction_id,
        payload=payload,
    ))
    db.commit()


def _parse_event(payload: dict) -> PeiboWebhookEvent:
    return PeiboWebhookEvent(
        tracking_code       = payload.get("tracking_code"),
        status              = payload.get("status"),
        type                = payload.get("type"),
        concept             = payload.get("concept"),
        reference           = payload.get("reference"),
        amount              = float(payload.get("amount") or 0) or None,
        date_time           = payload.get("date_time"),
        refund_reason_code  = payload.get("refund_reason_code"),
        beneficiary_account = payload.get("beneficiary_account"),
        originator_account  = payload.get("originator_account"),
        originator_bank     = payload.get("originator_bank"),
        originator_name     = payload.get("originator_name"),
        originator_tax_id   = payload.get("originator_tax_id"),
        raw_payload         = payload,
        received_at         = datetime.now(timezone.utc),
    )


@router.post("/peibo")
def peibo_webhook(payload: dict, db: Session = Depends(get_db)):
    """
    Webhook universal de PEIBO.
    Siempre responde 200 — PEIBO no reintenta.
    Busca la transacción por tracking_code, actualiza su estado
    y guarda el evento crudo en peibo_webhook_events.
    """
    tracking_code = payload.get("tracking_code")

    if not tracking_code:
        _log(db, "webhook_error", payload={"reason": "missing tracking_code", **payload})
        return {"ok": True}

    tx = db.query(PeiboTransaction).filter(
        PeiboTransaction.tracking_code == tracking_code
    ).first()

    event = _parse_event(payload)

    if not tx:
        # Guardamos el evento huérfano para no perder nada
        db.add(event)
        db.commit()
        _log(db, "webhook_error", payload={"reason": "tracking_code not found", **payload})
        return {"ok": True}

    # Actualizar estado de la transacción
    new_status = _STATUS_MAP.get(payload.get("status"), tx.status)
    tx.status = new_status
    if new_status == "success" and not tx.paid_at:
        tx.paid_at = datetime.now(timezone.utc)

    event.peibo_transaction_id = tx.id
    db.add(event)
    db.commit()

    _log(db, "webhook_received",
         company_id=tx.company_id,
         peibo_transaction_id=tx.id,
         payload=payload)

    return {"ok": True}
