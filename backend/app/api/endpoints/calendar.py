# Calendar API Endpoints
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import CalendarEvent
from app.db.schemas import CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get("/events", response_model=List[CalendarEventResponse])
def get_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all calendar events (paginated)."""
    return (
        db.query(CalendarEvent)
        .order_by(CalendarEvent.start_date.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/events", response_model=CalendarEventResponse)
def create_event(event_data: CalendarEventCreate, db: Session = Depends(get_db)):
    """Create a new calendar event."""
    event = CalendarEvent(**event_data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get a specific calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
def update_event(event_id: int, event_data: CalendarEventUpdate, db: Session = Depends(get_db)):
    """Update a calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    for key, value in event_data.model_dump(exclude_unset=True).items():
        setattr(event, key, value)

    db.commit()
    db.refresh(event)
    return event


@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Delete a calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}


# ----------------------------------------------------------------------
# V0.7 (Fase 4): endpoints adicionales de Google Calendar + availability
# ----------------------------------------------------------------------

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from app.tools.calendar_tool import CalendarTool


def _calendar_tool() -> CalendarTool:
    return CalendarTool()


@router.get("/google/events")
async def google_events(days_ahead: int = Query(7, ge=1, le=90), max_results: int = Query(20, ge=1, le=100)):
    """Lista eventos proximos de Google Calendar."""
    tool = _calendar_tool()
    r = await tool.execute("list_events", {"days_ahead": days_ahead, "max_results": max_results})
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return r["result"]


class CreateEventPayload(BaseModel):
    title: str
    start_datetime: str
    end_datetime: str
    description: Optional[str] = None
    attendees: Optional[List[str]] = None


@router.post("/google/create")
async def google_create(payload: CreateEventPayload):
    """Crea un evento en Google Calendar."""
    tool = _calendar_tool()
    r = await tool.execute("create_event", payload.model_dump())
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return r["result"]


@router.get("/availability")
async def availability(
    date: str = Query(..., description="YYYY-MM-DD"),
    duration_minutes: int = Query(60, ge=15, le=480),
    preferred_hours: Optional[str] = Query(None, description="JSON list de horas 0-23"),
):
    """Encuentra huecos libres combinando eventos Google + availability local."""
    import json as _json
    tool = _calendar_tool()
    params: Dict[str, Any] = {"date": date, "duration_minutes": duration_minutes}
    if preferred_hours:
        try:
            params["preferred_hours"] = _json.loads(preferred_hours)
        except Exception:
            pass
    r = await tool.execute("find_free_slots", params)
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return r["result"]


@router.post("/sync")
async def sync_calendar(days_ahead: int = Query(30, ge=1, le=90)):
    """Sincroniza eventos Google -> BD local."""
    tool = _calendar_tool()
    r = await tool.execute("sync_to_aithera", {"days_ahead": days_ahead})
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return r["result"]


# --- Availability (no requiere OAuth) ---

class AvailabilityPayload(BaseModel):
    date: str
    hour_start: int = 0
    hour_end: int = 24
    status: str = "available"
    label: Optional[str] = None


@router.post("/availability/config")
async def set_availability(payload: AvailabilityPayload):
    """Marca un bloque como available/unavailable/busy."""
    tool = _calendar_tool()
    r = await tool.execute("set_availability", payload.model_dump())
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return r["result"]


@router.get("/availability/list")
async def list_availability_blocks(
    from_date: Optional[str] = Query(None),
    days_ahead: int = Query(30, ge=1, le=365),
):
    """Lista bloques de disponibilidad manual configurados."""
    tool = _calendar_tool()
    params: Dict[str, Any] = {"days_ahead": days_ahead}
    if from_date:
        params["from_date"] = from_date
    r = await tool.execute("list_availability", params)
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return r["result"]


@router.get("/availability/day")
async def get_day_status(date: str = Query(..., description="YYYY-MM-DD")):
    """Devuelve el estado agregado de un dia."""
    tool = _calendar_tool()
    r = await tool.execute("get_day_status", {"date": date})
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return r["result"]


@router.delete("/availability/{avail_id}", status_code=204)
async def delete_availability(avail_id: int):
    tool = _calendar_tool()
    r = await tool.execute("delete_availability", {"id": avail_id})
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return None


@router.post("/availability/clear")
async def clear_all_availability():
    """Borra TODA la disponibilidad manual."""
    tool = _calendar_tool()
    r = await tool.execute("clear_availability", {})
    if not r.get("success"):
        raise HTTPException(status_code=400, detail=r.get("error"))
    return r["result"]


@router.get("/month")
async def month_overview(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
):
    """V0.7: resumen de todo un mes con el estado de cada dia (para la UI de calendario).
    Combina eventos locales (calendar_events) + bloques de availability manual.
    """
    from datetime import date as _date, datetime as _dt, time as _time
    from calendar import monthrange
    from collections import defaultdict

    from app.db.database import SessionLocal
    from app.db.models import CalendarEvent, CalendarAvailability

    first_day = _date(year, month, 1)
    days_in_month = monthrange(year, month)[1]
    last_day = _date(year, month, days_in_month)

    db = SessionLocal()
    try:
        blocks = db.query(CalendarAvailability).filter(
            CalendarAvailability.date >= _dt.combine(first_day, _time()),
            CalendarAvailability.date <= _dt.combine(last_day, _time()),
        ).all()
        events = db.query(CalendarEvent).filter(
            CalendarEvent.start_date >= _dt.combine(first_day, _time()),
            CalendarEvent.start_date <= _dt.combine(last_day, _time(23, 59, 59)),
        ).all()

        blocks_by_day = defaultdict(list)
        for b in blocks:
            blocks_by_day[b.date.date()].append(b)
        events_by_day = defaultdict(list)
        for e in events:
            events_by_day[e.start_date.date()].append(e)

        days = []
        for day_num in range(1, days_in_month + 1):
            d = _date(year, month, day_num)
            day_blocks = blocks_by_day.get(d, [])
            day_events = events_by_day.get(d, [])
            statuses = {b.status for b in day_blocks}
            if "unavailable" in statuses:
                status = "unavailable"
            elif statuses == {"available"}:
                status = "available"
            elif statuses == {"busy"}:
                status = "busy"
            elif statuses:
                status = "mixed"
            elif day_events:
                status = "busy"
            else:
                status = "neutral"

            days.append({
                "date": d.isoformat(),
                "status": status,
                "event_count": len(day_events),
                "event_titles": [e.title for e in day_events[:3]],
                "block_count": len(day_blocks),
                # V0.7 (Fase 4 extra): labels de bloques de availability manual.
                # Asi el usuario ve en la vista global del calendario lo mismo
                # que puso como etiqueta (ej. "Reunion cliente X") sin tener
                # que abrir el modal del dia. Sin prefijo especial: solo el
                # label que el usuario escribio. Si no tiene label, generamos
                # uno automatico basado en el status + horario.
                "block_labels": [
                    b.label if b.label else f"{b.status} {b.hour_start:02d}:00-{b.hour_end:02d}:00"
                    for b in day_blocks[:3]
                ],
            })

        return {
            "year": year,
            "month": month,
            "days": days,
        }
    finally:
        db.close()
