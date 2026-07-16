# app/memory/ingestion.py — Ingesta proactiva: email + calendario (V0.85 M2)
#
# Patron P3 (OpenHuman): sync en background hacia mem_personal para que
# Aithera ya tenga el contexto cuando el usuario pregunta. SIEMPRE via
# email_service/EmailTool y calendar_tool — NUNCA Gmail/Calendar directo
# (regla de capas doc 07 §2: endpoints -> MemoryRouter -> IMemoryStore).
#
# Dos jobs independientes (doc 07 §6):
#   - ingest_email(): cada MEMORY_INGEST_INTERVAL_MIN (default 20). Indexa
#     subject+snippet+sender, cruza EmailTriage ya calculado. NO llama al LLM.
#   - ingest_calendar(): cada 60 min. CalendarEvent local (-7..+14 dias) +
#     Google (calendar_tool, fail-soft; solo futuro, ver nota en _fetch_google_events).
#
# Cada pasada escribe un MemoryJobRun (auditable, con checkpoint). Si Google no
# esta conectado, la pasada es "ok, 0 items" sin ruido (fail-soft, doc 07 §6).
# [Δ doc 17] al terminar cada pasada CON items, emite memory.ingested; el
# triaje de cada email emite ademas email.triaged.
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from app.core.events import emit
from app.db.database import SessionLocal
from app.db.models import CalendarEvent, MemoryJobRun
from app.integrations import google_auth
from app.memory import MemoryType, memory_router
from app.services.email_service import _email_tool, get_triage_map

JOB_EMAIL = "memory_ingest_email"
JOB_CALENDAR = "memory_ingest_calendar"

EMAIL_MAX_RESULTS = 30  # tope por pasada — la cadencia (20 min) cubre el resto


