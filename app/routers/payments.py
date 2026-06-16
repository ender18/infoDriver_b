import hmac
import hashlib
import json
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
import requests as http_requests

from app.database import get_db
from app.models.bank import Bank
from app.models.company import Company
from app.models.driver_account import DriverAccount
from app.models.driver_account_history import DriverAccountHistory
from app.models.payment_queue import PaymentQueue
from app.models.peibo_transaction import PeiboTransaction
from app.models.peibo_webhook_event import PeiboWebhookEvent
from app.models.payment_log import PaymentLog
from app.utils.dependencies import require_permission
from app.services.peibo import send_transfer as _send_peibo_transfer

router = APIRouter(prefix="/payments", tags=["payments"])

PEIBO_BASE = os.getenv("PEIBO_BASE_URL")
if not PEIBO_BASE:
    raise RuntimeError("La variable de entorno PEIBO_BASE_URL no está configurada")


# ── Schemas ────────────────────────────────────────────────────────────────────

class TransferRequest(BaseModel):
    company_id:               int
    concept:                  str   = Field(..., max_length=40)
    amount:                   str   = Field(..., description="Decimal como string, ej: '1500.00'")
    beneficiary_account:      str   = Field(..., min_length=10, max_length=18)
    beneficiary_name:         str   = Field(..., max_length=40)
    beneficiary_bank:         str   = Field(..., max_length=5)
    beneficiary_account_type: str   = Field(..., pattern="^(CLABE|TDD|CELULAR)$")
    beneficiary_tax_id:       Optional[str] = Field(None, min_length=12, max_length=13)
    latitude:                 str   = Field("19.388113")
    longitude:                str   = Field("-99.252684")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _log(db: Session, event_type: str, company_id: int, payload: dict,
         driver_id: int = None, session_id: str = None,
         history_id: int = None, peibo_transaction_id: int = None):
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


def _tx_dict(tx: PeiboTransaction, events: list[PeiboWebhookEvent]) -> dict:
    return {
        "id":               tx.id,
        "tracking_code":    tx.tracking_code,
        "transaction_id":   tx.transaction_id,
        "status":           tx.status,
        "amount":           float(tx.amount)          if tx.amount          is not None else None,
        "original_amount":  float(tx.original_amount) if tx.original_amount is not None else None,
        "callsign":         tx.callsign,
        "beneficiary_name": tx.beneficiary_name,
        "company_id":       tx.company_id,
        "source_type":      tx.source_type,
        "source_id":        tx.source_id,
        "created_by":       tx.created_by,
        "error_message":    tx.error_message,
        "paid_at":          tx.paid_at.isoformat()    if tx.paid_at    else None,
        "created_at":       tx.created_at.isoformat() if tx.created_at else None,
        "updated_at":       tx.updated_at.isoformat() if tx.updated_at else None,
        "webhook_events":   [_event_dict(e) for e in events],
    }


def _event_dict(e: PeiboWebhookEvent) -> dict:
    return {
        "id":                   e.id,
        "status":               e.status,
        "type":                 e.type,
        "concept":              e.concept,
        "reference":            e.reference,
        "amount":               float(e.amount) if e.amount is not None else None,
        "beneficiary_account":  e.beneficiary_account,
        "originator_account":   e.originator_account,
        "originator_bank":      e.originator_bank,
        "originator_name":      e.originator_name,
        "originator_tax_id":    e.originator_tax_id,
        "date_time":            e.date_time.isoformat()    if e.date_time    else None,
        "received_at":          e.received_at.isoformat()  if e.received_at  else None,
        "refund_reason_code":   e.refund_reason_code,
    }


# ── Transferencia manual ─────────────────────────────────────────────���─────────

