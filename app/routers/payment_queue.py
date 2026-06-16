import uuid
import random
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.bank import Bank
from app.models.company import Company
from app.models.payment_queue import PaymentQueue
from app.models.peibo_transaction import PeiboTransaction
from app.services.peibo import send_transfer
from app.utils.dependencies import require_permission

router = APIRouter(prefix="/payment-queue", tags=["payment-queue"])

VALID_SOURCES = {
    "driver_balance", "referral_bonus", "daily_bonus",
    "first_trips_bonus", "spei_transfer", "individual",
}
VALID_STATUSES = {"pending", "approved", "rejected", "discarded", "paid"}


# ── Schemas ────────────────────────────────────────────────────────────

class EnqueueItem(BaseModel):
    source:         str
    driver_id:      Optional[int]   = None
    callsign:       Optional[str]   = None
    forename:       Optional[str]   = None
    surname:        Optional[str]   = None
    bank_name:      Optional[str]   = None
    bank_sort_code: Optional[str]   = None
    amount:         float
    notes:          Optional[str]   = None
    source_ref:     Optional[str]   = None

class ApproveBody(BaseModel):
    adjusted_amount: Optional[float] = None

class RejectBody(BaseModel):
    rejection_reason: Optional[str] = None

class BulkApproveBody(BaseModel):
    ids:             list[int]
    adjusted_amount: Optional[float] = None   # aplica igual a todos si se indica


# ── Helpers ────────────────────────────────────────────────────────────

def _get_company(company_id: int, db: Session) -> Company:
    c = db.query(Company).filter(Company.id == company_id, Company.is_active == True).first()
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    return c

def _row(pq: PaymentQueue) -> dict:
    return {
        "id":                   pq.id,
        "company_id":           pq.company_id,
        "source":               pq.source,
        "driver_id":            pq.driver_id,
        "callsign":             pq.callsign,
        "forename":             pq.forename,
        "surname":              pq.surname,
        "full_name":            f"{pq.forename or ''} {pq.surname or ''}".strip(),
        "bank_name":            pq.bank_name,
        "bank_sort_code":       pq.bank_sort_code,
        "amount":               pq.amount,
        "adjusted_amount":      pq.adjusted_amount,
        "effective_amount":     pq.adjusted_amount if pq.adjusted_amount is not None else pq.amount,
        "notes":                pq.notes,
        "source_ref":           pq.source_ref,
        "status":               pq.status,
        "rejection_reason":     pq.rejection_reason,
        "queued_by":            pq.queued_by.email  if pq.queued_by   else None,
        "queued_at":            pq.queued_at.isoformat() if pq.queued_at else None,
        "reviewed_by":          pq.reviewed_by.email if pq.reviewed_by else None,
        "reviewed_at":          pq.reviewed_at.isoformat() if pq.reviewed_at else None,
        "peibo_transaction_id": pq.peibo_transaction_id,
    }


SOURCE_CONCEPT = {
    "driver_balance":    "bookings",
    "referral_bonus":    "bono referido",
    "daily_bonus":       "bono diario",
    "first_trips_bonus": "bono primeros viajes",
    "spei_transfer":     "transferencia spei",
    "individual":        "pago individual",
}


def _execute_payment(pq: PaymentQueue, company: Company, user_id: int, db: Session) -> PeiboTransaction:
    """Ejecuta el pago Peibo para una entrada de la cola y devuelve la PeiboTransaction creada."""
    if not company.peibo_api_key or not company.peibo_customer_key:
        raise HTTPException(status_code=422, detail="La compañía no tiene credenciales Peibo configuradas")

    bank_name = (pq.bank_name or "").strip()
    bank = db.query(Bank).filter(func.lower(Bank.name).like(f"%{bank_name.lower()}%")).first()
    if not bank:
        raise HTTPException(status_code=422,
                            detail=f"Banco no encontrado en catálogo: '{bank_name}'")

    account = (pq.bank_sort_code or "").strip()
    if len(account) == 18:
        account_type = "CLABE"
    elif len(account) == 16:
        account_type = "TDD"
    else:
        raise HTTPException(status_code=422,
                            detail=f"Longitud de cuenta inválida: {len(account)}")

    effective_amount = pq.adjusted_amount if pq.adjusted_amount is not None else pq.amount
    beneficiary_name = f"{pq.forename or ''} {pq.surname or ''}".strip()[:40]
    concept          = SOURCE_CONCEPT.get(pq.source, "pago")[:40]

    peibo_payload = {
        "transaction_id":           uuid.uuid4().hex[:32].upper(),
        "date_time":                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "concept":                  concept,
        "reference":                str(random.randint(1000000, 9999999)),
        "amount":                   f"{float(effective_amount):.2f}",
        "beneficiary_account":      account,
        "beneficiary_name":         beneficiary_name,
        "beneficiary_bank":         bank.code,
        "beneficiary_account_type": account_type,
        "latitude":                 "19.388113",
        "longitude":                "-99.252684",
    }

    http_status, peibo_response = send_transfer(company, peibo_payload)

    if http_status == 401:
        raise HTTPException(status_code=502, detail="Firma inválida o IP no autorizada por Peibo")
    if peibo_response.get("status") == "error":
        raise HTTPException(status_code=400,
                            detail=peibo_response.get("error_message", "Error desconocido de Peibo"))

    tx = PeiboTransaction(
        tracking_code    = peibo_response.get("tracking_code"),
        transaction_id   = peibo_response.get("transaction_id") or peibo_payload["transaction_id"],
        status           = "pending",
        amount           = peibo_payload["amount"],
        original_amount  = pq.amount,
        callsign         = pq.callsign,
        beneficiary_name = beneficiary_name,
        company_id       = pq.company_id,
        source_type      = "payment_queue",
        source_id        = pq.id,
        created_by       = user_id,
    )
    db.add(tx)
    db.flush()

    pq.status               = "paid"
    pq.peibo_transaction_id = tx.id
    pq.reviewed_by_id       = user_id
    pq.reviewed_at          = datetime.now(timezone.utc)

    return tx


