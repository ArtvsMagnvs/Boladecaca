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



@router.get("/digest")
async def daily_digest(date: Optional[str] = Query(None, description="YYYY-MM-DD; default hoy")):
    """V0.7.3 (Sprint 4, B7): digest diario del Email Assistant.

    Una sola llamada para la tarjeta del Hub y el briefing matinal (V0.9):
      - triage_counts: emails triados ese dia por categoria
      - urgent_pending: alertas sin leer en el dashboard
      - drafts_awaiting: borradores propuestos sin revisar (autonomia propose)
      - meetings: propuestas de reunion del dia + pendientes totales
      - rules: reglas activas y su autonomia
    Solo lee BD local: no llama a Gmail ni al LLM.
    """
    from datetime import date as _date
    from app.db.models import EmailTriage, EmailAutoReplyRule

    if date:
        try:
            target = _date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"fecha invalida: {date!r} (formato YYYY-MM-DD)")
    else:
        target = datetime.utcnow().date()

    db = SessionLocal()
    try:
        # 1) Triaje del dia por categoria
        triage_counts: Dict[str, int] = {}
        for row in db.query(EmailTriage).all():
            if row.created_at and row.created_at.date() == target:
                triage_counts[row.category] = triage_counts.get(row.category, 0) + 1

        # 2) Alertas urgentes sin leer
        urgent_pending = db.query(EmailActivityLog).filter(
            EmailActivityLog.action_type == "alert",
            EmailActivityLog.read == False,  # noqa: E712
        ).count()

        # 3) Borradores propuestos sin revisar
        drafts_awaiting = db.query(EmailActivityLog).filter(
            EmailActivityLog.action_type == "draft",
            EmailActivityLog.read == False,  # noqa: E712
        ).count()

        # 4) Reuniones
        proposals = db.query(MeetingProposal).all()
        meetings_today = sum(
            1 for p in proposals if p.created_at and p.created_at.date() == target
        )
        meetings_pending = sum(1 for p in proposals if (p.status or "") == "pending")

        # 5) Reglas
        rules = db.query(EmailAutoReplyRule).filter(
            EmailAutoReplyRule.enabled == True  # noqa: E712
        ).all()
        rules_summary = {
            "enabled": len(rules),
            "auto": sum(1 for r in rules if getattr(r, "autonomy", "auto") == "auto"),
            "propose": sum(1 for r in rules if getattr(r, "autonomy", "auto") == "propose"),
        }

        return {
            "date": target.isoformat(),
            "triage_counts": triage_counts,
            "triaged_total": sum(triage_counts.values()),
            "urgent_pending": urgent_pending,
            "drafts_awaiting": drafts_awaiting,
            "meetings": {"today": meetings_today, "pending": meetings_pending},
            "rules": rules_summary,
        }
    finally:
        db.close()


@router.post("/activity/{entry_id}/respond")
async def respond_from_activity(entry_id: int, mode: str = Query(..., pattern="^(draft|send)$")):
    """2026-07-02 (peticion usuario): actuar sobre una alerta del dashboard.

    mode=draft -> genera la propuesta como borrador en Gmail.
    mode=send  -> responde automaticamente YA.
    Ejecuta el pipeline completo (regla + reunion + calendario local/Google).
    El click del usuario es el consentimiento: ignora la autonomia de la regla.
    """
    from app.services.email_service import respond_to_email

    db = SessionLocal()
    try:
        entry = db.query(EmailActivityLog).filter(EmailActivityLog.id == entry_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail=f"entrada no encontrada: id={entry_id}")
        email_id = entry.email_id
        sender = entry.sender or ""
        subject = entry.subject or ""
        snippet = entry.snippet or ""
    finally:
        db.close()

    if not google_auth.is_connected():
        raise HTTPException(status_code=503, detail="Google no conectado")

    result = await respond_to_email(
        email_id=email_id or "", mode=mode,
        fallback_sender=sender, fallback_subject=subject, fallback_body=snippet,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("detail", "no se pudo responder"))

    # marcar la alerta original como leida (ya se ha actuado)
    db = SessionLocal()
    try:
        entry = db.query(EmailActivityLog).filter(EmailActivityLog.id == entry_id).first()
        if entry:
            entry.read = True
            db.commit()
    finally:
        db.close()
    return result
