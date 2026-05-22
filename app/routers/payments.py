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
from app.models.payment_log import PaymentLog
from app.utils.dependencies import require_permission

router = APIRouter(prefix="/payments", tags=["payments"])

PEIBO_BASE = os.getenv("PEIBO_BASE_URL", "https://qa.peibo-api.lab-peibo.com")


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

def _build_signature(payload_str: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _log(db: Session, event_type: str, company_id: int, payload: dict):
    db.add(PaymentLog(event_type=event_type, company_id=company_id, payload=payload))
    db.commit()


# ── Endpoints ──────────────────────────────────────────────────────────────────

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
        raise HTTPException(
            status_code=422,
            detail="La compañía no tiene credenciales Peibo configuradas",
        )

    transaction_id = uuid.uuid4().hex[:32].upper()
    reference      = str(random.randint(1000000, 9999999))
    date_time      = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    peibo_payload = {
        "transaction_id":           transaction_id,
        "date_time":                date_time,
        "concept":                  body.concept,
        "reference":                reference,
        "amount":                   body.amount,
        "beneficiary_account":      body.beneficiary_account,
        "beneficiary_name":         body.beneficiary_name,
        "beneficiary_bank":         body.beneficiary_bank,
        "beneficiary_account_type": body.beneficiary_account_type,
        "beneficiary_tax_id":       body.beneficiary_tax_id,
        "latitude":                 body.latitude,
        "longitude":                body.longitude,
    }

    # Serializar exactamente igual que se va a enviar (sin espacios extra)
    payload_str = json.dumps(peibo_payload, separators=(",", ":"), ensure_ascii=False)
    signature   = _build_signature(payload_str, company.peibo_api_key)

    headers = {
        "Content-Type":    "application/json",
        "X-MSG-SIGNATURE": signature,
        "X-CUSTOMER-KEY":  company.peibo_customer_key,
    }

    try:
        resp = http_requests.post(
            f"{PEIBO_BASE}/latest/order/transfer",
            data=payload_str.encode("utf-8"),
            headers=headers,
            timeout=30,
        )
    except http_requests.RequestException as exc:
        _log(db, "payment_error", body.company_id, {"error": str(exc), "request": peibo_payload})
        raise HTTPException(status_code=502, detail=f"Error de conexión con Peibo: {exc}")

    try:
        peibo_response = resp.json()
    except Exception:
        peibo_response = {"raw": resp.text}

    log_payload = {
        "http_status":   resp.status_code,
        "request":       peibo_payload,
        "response":      peibo_response,
    }

    if resp.status_code == 401:
        _log(db, "payment_error", body.company_id, log_payload)
        raise HTTPException(status_code=502, detail="Firma inválida o IP no autorizada por Peibo")

    if peibo_response.get("status") == "error":
        _log(db, "payment_error", body.company_id, log_payload)
        raise HTTPException(
            status_code=400,
            detail=peibo_response.get("error_message", "Error desconocido de Peibo"),
        )

    _log(db, "payment_initiated", body.company_id, log_payload)
    return peibo_response


def _send_peibo_transfer(company: Company, peibo_payload: dict) -> dict:
    payload_str = json.dumps(peibo_payload, separators=(",", ":"), ensure_ascii=False)
    signature   = _build_signature(payload_str, company.peibo_api_key)
    headers = {
        "Content-Type":    "application/json",
        "X-MSG-SIGNATURE": signature,
        "X-CUSTOMER-KEY":  company.peibo_customer_key,
    }
    try:
        resp = http_requests.post(
            f"{PEIBO_BASE}/latest/order/transfer",
            data=payload_str.encode("utf-8"),
            headers=headers,
            timeout=30,
        )
    except http_requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Error de conexión con Peibo: {exc}")

    try:
        peibo_response = resp.json()
    except Exception:
        peibo_response = {"raw": resp.text}

    return resp.status_code, peibo_response


@router.post("/transfer/driver/{driver_id}")
def pay_driver(
    driver_id:  int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    row = db.query(DriverAccount).filter(
        DriverAccount.driver_id  == driver_id,
        DriverAccount.company_id == company_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")
    if row.payment_status == "success":
        raise HTTPException(status_code=400, detail="Este conductor ya fue pagado")

    amount = row.process_balance_before
    if not amount or float(amount) <= 0:
        raise HTTPException(status_code=400, detail="Sin saldo verificado para pagar")

    company = db.get(Company, company_id)
    if not company or not company.peibo_api_key or not company.peibo_customer_key:
        raise HTTPException(status_code=422, detail="La compañía no tiene credenciales Peibo configuradas")

    # Buscar banco SPEI por nombre (búsqueda parcial case-insensitive)
    bank_name = (row.bank_name or "").strip()
    bank = db.query(Bank).filter(
        func.lower(Bank.name).like(f"%{bank_name.lower()}%")
    ).first()
    if not bank:
        raise HTTPException(
            status_code=422,
            detail=f"No se encontró banco SPEI para '{bank_name}'. Verifica el catálogo de bancos.",
        )

    # Determinar tipo de cuenta por longitud
    account = (row.bank_sort_code or "").strip()
    if len(account) == 18:
        account_type = "CLABE"
    elif len(account) == 16:
        account_type = "TDD"
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Tipo de cuenta no reconocido (longitud: {len(account)})",
        )

    beneficiary_name = f"{row.forename or ''} {row.surname or ''}".strip()[:40]

    peibo_payload = {
        "transaction_id":           uuid.uuid4().hex[:32].upper(),
        "date_time":                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "concept":                  "bookings",
        "reference":                str(random.randint(1000000, 9999999)),
        "amount":                   f"{float(amount):.2f}",
        "beneficiary_account":      account,
        "beneficiary_name":         beneficiary_name,
        "beneficiary_bank":         bank.code,
        "beneficiary_account_type": account_type,
        "latitude":                 "19.388113",
        "longitude":                "-99.252684",
    }

    http_status, peibo_response = _send_peibo_transfer(company, peibo_payload)

    log_payload = {
        "http_status": http_status,
        "driver_id":   driver_id,
        "request":     peibo_payload,
        "response":    peibo_response,
    }

    if http_status == 401:
        _log(db, "payment_error", company_id, log_payload)
        raise HTTPException(status_code=502, detail="Firma inválida o IP no autorizada por Peibo")

    if peibo_response.get("status") == "error":
        _log(db, "payment_error", company_id, log_payload)
        raise HTTPException(
            status_code=400,
            detail=peibo_response.get("error_message", "Error desconocido de Peibo"),
        )

    now = datetime.now(timezone.utc)
    row.payment_status       = "pending"
    row.peibo_transaction_id = peibo_response.get("transaction_id")
    row.peibo_tracking_code  = peibo_response.get("tracking_code")
    row.peibo_paid_at        = now

    # Sincronizar en historial si existe el registro de esta sesión
    if row.session_id:
        hist = db.query(DriverAccountHistory).filter(
            DriverAccountHistory.driver_id  == driver_id,
            DriverAccountHistory.company_id == company_id,
            DriverAccountHistory.session_id == row.session_id,
        ).first()
        if hist:
            hist.payment_status       = "pending"
            hist.peibo_transaction_id = row.peibo_transaction_id
            hist.peibo_tracking_code  = row.peibo_tracking_code
            hist.peibo_paid_at        = now

    db.commit()
    _log(db, "payment_initiated", company_id, log_payload)

    return {
        "status":         "success",
        "transaction_id": row.peibo_transaction_id,
        "tracking_code":  row.peibo_tracking_code,
        "driver_id":      driver_id,
        "amount":         peibo_payload["amount"],
        "beneficiary":    beneficiary_name,
    }