@router.post("/transfer")
def create_transfer(
    body: TransferRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    company = db.get(Company, body.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Compañía no encontrada")
    if not company.peibo_api_key or not company.peibo_customer_key:
        raise HTTPException(status_code=422, detail="La compañía no tiene credenciales Peibo configuradas")

    transaction_id = uuid.uuid4().hex[:32].upper()
    peibo_payload = {
        "transaction_id":           transaction_id,
        "date_time":                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "concept":                  body.concept,
        "reference":                str(random.randint(1000000, 9999999)),
        "amount":                   body.amount,
        "beneficiary_account":      body.beneficiary_account,
        "beneficiary_name":         body.beneficiary_name,
        "beneficiary_bank":         body.beneficiary_bank,
        "beneficiary_account_type": body.beneficiary_account_type,
        "beneficiary_tax_id":       body.beneficiary_tax_id,
        "latitude":                 body.latitude,
        "longitude":                body.longitude,
    }

    http_status, peibo_response = _send_peibo_transfer(company, peibo_payload)

    log_payload = {"http_status": http_status, "request": peibo_payload, "response": peibo_response}

    if http_status == 401:
        _log(db, "payment_error", body.company_id, log_payload)
        raise HTTPException(status_code=502, detail="Firma inválida o IP no autorizada por Peibo")

    if peibo_response.get("status") == "error":
        _log(db, "payment_error", body.company_id, log_payload)
        raise HTTPException(status_code=400,
                            detail=peibo_response.get("error_message", "Error desconocido de Peibo"))

    tx = PeiboTransaction(
        tracking_code  = peibo_response.get("tracking_code"),
        transaction_id = peibo_response.get("transaction_id") or transaction_id,
        status         = "pending",
        amount         = body.amount,
        company_id     = body.company_id,
        source_type    = "manual",
        source_id      = current_user.id,
        created_by     = current_user.id,
    )
    db.add(tx)
    db.flush()
    _log(db, "payment_initiated", body.company_id, log_payload, peibo_transaction_id=tx.id)
    db.commit()
    return peibo_response


# ── Pago a conductor ───────────────────────────────────────────────────────────

@router.post("/transfer/driver/{driver_id}")
def enqueue_driver_payment(
    driver_id:  int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    """Encola el pago del saldo de un conductor para aprobación (ya no paga directo)."""
    row = db.query(DriverAccount).filter(
        DriverAccount.driver_id  == driver_id,
        DriverAccount.company_id == company_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")

    # Verificar que no tenga ya un pago pendiente/aprobado en la cola
    existing = db.query(PaymentQueue).filter(
        PaymentQueue.driver_id   == driver_id,
        PaymentQueue.company_id  == company_id,
        PaymentQueue.source      == "driver_balance",
        PaymentQueue.status.in_(("pending", "approved")),
    ).first()
    if existing:
        raise HTTPException(status_code=400,
                            detail=f"Este conductor ya tiene un pago en cola (id={existing.id}, estado={existing.status})")

    amount = row.process_balance_before
    if not amount or float(amount) <= 0:
        raise HTTPException(status_code=400, detail="Sin saldo verificado para encolar")

    # Validar banco antes de encolar para detectar errores temprano
    bank_name = (row.bank_name or "").strip()
    bank = db.query(Bank).filter(func.lower(Bank.name).like(f"%{bank_name.lower()}%")).first()
    if not bank:
        raise HTTPException(status_code=422,
                            detail=f"No se encontró banco SPEI para '{bank_name}'. Verifica el catálogo de bancos.")

    account = (row.bank_sort_code or "").strip()
    if len(account) not in (16, 18):
        raise HTTPException(status_code=422,
                            detail=f"Tipo de cuenta no reconocido (longitud: {len(account)})")

    pq = PaymentQueue(
        company_id     = company_id,
        source         = "driver_balance",
        driver_id      = row.driver_id,
        callsign       = row.callsign,
        forename       = row.forename,
        surname        = row.surname,
        bank_name      = row.bank_name,
        bank_sort_code = row.bank_sort_code,
        amount         = float(amount),
        notes          = f"Saldo de conductores",
        source_ref     = row.session_id,
        queued_by_id   = current_user.id,
    )
    db.add(pq)
    db.commit()
    db.refresh(pq)

    _log(db, "payment_enqueued", company_id,
         {"queue_id": pq.id, "driver_id": driver_id, "amount": float(amount)},
         driver_id=driver_id, session_id=row.session_id)

    return {
        "status":    "enqueued",
        "queue_id":  pq.id,
        "driver_id": driver_id,
        "amount":    float(amount),
        "message":   "Pago enviado a la cola de aprobación",
    }


# ── Auditoría de transacciones ─────────────────────────────────────────────────

@router.get("/transactions")
def list_transactions(
    company_id:  int = Query(...),
    status:      Optional[str] = Query(None, description="pending | success | failed | refunded"),
    source_type: Optional[str] = Query(None, description="driver_payment | manual"),
    limit:       int = Query(50, le=500),
    offset:      int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    q = db.query(PeiboTransaction).filter(PeiboTransaction.company_id == company_id)
    if status:
        q = q.filter(PeiboTransaction.status == status)
    if source_type:
        q = q.filter(PeiboTransaction.source_type == source_type)

    total = q.count()
    txs   = q.order_by(PeiboTransaction.created_at.desc()).offset(offset).limit(limit).all()

    tx_ids = [t.id for t in txs]
    events_by_tx: dict[int, list] = {t.id: [] for t in txs}
    if tx_ids:
        for e in db.query(PeiboWebhookEvent).filter(
            PeiboWebhookEvent.peibo_transaction_id.in_(tx_ids)
        ).order_by(PeiboWebhookEvent.received_at.asc()).all():
            events_by_tx[e.peibo_transaction_id].append(e)

    return {
        "total":  total,
        "offset": offset,
        "limit":  limit,
        "results": [_tx_dict(t, events_by_tx[t.id]) for t in txs],
    }


@router.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    tx = db.get(PeiboTransaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    events = (
        db.query(PeiboWebhookEvent)
        .filter(PeiboWebhookEvent.peibo_transaction_id == transaction_id)
        .order_by(PeiboWebhookEvent.received_at.asc())
        .all()
    )
    return _tx_dict(tx, events)


@router.get("/transactions/{transaction_id}/log")
def get_transaction_log(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    tx = db.get(PeiboTransaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    entries = (
        db.query(PaymentLog)
        .filter(PaymentLog.peibo_transaction_id == transaction_id)
        .order_by(PaymentLog.created_at.asc())
        .all()
    )
    return [
        {
            "id":         e.id,
            "event_type": e.event_type,
            "driver_id":  e.driver_id,
            "session_id": e.session_id,
            "history_id": e.history_id,
            "payload":    e.payload,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]
