from datetime import date, datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam
from sqlalchemy.exc import OperationalError
from pydantic import BaseModel
import requests as http_requests

from app.database import get_db, get_autocab_db
from app.models.company import Company
from app.utils.dependencies import require_permission

router = APIRouter(prefix="/stats", tags=["stats"])


# ──────────────────────────────────────────────
# Bookings summary
# ──────────────────────────────────────────────

class BookingStatsSummary(BaseModel):
    completed:       int
    cancelled:       int
    total:           int
    unique_vehicles: int

class BookingStatsByDay(BaseModel):
    date:            date
    completed:       int
    cancelled:       int
    total:           int
    unique_vehicles: int

class BookingStatsResponse(BaseModel):
    date_from: date
    date_to:   date
    summary:   BookingStatsSummary
    by_day:    list[BookingStatsByDay]


@router.get("/bookings/summary", response_model=BookingStatsResponse)
def get_booking_stats(
    date_from: date = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    date_to:   date = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    autocab_db: Session = Depends(get_autocab_db),
    current_user=Depends(require_permission("stats:read")),
):
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to no puede ser anterior a date_from")

    dt_from = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0)
    dt_to   = datetime(date_to.year,  date_to.month,   date_to.day,   0, 0, 0) + timedelta(days=1)

    try:
        summary_row = autocab_db.execute(text("""
            SELECT
                COUNT(CASE WHEN archive_reason = 'Completed' THEN 1 END) AS completed,
                COUNT(CASE WHEN archive_reason = 'Cancelled' THEN 1 END) AS cancelled,
                COUNT(*)                                                  AS total,
                COUNT(DISTINCT vehicle_callsign)                          AS unique_vehicles
            FROM bookings
            WHERE archive_time >= :dt_from AND archive_time < :dt_to
              AND archive_reason IN ('Completed', 'Cancelled')
        """), {"dt_from": dt_from, "dt_to": dt_to}).fetchone()

        day_rows = autocab_db.execute(text("""
            SELECT
                CAST(archive_time AS DATE)                                AS date,
                COUNT(CASE WHEN archive_reason = 'Completed' THEN 1 END) AS completed,
                COUNT(CASE WHEN archive_reason = 'Cancelled' THEN 1 END) AS cancelled,
                COUNT(*)                                                  AS total,
                COUNT(DISTINCT vehicle_callsign)                          AS unique_vehicles
            FROM bookings
            WHERE archive_time >= :dt_from AND archive_time < :dt_to
              AND archive_reason IN ('Completed', 'Cancelled')
            GROUP BY CAST(archive_time AS DATE)
            ORDER BY date ASC
        """), {"dt_from": dt_from, "dt_to": dt_to}).fetchall()

    except OperationalError:
        raise HTTPException(status_code=502, detail="Error consultando la base de datos de Autocab")

    return BookingStatsResponse(
        date_from=date_from,
        date_to=date_to,
        summary=BookingStatsSummary(
            completed=      summary_row.completed       or 0,
            cancelled=      summary_row.cancelled       or 0,
            total=          summary_row.total           or 0,
            unique_vehicles=summary_row.unique_vehicles or 0,
        ),
        by_day=[
            BookingStatsByDay(
                date=           row.date,
                completed=      row.completed       or 0,
                cancelled=      row.cancelled       or 0,
                total=          row.total           or 0,
                unique_vehicles=row.unique_vehicles or 0,
            )
            for row in day_rows
        ],
    )


# ──────────────────────────────────────────────
# Driver stats
# ──────────────────────────────────────────────

class DriverDayStats(BaseModel):
    date:      date
    completed: int
    cancelled: int
    total:     int

class DriverAllTimeStats(BaseModel):
    completed: int
    cancelled: int
    total:     int

class DriverStatsItem(BaseModel):
    id:              int
    callsign:        str
    forename:        str
    surname:         str
    full_name:       str
    mobile:          str
    active:          bool
    last_15_days:    list[DriverDayStats]
    all_time:        DriverAllTimeStats
    last_booking_at: Optional[datetime] = None

class DriversStatsResponse(BaseModel):
    company:       dict
    total_drivers: int
    drivers:       list[DriverStatsItem]


