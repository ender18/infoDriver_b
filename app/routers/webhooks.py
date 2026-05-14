from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.driver_account import DriverAccount
from app.models.driver_account_history import DriverAccountHistory
from app.models.payment_log import PaymentLog

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _log(db: Session, event_type: str, company_id=None, driver_id=None,
         session_id=None, history_id=None, payload=None):
    db.add(PaymentLog(
        event_type=event_type,
        company_id=company_id,
        driver_id=driver_id,
        session_id=session_id,
        history_id=history_id,
        payload=payload,
    ))
    db.commit()


def _apply_webhook_fields(row, payload: dict):
    row.webhook_status              = payload.get("status")
    row.webhook_transaction_id      = payload.get("transaction_id")
    row.webhook_date_time           = payload.get("date_time")
    row.webhook_concept             = payload.get("concept")
    row.webhook_reference           = payload.get("reference")
    row.webhook_amount              = float(payload.get("amount") or 0)
    row.webhook_beneficiary_account = payload.get("beneficiary_account")
    row.webhook_originator_account  = payload.get("originator_account")
    row.webhook_originator_bank     = payload.get("originator_bank")
    row.webhook_originator_name     = payload.get("originator_name")
    row.webhook_originator_tax_id   = payload.get("originator_tax_id")
    row.webhook_type                = payload.get("type")
    row.webhook_refund_reason_code  = payload.get("refund_reason_code")
    row.webhook_received_at         = datetime.now(timezone.utc)
    if payload.get("status") == "Liquidada":
        row.payment_status = "success"


@router.post("/peibo")
def peibo_webhook(payload: dict, db: Session = Depends(get_db)):
    """
    Recibe la confirmación de liquidación de Peibo.
    Siempre responde 200 — Peibo no reintenta.
    Identifica el registro por tracking_code y actualiza ambas tablas.
    """
    tracking_code = payload.get("tracking_code")

    if not tracking_code:
        _log(db, "webhook_error", payload={"reason": "missing tracking_code", **payload})
        return {"ok": True}

    work_row = (
        db.query(DriverAccount)
        .filter(DriverAccount.peibo_tracking_code == tracking_code)
        .first()
    )

    hist_row = (
        db.query(DriverAccountHistory)
        .filter(DriverAccountHistory.peibo_tracking_code == tracking_code)
        .order_by(DriverAccountHistory.fetched_at.desc())
        .first()
    )

    if not work_row and not hist_row:
        _log(db, "webhook_error",
             payload={"reason": "tracking_code not found", **payload})
        return {"ok": True}

    if work_row:
        _apply_webhook_fields(work_row, payload)
    if hist_row:
        _apply_webhook_fields(hist_row, payload)

    db.commit()

    ref = hist_row or work_row
    _log(db, "webhook_received",
         company_id=ref.company_id,
         driver_id=ref.driver_id,
         session_id=getattr(ref, "session_id", None),
         history_id=hist_row.id if hist_row else None,
         payload=payload)

    return {"ok": True}