# ── Endpoints ──────────────────────────────────────────────────────────

@router.post("/enqueue", status_code=status.HTTP_201_CREATED)
def enqueue(
    company_id: int = Query(...),
    items:      list[EnqueueItem] = ...,
    db:         Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    """Encola uno o varios pagos desde cualquier módulo."""
    _get_company(company_id, db)

    for item in items:
        if item.source not in VALID_SOURCES:
            raise HTTPException(status_code=422, detail=f"Fuente inválida: {item.source}")
        if item.amount <= 0:
            raise HTTPException(status_code=422, detail="El monto debe ser mayor a 0")

    created = []
    for item in items:
        pq = PaymentQueue(
            company_id    = company_id,
            queued_by_id  = current_user.id,
            **item.model_dump(),
        )
        db.add(pq)
        created.append(pq)

    db.commit()
    for pq in created:
        db.refresh(pq)

    return {"enqueued": len(created), "ids": [pq.id for pq in created]}


@router.get("/")
def list_queue(
    company_id: int           = Query(...),
    status_filter: Optional[str]  = Query(None, alias="status"),
    source:     Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:    Optional[str] = Query(None, description="YYYY-MM-DD"),
    db:         Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    _get_company(company_id, db)

    q = db.query(PaymentQueue).filter(PaymentQueue.company_id == company_id)

    if status_filter:
        q = q.filter(PaymentQueue.status == status_filter)
    if source:
        q = q.filter(PaymentQueue.source == source)
    if date_from:
        q = q.filter(PaymentQueue.queued_at >= date_from)
    if date_to:
        q = q.filter(PaymentQueue.queued_at <= f"{date_to} 23:59:59")

    rows = q.order_by(PaymentQueue.queued_at.desc()).all()

    total_effective = sum(
        (r.adjusted_amount if r.adjusted_amount is not None else r.amount)
        for r in rows
    )

    return {
        "total":            len(rows),
        "total_amount":     total_effective,
        "items":            [_row(r) for r in rows],
    }


@router.patch("/{pq_id}/approve")
def approve(
    pq_id:  int,
    body:   ApproveBody = ApproveBody(),
    db:     Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    pq = db.get(PaymentQueue, pq_id)
    if not pq:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pq.status not in ("pending", "rejected"):
        raise HTTPException(status_code=422, detail=f"No se puede aprobar un pago en estado '{pq.status}'")

    if body.adjusted_amount is not None:
        pq.adjusted_amount = body.adjusted_amount
    pq.rejection_reason = None

    company = db.get(Company, pq.company_id)
    tx = _execute_payment(pq, company, current_user.id, db)
    db.commit()
    db.refresh(pq)

    return {**_row(pq), "peibo_transaction_id": tx.id, "tracking_code": tx.tracking_code}


@router.patch("/{pq_id}/reject")
def reject(
    pq_id: int,
    body:  RejectBody = RejectBody(),
    db:    Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    pq = db.get(PaymentQueue, pq_id)
    if not pq:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pq.status != "pending":
        raise HTTPException(status_code=422, detail=f"No se puede rechazar un pago en estado '{pq.status}'")

    pq.status           = "rejected"
    pq.rejection_reason = body.rejection_reason
    pq.reviewed_by_id   = current_user.id
    pq.reviewed_at      = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pq)
    return _row(pq)


@router.patch("/{pq_id}/discard")
def discard(
    pq_id: int,
    db:    Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    pq = db.get(PaymentQueue, pq_id)
    if not pq:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pq.status != "rejected":
        raise HTTPException(status_code=422, detail="Solo se pueden descartar pagos rechazados")

    pq.status         = "discarded"
    pq.reviewed_by_id = current_user.id
    pq.reviewed_at    = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pq)
    return _row(pq)


@router.post("/bulk-approve")
def bulk_approve(
    company_id: int = Query(...),
    body:       BulkApproveBody = ...,
    db:         Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    if not body.ids:
        raise HTTPException(status_code=422, detail="Lista de IDs vacía")

    rows = db.query(PaymentQueue).filter(
        PaymentQueue.id.in_(body.ids),
        PaymentQueue.company_id == company_id,
        PaymentQueue.status.in_(("pending", "rejected")),
    ).all()

    company = db.get(Company, company_id)
    paid, errors = [], []

    for pq in rows:
        if body.adjusted_amount is not None:
            pq.adjusted_amount = body.adjusted_amount
        pq.rejection_reason = None
        try:
            tx = _execute_payment(pq, company, current_user.id, db)
            db.commit()
            paid.append({"id": pq.id, "tracking_code": tx.tracking_code})
        except HTTPException as e:
            db.rollback()
            errors.append({"id": pq.id, "error": e.detail})

    return {
        "paid":   len(paid),
        "errors": len(errors),
        "results": paid,
        "failed":  errors,
    }
