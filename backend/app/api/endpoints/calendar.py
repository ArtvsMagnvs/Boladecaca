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
