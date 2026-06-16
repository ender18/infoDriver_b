import uuid
import re
from datetime import datetime, timezone, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
import requests as http_requests
import math
import json

from sqlalchemy import func, text, bindparam
from sqlalchemy.exc import OperationalError

from app.database import get_db, get_autocab_db
from app.models.company import Company
from app.models.driver_account import DriverAccount
from app.models.driver_account_history import DriverAccountHistory
from app.models.peibo_transaction import PeiboTransaction
from app.models.peibo_webhook_event import PeiboWebhookEvent
from app.models.bank import Bank
from app.models.payment_log import PaymentLog
from app.models.payment_queue import PaymentQueue
from app.utils.dependencies import require_permission
from app.services.tools import drivers_client
from app.services.tools import (
    authorization_validator,
    bank_validator,
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


def _log(db: Session, event_type: str, company_id=None, driver_id=None,
         session_id=None, history_id=None, payload=None):
    entry = PaymentLog(
        event_type=event_type,
        company_id=company_id,
        driver_id=driver_id,
        session_id=session_id,
        history_id=history_id,
        payload=payload,
    )
    db.add(entry)
    db.commit()


def _row_to_dict(row, tx: PeiboTransaction = None, event: PeiboWebhookEvent = None, queue_status: str = None) -> dict:
    return {
        "id":                       row.id,
        "driver_id":                row.driver_id,
        "session_id":               row.session_id,
        "callsign":                 row.callsign,
        "forename":                 row.forename,
        "surname":                  row.surname,
        "bank_name":                row.bank_name,
        "bank_sort_code":           row.bank_sort_code,
        "current_balance":          row.current_balance,
        "outstanding_amount":       row.outstanding_amount,
        "all_jobs_total":           row.all_jobs_total,
        "all_jobs_commission":      row.all_jobs_commission,
        "notes":                    row.notes,
        "fetched_at":               row.fetched_at.isoformat() if row.fetched_at else None,
        "process_status":           row.process_status,
        "process_result":           row.process_result,
        "process_balance_before":   row.process_balance_before,
        "processed_at":             row.processed_at.isoformat() if row.processed_at else None,
        # Pago — queue activa tiene prioridad sobre peibo_transactions
        "payment_status":           "pending" if queue_status in ("pending", "approved") else (tx.status if tx else None),
        "peibo_transaction_id":     tx.id            if tx    else None,
        "peibo_tracking_code":      tx.tracking_code if tx    else None,
        "peibo_paid_at":            tx.paid_at.isoformat() if (tx and tx.paid_at) else None,
        # Webhook — leído del último peibo_webhook_events
        "webhook_status":              event.status             if event else None,
        "webhook_transaction_id":      event.tracking_code      if event else None,
        "webhook_date_time":           event.date_time.isoformat() if (event and event.date_time) else None,
        "webhook_concept":             event.concept            if event else None,
        "webhook_reference":           event.reference          if event else None,
        "webhook_amount":              float(event.amount)      if (event and event.amount is not None) else None,
        "webhook_beneficiary_account": event.beneficiary_account if event else None,
        "webhook_originator_account":  event.originator_account  if event else None,
        "webhook_originator_bank":     event.originator_bank     if event else None,
        "webhook_originator_name":     event.originator_name     if event else None,
        "webhook_originator_tax_id":   event.originator_tax_id   if event else None,
        "webhook_type":                event.type                if event else None,
        "webhook_refund_reason_code":  event.refund_reason_code  if event else None,
        "webhook_received_at":         event.received_at.isoformat() if (event and event.received_at) else None,
    }


def _load_tx_and_events(db: Session, rows: list) -> tuple[dict, dict]:
    """Carga en batch PeiboTransaction y el último PeiboWebhookEvent para una lista de rows."""
    tx_ids = [r.peibo_transaction_id for r in rows if r.peibo_transaction_id]
    if not tx_ids:
        return {}, {}

    txs = {t.id: t for t in db.query(PeiboTransaction).filter(PeiboTransaction.id.in_(tx_ids)).all()}

    # Subconsulta: id máximo de evento por transacción
    latest_ids = (
        db.query(func.max(PeiboWebhookEvent.id))
        .filter(PeiboWebhookEvent.peibo_transaction_id.in_(tx_ids))
        .group_by(PeiboWebhookEvent.peibo_transaction_id)
        .all()
    )
    latest_id_list = [row[0] for row in latest_ids if row[0]]
    events = {}
    if latest_id_list:
        for e in db.query(PeiboWebhookEvent).filter(PeiboWebhookEvent.id.in_(latest_id_list)).all():
            events[e.peibo_transaction_id] = e

    return txs, events


def _history_row_from_account(row: DriverAccount, session_id: str | None = None) -> DriverAccountHistory:
    return DriverAccountHistory(
        session_id             = session_id or row.session_id or "legacy",
        company_id             = row.company_id,
        driver_id              = row.driver_id,
        callsign               = row.callsign,
        forename               = row.forename,
        surname                = row.surname,
        bank_name              = row.bank_name,
        bank_sort_code         = row.bank_sort_code,
        current_balance        = row.current_balance,
        outstanding_amount     = row.outstanding_amount,
        all_jobs_total         = row.all_jobs_total,
        all_jobs_commission    = row.all_jobs_commission,
        notes                  = row.notes,
        fetched_at             = row.fetched_at,
        process_status         = row.process_status,
        process_result         = row.process_result,
        process_balance_before = row.process_balance_before,
        processed_at           = row.processed_at,
        peibo_transaction_id   = row.peibo_transaction_id,
    )


# ──────────────────────────────────────────────
# Validation endpoint (original — sin cambios)
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

    known_banks = {r.name.upper() for r in db.query(Bank.name).all()}
    cfg = company.validation_config or {}

    all_results = []
    for validator in VALIDATORS:
        all_results.extend(validator.run(drivers, authorizations, cfg))
    all_results.extend(bank_validator.run(drivers, authorizations, known_banks, cfg))

    return {
        "company":       {"id": company.id, "name": company.name},
        "total_drivers": len(drivers),
        "total_errors":  len(all_results),
        "results":       all_results,
    }


# ──────────────────────────────────────────────
# Referidos
# ──────────────────────────────────────────────

_REF_RE = re.compile(r"^REF: (\S+)$")

# Plan HERO — umbrales de viajes completados y bono parcial para el referidor
_HERO_MILESTONES = [
    {"viajes": 1,   "parcial": 500},
    {"viajes": 15,  "parcial": 200},
    {"viajes": 25,  "parcial": 300},
    {"viajes": 50,  "parcial": 500},
    {"viajes": 100, "parcial": 1000},
]
_HERO_ONGOING_THRESHOLD = 100   # a partir de aquí aplica bono recurrente
_HERO_ONGOING_BONUS     = 2500


def _calc_hero(completed: int) -> dict:
    earned = 0
    level  = 0
    for i, m in enumerate(_HERO_MILESTONES):
        if completed >= m["viajes"]:
            earned += m["parcial"]
            level   = i + 1
    return {
        "level":   level,          # 0 = sin viajes, 1-5 = milestone alcanzado
        "earned":  earned,         # bono acumulado one-time para el referidor
        "ongoing": completed >= _HERO_ONGOING_THRESHOLD,
    }

@router.get("/drivers/referrals")
def get_driver_referrals(
    company_id:  int = Query(...),
    db:          Session = Depends(get_db),
    autocab_db:  Session = Depends(get_autocab_db),
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
        raise HTTPException(status_code=504, detail="Tiempo de espera agotado")
    except http_requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error de la API externa: {e}")

    drivers = data["drivers"]

    # Índice por teléfono para resolver quién es el referidor
    phone_map: dict[str, dict] = {}
    for d in drivers:
        for field in ("mobile", "telephone"):
            phone = (d.get(field) or "").strip()
            if phone:
                phone_map[phone] = d

    # Agrupar referidos por ref_value (postcode = "REF: <valor>")
    groups: dict[str, list] = {}
    for d in drivers:
        postcode = ((d.get("postalAddress") or {}).get("postcode") or "").strip()
        m = _REF_RE.match(postcode)
        if not m:
            continue
        ref_value = m.group(1)
        groups.setdefault(ref_value, []).append({
            "driver_id": d.get("id"),
            "callsign":  str(d.get("callsign") or ""),
            "full_name": d.get("fullName"),
            "email":     d.get("email"),
        })

    # ── Semana actual (lunes–domingo) ────────────────────────────────────
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())   # lunes
    week_end   = week_start + timedelta(days=7)            # lunes siguiente (exclusivo)

    # ── Stats de viajes para los conductores referidos ──────────────────
    all_referred_callsigns = list({
        r["callsign"]
        for referred_list in groups.values()
        for r in referred_list
        if r["callsign"]
    })

    booking_map: dict[str, dict] = {}    # callsign → totales
    milestone_map: dict[str, list] = {}  # callsign → [{trip_num, reached_at}]

    if all_referred_callsigns:
        try:
            # Query 1 — totales por conductor
            totals_stmt = text("""
                SELECT
                    driver_callsign,
                    COUNT(*)                                                                          AS completed_all,
                    COUNT(CASE WHEN archive_time >= CURRENT_DATE - INTERVAL '14 days' THEN 1 END)   AS completed_15d,
                    MAX(archive_time)                                                                 AS last_booking_at
                FROM bookings
                WHERE archive_reason = 'Completed'
                  AND driver_callsign IN :callsigns
                GROUP BY driver_callsign
            """).bindparams(bindparam("callsigns", expanding=True))

            for row in autocab_db.execute(totals_stmt, {"callsigns": all_referred_callsigns}).fetchall():
                booking_map[row.driver_callsign] = {
                    "completed_all":   row.completed_all  or 0,
                    "completed_15d":   row.completed_15d  or 0,
                    "last_booking_at": row.last_booking_at.isoformat() if row.last_booking_at else None,
                }

            # Query 2 — fecha exacta en que se alcanzó cada milestone (viaje N)
            milestone_stmt = text("""
                SELECT driver_callsign, trip_num, archive_time
                FROM (
                    SELECT
                        driver_callsign,
                        archive_time,
                        ROW_NUMBER() OVER (
                            PARTITION BY driver_callsign
                            ORDER BY archive_time
                        ) AS trip_num
                    FROM bookings
                    WHERE archive_reason = 'Completed'
                      AND driver_callsign IN :callsigns
                ) ranked
                WHERE trip_num IN (1, 15, 25, 50, 100)
                ORDER BY driver_callsign, trip_num
            """).bindparams(bindparam("callsigns", expanding=True))

            for row in autocab_db.execute(milestone_stmt, {"callsigns": all_referred_callsigns}).fetchall():
                milestone_map.setdefault(row.driver_callsign, []).append({
                    "trip_num":   row.trip_num,
                    "reached_at": row.archive_time.isoformat() if row.archive_time else None,
                })

        except OperationalError:
            pass   # Autocab DB no disponible — continuamos sin stats

    # ── Helper: enriquecer un referido con stats + HERO + semana ─────────
    _milestone_by_trips = {m["viajes"]: (i + 1, m["parcial"]) for i, m in enumerate(_HERO_MILESTONES)}

    def _enrich_referred(r: dict) -> dict:
        cs      = r["callsign"]
        stats   = booking_map.get(cs, {})
        completed = stats.get("completed_all", 0)
        hero    = _calc_hero(completed)

        milestones = []
        for ms in milestone_map.get(cs, []):
            level, parcial = _milestone_by_trips.get(ms["trip_num"], (0, 0))
            if level:
                milestones.append({
                    "level":      level,
                    "viajes":     ms["trip_num"],
                    "parcial":    parcial,
                    "reached_at": ms["reached_at"],
                })

        this_week_milestones = []
        for ms in milestones:
            if ms["reached_at"]:
                ra = datetime.fromisoformat(ms["reached_at"]).date()
                if week_start <= ra < week_end:
                    this_week_milestones.append(ms)

        return {
            **r,
            "completed_trips":       completed,
            "completed_15d":         stats.get("completed_15d", 0),
            "last_booking_at":       stats.get("last_booking_at"),
            "hero_level":            hero["level"],
            "hero_earned":           hero["earned"],
            "hero_ongoing":          hero["ongoing"],
            "hero_milestones":       milestones,
            "this_week_milestones":  this_week_milestones,
            "this_week_bonus":       sum(m["parcial"] for m in this_week_milestones),
        }

    # ── Construir respuesta ──────────────────────────────────────────────
    referrers = []
    for ref_value, referred_list in groups.items():
        referrer         = phone_map.get(ref_value)
        enriched_referred = [_enrich_referred(r) for r in referred_list]

        referrers.append({
            "ref_value":        ref_value,
            "callsign":         referrer.get("callsign") if referrer else None,
            "full_name":        referrer.get("fullName") if referrer else None,
            "referred_count":   len(enriched_referred),
            "total_hero_bonus": sum(r["hero_earned"]      for r in enriched_referred),
            "this_week_bonus":  sum(r["this_week_bonus"]  for r in enriched_referred),
            "referred":         enriched_referred,
        })

    referrers.sort(key=lambda x: x["referred_count"], reverse=True)

    # ── Pagos de la semana (solo referidores con bono > 0 esta semana) ───
    weekly_referrers = []
    for ref in referrers:
        drivers_this_week = [
            {
                "driver_id":  r["driver_id"],
                "callsign":   r["callsign"],
                "full_name":  r["full_name"],
                "milestones": r["this_week_milestones"],
                "bonus":      r["this_week_bonus"],
            }
            for r in ref["referred"]
            if r["this_week_bonus"] > 0
        ]
        if drivers_this_week:
            weekly_referrers.append({
                "ref_value":       ref["ref_value"],
                "callsign":        ref["callsign"],
                "full_name":       ref["full_name"],
                "this_week_bonus": ref["this_week_bonus"],
                "drivers":         drivers_this_week,
            })

    weekly_referrers.sort(key=lambda x: x["this_week_bonus"], reverse=True)

    return {
        "company":         {"id": company.id, "name": company.name},
        "total_drivers":   len(drivers),
        "total_referrers": len(referrers),
        "total_referred":  sum(r["referred_count"] for r in referrers),
        "hero_plan":       _HERO_MILESTONES + [{"viajes": None, "parcial": _HERO_ONGOING_BONUS}],
        "referrers":       referrers,
        "weekly_payments": {
            "week_start":   week_start.isoformat(),
            "week_end":     (week_end - timedelta(days=1)).isoformat(),
            "total_to_pay": sum(r["this_week_bonus"] for r in referrers),
            "referrers":    weekly_referrers,
        },
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

    txs, events = _load_tx_and_events(db, rows)

    # Conductores con pago activo en la cola (pending o approved)
    driver_ids = [r.driver_id for r in rows]
    queue_map: dict[int, str] = {}
    if driver_ids:
        active_queue = db.query(PaymentQueue).filter(
            PaymentQueue.company_id == company_id,
            PaymentQueue.source     == "driver_balance",
            PaymentQueue.driver_id.in_(driver_ids),
            PaymentQueue.status.in_(("pending", "approved")),
        ).all()
        queue_map = {q.driver_id: q.status for q in active_queue}

    return {
        "company":              {"id": company.id, "name": company.name},
        "drivers_with_balance": len(rows),
        "fetched_at":           rows[0].fetched_at.isoformat() if rows else None,
        "results":              [_row_to_dict(r, txs.get(r.peibo_transaction_id), events.get(r.peibo_transaction_id), queue_map.get(r.driver_id)) for r in rows],
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
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    sub_key      = company.api_subscription_key
    company_info = {"id": company.id, "name": company.name}
    new_session  = str(uuid.uuid4())

    def generate():
        # — Mapa de conductores para cruzar bank/callsign —
        try:
            drivers_data = drivers_client.fetch_all(sub_key)
            driver_map = {d["id"]: d for d in drivers_data["drivers"]}
        except Exception:
            driver_map = {}

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

        # ── TODO O NADA: archivar sesión anterior + borrar en un solo commit ──
        existing = db.query(DriverAccount).options(
            joinedload(DriverAccount.peibo_transaction)
        ).filter(DriverAccount.company_id == company_id).all()
        if existing:
            first = existing[0]
            archive_session = (
                first.session_id
                or (first.fetched_at.strftime("%Y-%m-%dT%H:%M:00+00:00")
                    if first.fetched_at else "legacy")
            )
            # Cargar registros que ya existen en histórico para esta sesión
            # (escritos durante el refresh anterior, página a página)
            hist_map = {
                r.driver_id: r
                for r in db.query(DriverAccountHistory).filter(
                    DriverAccountHistory.session_id == archive_session,
                    DriverAccountHistory.company_id == company_id,
                ).all()
            } if archive_session != "legacy" else {}

            try:
                for row in existing:
                    if row.driver_id in hist_map:
                        # Ya existe en histórico — actualizar con el estado final
                        # (captura process_status, payment_status, etc. que cambiaron
                        #  después de que se guardó la página original)
                        h = hist_map[row.driver_id]
                        h.process_status         = row.process_status
                        h.process_result         = row.process_result
                        h.process_balance_before = row.process_balance_before
                        h.processed_at           = row.processed_at
                        h.current_balance        = row.current_balance
                        tx = row.peibo_transaction
                        h.payment_status         = tx.status        if tx else None
                        h.peibo_transaction_id   = row.peibo_transaction_id
                        h.peibo_tracking_code    = tx.tracking_code if tx else None
                        h.peibo_paid_at          = tx.paid_at       if tx else None
                    else:
                        # No existe en histórico (datos legacy) — insertar
                        db.add(_history_row_from_account(row, session_id=archive_session))

                db.query(DriverAccount).filter(DriverAccount.company_id == company_id).delete()
                db.commit()
            except Exception as e:
                db.rollback()
                yield _sse({"type": "error", "code": 500,
                             "detail": f"Error al respaldar sesión anterior: {str(e)}"})
                return

        _log(db, "refresh_start", company_id=company_id, session_id=new_session)
        yield _sse({"type": "init", "total": total, "total_pages": total_pages, "company": company_info})

        # — Procesar páginas —
        session_fetched_at = datetime.now(timezone.utc)   # timestamp único para toda la sesión
        saved_count = 0
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
                drv = driver_map.get(d.get("driverId"), {})

                work_row = DriverAccount(
                    company_id          = company_id,
                    session_id          = new_session,
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
                    fetched_at          = session_fetched_at,
                )
                hist_row = DriverAccountHistory(
                    session_id          = new_session,
                    company_id          = company_id,
                    driver_id           = d.get("driverId"),
                    callsign            = drv.get("callsign", ""),
                    forename            = d.get("forename"),
                    surname             = d.get("surname"),
                    bank_name           = drv.get("bankName", ""),
                    fetched_at          = session_fetched_at,
                    bank_sort_code      = drv.get("bankSortCode", ""),
                    current_balance     = d.get("currentBalance", 0.0),
                    outstanding_amount  = d.get("outstandingAmount", 0.0),
                    all_jobs_total      = d.get("allJobsTotal", 0.0),
                    all_jobs_commission = d.get("allJobsCommission", 0.0),
                    notes               = d.get("notes", ""),
                )
                db.add(work_row)
                db.add(hist_row)
            db.commit()
            saved_count += len(with_balance)

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

        _log(db, "refresh_done", company_id=company_id, session_id=new_session,
             payload={"total_drivers": total, "drivers_with_balance": saved_count})
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
        pass

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

    # — 3. Guardar resultado en tabla de trabajo —
    row.process_status          = proc_status
    row.process_result          = proc_result
    row.process_balance_before  = balance_before
    row.processed_at            = datetime.now(timezone.utc)
    db.commit()

    # — 4. Sincronizar con el histórico de la misma sesión —
    hist_row = (
        db.query(DriverAccountHistory)
        .filter(
            DriverAccountHistory.company_id == company_id,
            DriverAccountHistory.driver_id  == driver_id,
            DriverAccountHistory.session_id == row.session_id,
        )
        .first()
    )
    if hist_row:
        hist_row.process_status         = proc_status
        hist_row.process_result         = proc_result
        hist_row.process_balance_before = balance_before
        hist_row.processed_at           = row.processed_at
        db.commit()

    _log(db, f"process_{proc_status}",
         company_id=company_id,
         driver_id=driver_id,
         session_id=row.session_id,
         history_id=hist_row.id if hist_row else None,
         payload={"balance_before": balance_before, "result": proc_result[:500]})

    return {
        "driver_id":       driver_id,
        "forename":        row.forename,
        "surname":         row.surname,
        "status":          proc_status,
        "balance_before":  balance_before,
        "current_balance": row.current_balance,
        "result":          proc_result,
        "processed_at":    row.processed_at.isoformat(),
    }


# ──────────────────────────────────────────────
# Histórico — listar sesiones
# ──────────────────────────────────────────────

@router.get("/drivers/accounts/history")
def list_history_sessions(
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

    rows = (
        db.query(DriverAccountHistory)
        .filter(DriverAccountHistory.company_id == company_id)
        .order_by(DriverAccountHistory.fetched_at.desc())
        .all()
    )

    # Agrupar por session_id
    sessions: dict = {}
    for r in rows:
        sid = r.session_id
        if sid not in sessions:
            sessions[sid] = {
                "session_id":           sid,
                "fetched_at":           r.fetched_at.isoformat() if r.fetched_at else None,
                "drivers_with_balance": 0,
                "processed_count":      0,
                "paid_count":           0,
            }
        s = sessions[sid]
        s["drivers_with_balance"] += 1
        if r.process_status == "done":
            s["processed_count"] += 1
        if r.process_status == "success":
            s["paid_count"] += 1

    return {"company": {"id": company.id, "name": company.name},
            "sessions": list(sessions.values())}


# ──────────────────────────────────────────────
# Histórico — detalle de una sesión
# ──────────────────────────────────────────────

@router.get("/drivers/accounts/history/{session_id}")
def get_history_session(
    session_id: str,
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

    rows = (
        db.query(DriverAccountHistory)
        .filter(
            DriverAccountHistory.company_id == company_id,
            DriverAccountHistory.session_id == session_id,
        )
        .order_by(DriverAccountHistory.current_balance.desc())
        .all()
    )

    txs, events = _load_tx_and_events(db, rows)

    return {
        "company":    {"id": company.id, "name": company.name},
        "session_id": session_id,
        "results":    [_row_to_dict(r, txs.get(r.peibo_transaction_id), events.get(r.peibo_transaction_id)) for r in rows],
    }


# ──────────────────────────────────────────────
# Log de auditoría
# ──────────────────────────────────────────────

@router.get("/drivers/accounts/log")
def get_payment_log(
    company_id: int = Query(...),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    entries = (
        db.query(PaymentLog)
        .filter(PaymentLog.company_id == company_id)
        .order_by(PaymentLog.created_at.desc())
        .limit(limit)
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
