# email_activity.py — /api/email activity log (dashboard de acciones)
#
# V0.7.2 (Sprint 2, PLAN_MAESTRO_2026 B4): extraido del god-endpoint
# email_assistant.py (2038 lineas) SIN cambiar ninguna ruta publica.
# Los tests de contrato (tests/test_email_contracts.py) congelan la
# superficie /api/email; deben pasar identicos antes y despues.
#
# FIX incluido en el split: el modulo original solo tenia `import json
# as _json`, con lo que todo uso de `json.` (log_activity, list_activity,
# process-inbox) moria en silencio dentro de sus try/except. Aqui `json`
# se importa correctamente.

import json
import json as _json  # compat: algunas secciones usan el alias original
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.integrations import google_auth
from app.integrations.google_auth import get_credentials_source as google_get_credentials_source
from app.tools.email_tool import (
    EmailTool,
    check_auto_reply_match,
    asyncio_run_sync,
    _extract_email_address,
    _extract_domain,
    _render_template,
    _rule_matches,
    extract_meeting_datetime,
    generate_meeting_reschedule_reply,
    detect_meeting_confirmation,
    detect_meeting_proposal,
)
from app.db.database import SessionLocal
from app.db.models import MeetingProposal, CalendarAvailability, EmailActivityLog
from app.services.email_service import (
    _email_tool,
    _parse_iso,
    detect_calendar_conflicts,
    _gcal_events_for_date,
    log_activity,
    _calendar_find_free_slots,
)

router = APIRouter(prefix="/email", tags=["email"])

@router.get("/activity")
async def list_activity(
    action_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    only_unread: bool = Query(False),
):
    """V0.7 extra: lista el historial de actividad del Email Assistant.

    Devuelve las ultimas acciones en orden cronologico inverso. Soporta
    filtros por tipo (sent/draft/alert/meeting_proposal/etc) y por leido/no leido.
    """
    db = SessionLocal()
    try:
        q = db.query(EmailActivityLog)
        if action_type:
            q = q.filter(EmailActivityLog.action_type == action_type)
        if only_unread:
            q = q.filter(EmailActivityLog.read == False)  # noqa: E712
        entries = q.order_by(EmailActivityLog.timestamp.desc()).limit(limit).all()
        items = []
        for e in entries:
            try:
                details = json.loads(e.details or "{}")
            except Exception:
                details = {}
            items.append({
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "email_id": e.email_id,
                "sender": e.sender,
                "sender_email": e.sender_email,
                "subject": e.subject,
                "snippet": e.snippet,
                "action_type": e.action_type,
                "details": details,
                "rule_id": e.rule_id,
                "rule_name": e.rule_name,
                "read": e.read,
            })
        return {"items": items, "count": len(items)}
    finally:
        db.close()


@router.get("/activity/stats")
async def activity_stats():
    """V0.7 extra: contadores por tipo de accion (para los cards del dashboard)."""
    db = SessionLocal()
    try:
        # V0.7 extra: dos queries separadas (mas simple y robusto que CASE).
        total_rows = db.query(
            EmailActivityLog.action_type,
        ).all()
        unread_rows = db.query(
            EmailActivityLog.action_type,
        ).filter(EmailActivityLog.read == False).all()  # noqa: E712

        # Contar en Python (escala perfectamente para miles de entradas)
        from collections import Counter
        total_counts = Counter(r[0] for r in total_rows)
        unread_counts = Counter(r[0] for r in unread_rows)

        stats = {
            "sent": {"total": 0, "unread": 0},
            "draft": {"total": 0, "unread": 0},
            "alert": {"total": 0, "unread": 0},
            "meeting_proposal": {"total": 0, "unread": 0},
            "meeting_confirmed": {"total": 0, "unread": 0},
            "auto_replied": {"total": 0, "unread": 0},
            "error": {"total": 0, "unread": 0},
            "skipped": {"total": 0, "unread": 0},
        }
        # Mezclar todos los tipos que existan en la BD
        all_types = set(total_counts.keys()) | set(unread_counts.keys())
        for action_type in all_types:
            if action_type not in stats:
                stats[action_type] = {"total": 0, "unread": 0}
            stats[action_type]["total"] = total_counts.get(action_type, 0)
            stats[action_type]["unread"] = unread_counts.get(action_type, 0)
        return stats
    finally:
        db.close()


@router.post("/activity/{entry_id}/read", status_code=204)
async def mark_read(entry_id: int):
    """Marca una entrada como leida."""
    db = SessionLocal()
    try:
        entry = db.query(EmailActivityLog).filter(EmailActivityLog.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail=f"entrada no encontrada: id={entry_id}")
        entry.read = True
        db.commit()
        return None
    finally:
        db.close()


@router.post("/activity/mark-all-read", status_code=204)
async def mark_all_read():
    """Marca todas las entradas como leidas."""
    db = SessionLocal()
    try:
        n = db.query(EmailActivityLog).update({EmailActivityLog.read: True})
        db.commit()
        return None
    finally:
        db.close()


@router.delete("/activity/{entry_id}", status_code=204)
async def delete_activity_entry(entry_id: int):
    db = SessionLocal()
    try:
        entry = db.query(EmailActivityLog).filter(EmailActivityLog.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail=f"entrada no encontrada: id={entry_id}")
        db.delete(entry)
        db.commit()
        return None
    finally:
        db.close()


@router.delete("/activity", status_code=204)
async def clear_activity():
    """Borra todo el historial de actividad."""
    db = SessionLocal()
    try:
        n = db.query(EmailActivityLog).delete()
        db.commit()
        return None
    finally:
        db.close()