# ---------------------------------------------------------------------------
# Tracking (MemoryJobRun)
# ---------------------------------------------------------------------------
def _start_run(job_name: str) -> int:
    db = SessionLocal()
    try:
        run = MemoryJobRun(job_name=job_name, started_at=datetime.utcnow(), status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id
    finally:
        db.close()


def _finish_run(
    run_id: int,
    *,
    status: str,
    items_processed: int = 0,
    error_detail: Optional[str] = None,
    checkpoint: Optional[dict] = None,
) -> None:
    db = SessionLocal()
    try:
        run = db.get(MemoryJobRun, run_id)
        if run is None:
            return
        run.finished_at = datetime.utcnow()
        run.status = status
        run.items_processed = items_processed
        run.error_detail = error_detail
        if checkpoint is not None:
            run.checkpoint = json.dumps(checkpoint, ensure_ascii=False)
        db.commit()
    finally:
        db.close()


def last_run(job_name: str) -> Optional[MemoryJobRun]:
    db = SessionLocal()
    try:
        return (
            db.query(MemoryJobRun)
            .filter(MemoryJobRun.job_name == job_name)
            .order_by(MemoryJobRun.id.desc())
            .first()
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
async def ingest_email() -> dict:
    """Una pasada de ingesta de email. Devuelve un resumen (para ingest/run)."""
    run_id = _start_run(JOB_EMAIL)
    try:
        if not google_auth.is_connected():
            _finish_run(run_id, status="ok", items_processed=0)
            return {"job": JOB_EMAIL, "status": "ok", "items_new": 0, "reason": "google_not_connected"}

        tool = _email_tool()
        resp = await tool.execute("list_inbox_preview", {"max_results": EMAIL_MAX_RESULTS})
        if not resp.get("success"):
            # Fail-soft: Gmail temporalmente inaccesible NO es un error de la
            # ingesta en si — se registra y la siguiente pasada reintenta.
            detail = resp.get("error") or "list_inbox_preview fallo"
            _finish_run(run_id, status="ok", items_processed=0, error_detail=detail)
            return {"job": JOB_EMAIL, "status": "ok", "items_new": 0, "reason": detail}

        items = (resp.get("result") or {}).get("items", [])
        triage_map = get_triage_map([it["id"] for it in items])
        last_id = None
        for it in items:
            category = triage_map.get(it["id"])  # None si aun no triado (doc 07 §6)
            content = f"{it.get('subject', '')}\n{it.get('snippet', '')}"
            await memory_router.store(
                content=content,
                memory_type=MemoryType.PERSONAL,
                source="email",
                metadata={
                    "kind": "inbox_item",
                    "email_id": it["id"],
                    "sender": it.get("from", ""),
                    "subject": it.get("subject", ""),
                    "category": category,
                    "email_date": it.get("date", ""),
                },
                dedup_key=it["id"],
            )
            if category:
                emit("email.triaged", source="mos", payload={"email_id": it["id"], "category": category})
            last_id = it["id"]

        checkpoint = {"last_email_id": last_id} if last_id else None
        _finish_run(run_id, status="ok", items_processed=len(items), checkpoint=checkpoint)
        if items:
            emit(
                "memory.ingested",
                source="mos",
                payload={"job": JOB_EMAIL, "items_new": len(items)},
            )
        return {"job": JOB_EMAIL, "status": "ok", "items_new": len(items)}
    except Exception as e:
        _finish_run(run_id, status="error", error_detail=f"{type(e).__name__}: {e}")
        return {"job": JOB_EMAIL, "status": "error", "items_new": 0, "reason": str(e)}


# ---------------------------------------------------------------------------
# Calendario
# ---------------------------------------------------------------------------
def _local_events(date_from, date_to) -> list[dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = (
            db.query(CalendarEvent)
            .filter(CalendarEvent.start_date >= date_from, CalendarEvent.start_date <= date_to)
            .all()
        )
        return [
            {
                "id": f"local:{r.id}",
                "title": r.title or "",
                "description": r.description or "",
                "start": r.start_date.isoformat() if r.start_date else "",
            }
            for r in rows
        ]
    finally:
        db.close()


async def _google_events() -> list[dict[str, Any]]:
    """Fail-soft: [] si Google no esta conectado o la llamada falla. NOTA: la
    accion list_events del CalendarTool solo cubre ventana futura (timeMin=now,
    doc calendar_tool.py) — el "-7 dias" del diseño lo cubren los CalendarEvent
    LOCALES (_local_events, sin esa limitacion). Extender CalendarTool con una
    ventana pasada queda fuera de alcance de M2 (no se toca sin necesidad real)."""
    if not google_auth.is_connected():
        return []
    try:
        from app.tools.calendar_tool import CalendarTool

        ct = CalendarTool()
        resp = await ct.execute("list_events", {"days_ahead": 14, "max_results": 100})
        if not resp.get("success"):
            return []
        return [
            {
                "id": f"google:{e['id']}",
                "title": e.get("title", ""),
                "description": e.get("description", ""),
                "start": e.get("start", ""),
            }
            for e in (resp.get("result") or {}).get("events", [])
        ]
    except Exception as e:
        print(f"[ingestion] _google_events fallo (fail-soft, solo local): {e}")
        return []


async def ingest_calendar() -> dict:
    """Una pasada de ingesta de calendario: local (-7..+14d, sin limite de
    Google) + Google (solo futuro, fail-soft)."""
    run_id = _start_run(JOB_CALENDAR)
    try:
        now = datetime.utcnow()
        date_from, date_to = now - timedelta(days=7), now + timedelta(days=14)
        events = _local_events(date_from, date_to) + await _google_events()

        for ev in events:
            content = f"{ev['title']}\n{ev['description']}".strip()
            if not content:
                continue
            await memory_router.store(
                content=content,
                memory_type=MemoryType.PERSONAL,
                source="calendar",
                metadata={"kind": "agenda_item", "event_id": ev["id"], "event_start": ev["start"]},
                dedup_key=f"cal:{ev['id']}",
            )

        _finish_run(run_id, status="ok", items_processed=len(events))
        if events:
            emit(
                "memory.ingested",
                source="mos",
                payload={"job": JOB_CALENDAR, "items_new": len(events)},
            )
        return {"job": JOB_CALENDAR, "status": "ok", "items_new": len(events)}
    except Exception as e:
        _finish_run(run_id, status="error", error_detail=f"{type(e).__name__}: {e}")
        return {"job": JOB_CALENDAR, "status": "error", "items_new": 0, "reason": str(e)}


# V0.9 (A2a): la programacion de estos jobs se movio a APScheduler (wiring en el
# lifespan de main.py). `ingest_email`/`ingest_calendar` (arriba) siguen siendo
# las funciones de trabajo — las llama el scheduler y tambien el endpoint
# POST /api/memory/ingest/run. Los antiguos `_loop`/`start_background_jobs`
# (asyncio.create_task) se retiraron: un solo planificador, mejor gestion.