@router.get("/drivers/summary", response_model=DriversStatsResponse)
def get_driver_stats(
    company_id: int = Query(...),
    db:         Session = Depends(get_db),
    autocab_db: Session = Depends(get_autocab_db),
    current_user=Depends(require_permission("stats:read")),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Fetch drivers from Autocab API
    try:
        resp = http_requests.get(
            "https://autocab-api.azure-api.net/driver/v1/drivers",
            headers={
                "User-Agent":              "python-requests",
                "Accept":                  "*/*",
                "Ocp-Apim-Subscription-Key": company.api_subscription_key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()
        drivers = raw if isinstance(raw, list) else raw.get("drivers", [raw])
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="No se pudo conectar a la API de Autocab")
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Tiempo de espera agotado")
    except http_requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error de la API: {e}")

    active_drivers = [d for d in drivers if d.get("active") is True]

    if not active_drivers:
        return DriversStatsResponse(
            company={"id": company.id, "name": company.name},
            total_drivers=0,
            drivers=[],
        )

    callsigns = [str(d["callsign"]) for d in active_drivers if d.get("callsign") is not None]

    try:
        # Query 1: desglose día por día — últimos 15 días
        daily_stmt = text("""
            SELECT
                driver_callsign,
                CAST(archive_time AS DATE)                                AS day,
                COUNT(CASE WHEN archive_reason = 'Completed' THEN 1 END) AS completed,
                COUNT(CASE WHEN archive_reason = 'Cancelled' THEN 1 END) AS cancelled
            FROM bookings
            WHERE archive_reason IN ('Completed', 'Cancelled')
              AND archive_time >= CURRENT_DATE - INTERVAL '14 days'
              AND driver_callsign IN :callsigns
            GROUP BY driver_callsign, CAST(archive_time AS DATE)
        """).bindparams(bindparam("callsigns", expanding=True))

        daily_rows = autocab_db.execute(daily_stmt, {"callsigns": callsigns}).fetchall()

        # Query 2: totales históricos + último booking
        total_stmt = text("""
            SELECT
                driver_callsign,
                COUNT(CASE WHEN archive_reason = 'Completed' THEN 1 END) AS completed_total,
                COUNT(CASE WHEN archive_reason = 'Cancelled' THEN 1 END) AS cancelled_total,
                MAX(archive_time)                                         AS last_booking_at
            FROM bookings
            WHERE archive_reason IN ('Completed', 'Cancelled')
              AND driver_callsign IN :callsigns
            GROUP BY driver_callsign
        """).bindparams(bindparam("callsigns", expanding=True))

        total_rows = autocab_db.execute(total_stmt, {"callsigns": callsigns}).fetchall()

    except OperationalError:
        raise HTTPException(status_code=502, detail="Error consultando la base de datos de Autocab")

    # Índices para lookup rápido
    # daily_map[callsign][date] = row
    daily_map: dict = {}
    for row in daily_rows:
        daily_map.setdefault(row.driver_callsign, {})[row.day] = row

    total_map = {row.driver_callsign: row for row in total_rows}

    # Rango de fechas últimos 15 días (hoy incluido)
    today = date.today()
    last_15 = [today - timedelta(days=i) for i in range(14, -1, -1)]

    result = []
    for d in active_drivers:
        cs       = str(d.get("callsign", ""))
        trow     = total_map.get(cs)
        day_data = daily_map.get(cs, {})

        ct = trow.completed_total if trow else 0
        xt = trow.cancelled_total if trow else 0

        days_out = []
        for day in last_15:
            drow = day_data.get(day)
            c = drow.completed if drow else 0
            x = drow.cancelled if drow else 0
            days_out.append(DriverDayStats(date=day, completed=c, cancelled=x, total=c + x))

        result.append(DriverStatsItem(
            id=              d.get("id", 0),
            callsign=        cs,
            forename=        d.get("forename", ""),
            surname=         d.get("surname", ""),
            full_name=       d.get("fullName", ""),
            mobile=          d.get("mobile", ""),
            active=          d.get("active", True),
            last_15_days=    days_out,
            all_time=        DriverAllTimeStats(completed=ct, cancelled=xt, total=ct + xt),
            last_booking_at= trow.last_booking_at if trow else None,
        ))

    return DriversStatsResponse(
        company={"id": company.id, "name": company.name},
        total_drivers=len(result),
        drivers=result,
    )
