from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import requests as http_requests
import math
import json

from app.database import get_db
from app.models.company import Company
from app.models.driver_account import DriverAccount
from app.utils.dependencies import require_permission
from app.services.tools import drivers_client
from app.services.tools import (
    authorization_validator,
    curp_validator,
    email_validator,
    name_validator,
    phone_validator,
    city_validator,
)

ACCOUNTS_BASE  = "https://autocab-api.azure-api.net/accounts/v1"
ACCOUNTS_URL   = f"{ACCOUNTS_BASE}/DriversAccounts"
PROCESS_URL    = f"{ACCOUNTS_BASE}/ProcessDriverAccount"
PAGE_SIZE      = 50

router = APIRouter(prefix="/tools", tags=["tools"])

VALIDATORS = [
    authorization_validator,
    email_validator,
    curp_validator,
    name_validator,
    phone_validator,
    city_validator,
]


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _autocab_headers(subscription_key: str) -> dict:
    return {
        "User-Agent": "python-requests",
        "Accept": "*/*",
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/json",
    }


def _fetch_accounts_page(subscription_key: str, page: int, driver_id: int | None = None) -> dict:
    resp = http_requests.post(
        ACCOUNTS_URL,
        params={"pageno": page, "pagesize": PAGE_SIZE},
        headers=_autocab_headers(subscription_key),
        json={"companyId": None, "driverId": driver_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _row_to_dict(row: DriverAccount) -> dict:
    return {
        "id":                     row.id,
        "driver_id":              row.driver_id,
        "callsign":               row.callsign,
        "forename":               row.forename,
        "surname":                row.surname,
        "bank_name":              row.bank_name,
        "bank_sort_code":         row.bank_sort_code,
        "current_balance":        row.current_balance,
        "outstanding_amount":     row.outstanding_amount,
        "all_jobs_total":         row.all_jobs_total,
        "all_jobs_commission":    row.all_jobs_commission,
        "notes":                  row.notes,
        "fetched_at":             row.fetched_at.isoformat() if row.fetched_at else None,
        "process_status":         row.process_status,
        "process_result":         row.process_result,
        "process_balance_before": row.process_balance_before,
        "processed_at":           row.processed_at.isoformat() if row.processed_at else None,
    }


# ──────────────────────────────────────────────
# Validation endpoint (original)
# ──────────────────────────────────────────────

@router.get("/drivers/validate")
def validate_drivers(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    try:
        data = drivers_client.fetch_all(company.api_subscription_key)
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="No se pudo conectar a la API externa")
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Tiempo de espera agotado al conectar con la API externa")
    except http_requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error de la API externa: {e}")

    drivers        = data["drivers"]
    authorizations = data["authorizations"]

    all_results = []
    for validator in VALIDATORS:
        all_results.extend(validator.run(drivers, authorizations))

    return {
        "company":       {"id": company.id, "name": company.name},
        "total_drivers": len(drivers),
        "total_errors":  len(all_results),
        "results":       all_results,
    }


# ──────────────────────────────────────────────
# Driver accounts — leer desde BD
# ──────────────────────────────────────────────

@router.get("/drivers/accounts")
def get_driver_accounts(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    """Devuelve los registros guardados en BD para la compañía."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    rows = (
        db.query(DriverAccount)
        .filter(DriverAccount.company_id == company_id)
        .order_by(DriverAccount.current_balance.desc())
        .all()
    )

    return {
        "company":              {"id": company.id, "name": company.name},
        "drivers_with_balance": len(rows),
        "fetched_at":           rows[0].fetched_at.isoformat() if rows else None,
        "results":              [_row_to_dict(r) for r in rows],
    }


# ──────────────────────────────────────────────
# Driver accounts — refrescar desde API externa (SSE)
# ──────────────────────────────────────────────

@router.get("/drivers/accounts/refresh")
def refresh_driver_accounts(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    """
    Consulta la API externa página a página, reemplaza los datos en BD
    y emite eventos SSE con el progreso en tiempo real.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    sub_key      = company.api_subscription_key
    company_info = {"id": company.id, "name": company.name}

    def generate():
        # — Cargar lista de conductores para cruzar bank/callsign —
        try:
            drivers_data = drivers_client.fetch_all(sub_key)
            driver_map = {d["id"]: d for d in drivers_data["drivers"]}
        except Exception:
            driver_map = {}   # si falla, seguimos sin datos de banco

        # — Primera página para conocer el total —
        try:
            first_data = _fetch_accounts_page(sub_key, 1)
        except http_requests.exceptions.ConnectionError:
            yield _sse({"type": "error", "code": 502, "detail": "No se pudo conectar a la API externa"})
            return
        except http_requests.exceptions.Timeout:
            yield _sse({"type": "error", "code": 504, "detail": "Tiempo de espera agotado"})
            return
        except http_requests.exceptions.HTTPError as e:
            yield _sse({"type": "error", "code": 502, "detail": str(e)})
            return

        total       = first_data.get("totalSummariesCount", 0)
        total_pages = math.ceil(total / PAGE_SIZE) if total else 1

        # Borrar registros anteriores de esta compañía
        db.query(DriverAccount).filter(DriverAccount.company_id == company_id).delete()
        db.commit()

        yield _sse({"type": "init", "total": total, "total_pages": total_pages, "company": company_info})

        # — Procesar páginas —
        for page_num in range(1, total_pages + 1):
            if page_num == 1:
                raw = first_data
            else:
                try:
                    raw = _fetch_accounts_page(sub_key, page_num)
                except (http_requests.exceptions.ConnectionError,
                        http_requests.exceptions.Timeout,
                        http_requests.exceptions.HTTPError) as e:
                    yield _sse({"type": "error", "code": 502, "detail": str(e)})
                    return

            with_balance = [d for d in raw.get("summaries", []) if (d.get("currentBalance") or 0) > 0]

            for d in with_balance:
                drv       = driver_map.get(d.get("driverId"), {})
                new_row   = DriverAccount(
                    company_id          = company_id,
                    driver_id           = d.get("driverId"),
                    callsign            = drv.get("callsign", ""),
                    forename            = d.get("forename"),
                    surname             = d.get("surname"),
                    bank_name           = drv.get("bankName", ""),
                    bank_sort_code      = drv.get("bankSortCode", ""),
                    current_balance     = d.get("currentBalance", 0.0),
                    outstanding_amount  = d.get("outstandingAmount", 0.0),
                    all_jobs_total      = d.get("allJobsTotal", 0.0),
                    all_jobs_commission = d.get("allJobsCommission", 0.0),
                    notes               = d.get("notes", ""),
                )
                db.add(new_row)
            db.commit()

            # Enriquecer new_results con los datos de banco antes de emitir
            enriched = []
            for d in with_balance:
                drv = driver_map.get(d.get("driverId"), {})
                enriched.append({**d, "callsign": drv.get("callsign", ""),
                                  "bankName": drv.get("bankName", ""),
                                  "bankSortCode": drv.get("bankSortCode", "")})

            yield _sse({
                "type":        "page",
                "page":        page_num,
                "total_pages": total_pages,
                "new_results": enriched,
            })

        yield _sse({"type": "done", "total_drivers": total})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ──────────────────────────────────────────────
# Driver accounts — procesar conductor individual
# ──────────────────────────────────────────────

@router.post("/drivers/accounts/process/{driver_id}")
def process_single_driver(
    driver_id: int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    """
    Procesa un conductor con saldo:
      1. Re-verifica su saldo actual en la API externa.
      2. Actualiza en BD si cambió.
      3. Ejecuta ProcessDriverAccount/{driver_id}.
      4. Guarda el resultado en BD.
    El proceso masivo desde el frontend es un loop de llamadas a este endpoint.
    """
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    row = (
        db.query(DriverAccount)
        .filter(
            DriverAccount.company_id == company_id,
            DriverAccount.driver_id  == driver_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Conductor no encontrado en BD. Ejecuta 'Consultar saldos' primero.")

    sub_key = company.api_subscription_key

    # — 1. Re-verificar saldo —
    try:
        check     = _fetch_accounts_page(sub_key, 1, driver_id=driver_id)
        summaries = check.get("summaries", [])
        if summaries:
            fresh = summaries[0].get("currentBalance", row.current_balance)
            if fresh != row.current_balance:
                row.current_balance = fresh
                db.commit()
    except Exception:
        pass   # si falla la re-verificación, continuamos con el saldo guardado

    balance_before = row.current_balance

    # — 2. Ejecutar ProcessDriverAccount —
    issue_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    try:
        proc_resp = http_requests.post(
            f"{PROCESS_URL}/{driver_id}",
            headers=_autocab_headers(sub_key),
            json={
                "amount":             0,
                "issueDate":          issue_date,
                "loadPrepaidCard":    False,
                "processDocketsOnly": False,
                "sendAsEmail":        False,
                "walletPayOut":       False,
            },
            timeout=30,
        )
        proc_resp.raise_for_status()
        proc_status = "done"
        proc_result = proc_resp.text or "OK"
    except http_requests.exceptions.HTTPError as e:
        proc_status = "error"
        proc_result = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
    except Exception as e:
        proc_status = "error"
        proc_result = str(e)[:500]

    # — 3. Guardar resultado —
    row.process_status          = proc_status
    row.process_result          = proc_result
    row.process_balance_before  = balance_before
    row.processed_at            = datetime.now(timezone.utc)
    db.commit()

    return {
        "driver_id":      driver_id,
        "forename":       row.forename,
        "surname":        row.surname,
        "status":         proc_status,
        "balance_before": balance_before,
        "current_balance": row.current_balance,
        "result":         proc_result,
        "processed_at":   row.processed_at.isoformat(),
    }
