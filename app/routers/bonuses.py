from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam
from sqlalchemy.exc import OperationalError
import requests as http_requests

from app.database import get_db, get_autocab_db
from app.models.company import Company
from app.utils.dependencies import require_permission

router = APIRouter(prefix="/bonuses", tags=["bonuses"])

AUTOCAB_DRIVERS_URL = "https://autocab-api.azure-api.net/driver/v1/drivers"


def _get_bonus_config(company: Company) -> dict:
    cfg = company.bonus_config or {}
    return {
        "daily_trips":       cfg.get("daily_trips", [
            {"trips": 10, "bonus": 200},
            {"trips": 15, "bonus": 100},
        ]),
        "first_trips_count": cfg.get("first_trips_count", 5),
        "first_trips_bonus": cfg.get("first_trips_bonus", 1000),
    }


def _calc_day_bonus(completed: int, levels: list) -> tuple[int, int]:
    """Devuelve (nivel_alcanzado 1-based, bono_total). Cada nivel suma ADICIONAL al anterior."""
    sorted_levels = sorted(levels, key=lambda x: x["trips"])
    total = 0
    level = 0
    for i, lv in enumerate(sorted_levels):
        if completed >= lv["trips"]:
            total += lv["bonus"]
            level  = i + 1
        else:
            break
    return level, total


