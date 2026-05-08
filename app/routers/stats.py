from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from pydantic import BaseModel

from app.database import get_autocab_db
from app.utils.dependencies import require_permission

router = APIRouter(prefix="/stats", tags=["stats"])


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
            WHERE pickup_due_time >= :dt_from AND pickup_due_time < :dt_to
              AND archive_reason IN ('Completed', 'Cancelled')
        """), {"dt_from": dt_from, "dt_to": dt_to}).fetchone()

        day_rows = autocab_db.execute(text("""
            SELECT
                CAST(pickup_due_time AS DATE)                             AS date,
                COUNT(CASE WHEN archive_reason = 'Completed' THEN 1 END) AS completed,
                COUNT(CASE WHEN archive_reason = 'Cancelled' THEN 1 END) AS cancelled,
                COUNT(*)                                                  AS total,
                COUNT(DISTINCT vehicle_callsign)                          AS unique_vehicles
            FROM bookings
            WHERE pickup_due_time >= :dt_from AND pickup_due_time < :dt_to
              AND archive_reason IN ('Completed', 'Cancelled')
            GROUP BY CAST(pickup_due_time AS DATE)
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