def _fetch_drivers(subscription_key: str) -> list[dict]:
    resp = http_requests.get(
        AUTOCAB_DRIVERS_URL,
        headers={
            "User-Agent": "python-requests",
            "Accept":     "*/*",
            "Ocp-Apim-Subscription-Key": subscription_key,
        },
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()
    return raw if isinstance(raw, list) else raw.get("drivers", [raw])


def _dt_range(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    dt_from = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0)
    dt_to   = datetime(date_to.year,   date_to.month,   date_to.day,   0, 0, 0) + timedelta(days=1)
    return dt_from, dt_to


# ──────────────────────────────────────────────
# Bonos diarios
# ──────────────────────────────────────────────

@router.get("/drivers/daily")
def get_daily_bonuses(
    company_id: int  = Query(...),
    date_from:  date = Query(..., description="Fecha inicio YYYY-MM-DD"),
    date_to:    date = Query(..., description="Fecha fin YYYY-MM-DD"),
    db:          Session = Depends(get_db),
    autocab_db:  Session = Depends(get_autocab_db),
    current_user=Depends(require_permission("stats:read")),
):
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to no puede ser anterior a date_from")

    company = db.query(Company).filter(
        Company.id == company_id, Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    bonus_cfg  = _get_bonus_config(company)
    levels     = bonus_cfg["daily_trips"]
    min_trips  = min(lv["trips"] for lv in levels) if levels else 1

    try:
        drivers = _fetch_drivers(company.api_subscription_key)
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="No se pudo conectar a la API de Autocab")
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Tiempo de espera agotado")
    except http_requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error de la API: {e}")

    active     = [d for d in drivers if d.get("active") is True]
    callsigns  = [str(d["callsign"]) for d in active if d.get("callsign") is not None]
    driver_map = {str(d["callsign"]): d for d in active if d.get("callsign")}

    if not callsigns:
        return _empty_daily(company, date_from, date_to, bonus_cfg)

    dt_from, dt_to = _dt_range(date_from, date_to)

    try:
        stmt = text("""
            SELECT
                driver_callsign,
                CAST(archive_time AS DATE) AS day,
                COUNT(*)                   AS completed
            FROM bookings
            WHERE archive_reason = 'Completed'
              AND archive_time >= :dt_from
              AND archive_time <  :dt_to
              AND driver_callsign IN :callsigns
            GROUP BY driver_callsign, CAST(archive_time AS DATE)
            HAVING COUNT(*) >= :min_trips
            ORDER BY driver_callsign, day
        """).bindparams(bindparam("callsigns", expanding=True))

        rows = autocab_db.execute(stmt, {
            "dt_from":   dt_from,
            "dt_to":     dt_to,
            "callsigns": callsigns,
            "min_trips": min_trips,
        }).fetchall()

    except OperationalError:
        raise HTTPException(status_code=502, detail="Error consultando la BD de Autocab")

    # Agrupar por conductor
    by_driver: dict = {}
    for row in rows:
        level, bonus = _calc_day_bonus(row.completed, levels)
        if bonus == 0:
            continue
        cs = row.driver_callsign
        if cs not in by_driver:
            by_driver[cs] = {"days": [], "total_bonus": 0}
        by_driver[cs]["days"].append({
            "date":            row.day.isoformat(),
            "completed_trips": row.completed,
            "level_reached":   level,
            "bonus":           bonus,
        })
        by_driver[cs]["total_bonus"] += bonus

    result = []
    for cs, data in by_driver.items():
        drv = driver_map.get(cs, {})
        result.append({
            "callsign":    cs,
            "forename":    drv.get("forename", ""),
            "surname":     drv.get("surname",  ""),
            "full_name":   drv.get("fullName", cs),
            "mobile":      drv.get("mobile",   ""),
            "total_bonus": data["total_bonus"],
            "days":        data["days"],
        })

    result.sort(key=lambda x: x["total_bonus"], reverse=True)

    return {
        "company":                  {"id": company.id, "name": company.name},
        "date_from":                date_from.isoformat(),
        "date_to":                  date_to.isoformat(),
        "bonus_config":             bonus_cfg,
        "total_drivers_with_bonus": len(result),
        "total_bonus_amount":       sum(r["total_bonus"] for r in result),
        "drivers":                  result,
    }


def _empty_daily(company, date_from, date_to, bonus_cfg):
    return {
        "company":                  {"id": company.id, "name": company.name},
        "date_from":                date_from.isoformat(),
        "date_to":                  date_to.isoformat(),
        "bonus_config":             bonus_cfg,
        "total_drivers_with_bonus": 0,
        "total_bonus_amount":       0,
        "drivers":                  [],
    }


# ──────────────────────────────────────────────
# Bono primer viaje
# ──────────────────────────────────────────────

@router.get("/drivers/first-trip")
def get_first_trip_bonuses(
    company_id: int  = Query(...),
    date_from:  date = Query(..., description="Fecha inicio YYYY-MM-DD"),
    date_to:    date = Query(..., description="Fecha fin YYYY-MM-DD"),
    db:          Session = Depends(get_db),
    autocab_db:  Session = Depends(get_autocab_db),
    current_user=Depends(require_permission("stats:read")),
):
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to no puede ser anterior a date_from")

    company = db.query(Company).filter(
        Company.id == company_id, Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    bonus_cfg         = _get_bonus_config(company)
    first_trips_count = bonus_cfg["first_trips_count"]
    first_trips_bonus = bonus_cfg["first_trips_bonus"]

    try:
        # Todos los conductores (activos e inactivos) — el viaje N pudo ser antes de desactivarse
        drivers = _fetch_drivers(company.api_subscription_key)
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="No se pudo conectar a la API de Autocab")
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Tiempo de espera agotado")
    except http_requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error de la API: {e}")

    callsigns  = [str(d["callsign"]) for d in drivers if d.get("callsign") is not None]
    driver_map = {str(d["callsign"]): d for d in drivers if d.get("callsign")}

    if not callsigns:
        return {
            "company":            {"id": company.id, "name": company.name},
            "date_from":          date_from.isoformat(),
            "date_to":            date_to.isoformat(),
            "first_trips_count":  first_trips_count,
            "first_trips_bonus":  first_trips_bonus,
            "total_drivers":      0,
            "total_bonus_amount": 0,
            "drivers":            [],
        }

    dt_from, dt_to = _dt_range(date_from, date_to)

    try:
        # Conductores cuyo viaje #N ever (el qualifying_trip) cayó dentro del rango
        stmt = text("""
            SELECT driver_callsign, archive_time AS qualifying_trip_at
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
            WHERE trip_num   = :n_trips
              AND archive_time >= :dt_from
              AND archive_time <  :dt_to
            ORDER BY qualifying_trip_at
        """).bindparams(bindparam("callsigns", expanding=True))

        rows = autocab_db.execute(stmt, {
            "callsigns": callsigns,
            "n_trips":   first_trips_count,
            "dt_from":   dt_from,
            "dt_to":     dt_to,
        }).fetchall()

    except OperationalError:
        raise HTTPException(status_code=502, detail="Error consultando la BD de Autocab")

    result = []
    for row in rows:
        drv = driver_map.get(row.driver_callsign, {})
        result.append({
            "callsign":           row.driver_callsign,
            "forename":           drv.get("forename", ""),
            "surname":            drv.get("surname",  ""),
            "full_name":          drv.get("fullName", row.driver_callsign),
            "mobile":             drv.get("mobile",   ""),
            "qualifying_trip_at": row.qualifying_trip_at.isoformat() if row.qualifying_trip_at else None,
            "bonus":              first_trips_bonus,
        })

    return {
        "company":            {"id": company.id, "name": company.name},
        "date_from":          date_from.isoformat(),
        "date_to":            date_to.isoformat(),
        "first_trips_count":  first_trips_count,
        "first_trips_bonus":  first_trips_bonus,
        "total_drivers":      len(result),
        "total_bonus_amount": len(result) * first_trips_bonus,
        "drivers":            result,
    }
