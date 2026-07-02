# email_meetings.py — /api/email reuniones: process-meetings, check-confirmations, proposals
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


@router.post("/process-meetings")
async def process_meetings(max_emails: int = Query(10, ge=1, le=50)):
    """V0.7 extra: procesa emails recientes buscando peticiones de reunion.

    Para cada email:
      - Clasifica con IA
      - Si es 'meeting' o 'urgent' y contiene fecha propuesta
      - Mira calendario para esa fecha
      - Si esta ocupado: genera respuesta IA con nueva fecha disponible
      - Envia la respuesta y guarda MeetingProposal con status='counter_sent'

    Devuelve lista de propuestas creadas/procesadas.
    """
    if not google_auth.is_connected():
        raise HTTPException(status_code=503, detail="Google no conectado. Configura OAuth en Settings.")

    creds = google_auth.get_credentials()
    tool = _email_tool()

    # 1) Listar inbox
    list_result = await tool.execute("list_inbox", {"max_results": max_emails})
    if not list_result.get("success"):
        raise HTTPException(status_code=500, detail=list_result.get("error"))
    msg_ids = [m["id"] for m in (list_result.get("result", {}).get("messages") or [])]

    processed = []
    # Cache de eventos de Google Calendar por fecha (Tarea 2.4).
    gcal_cache: Dict[str, Any] = {}
    for mid in msg_ids[:max_emails]:
        # 2) Clasificar + leer
        classify = await tool.execute("classify_email", {"email_id": mid})
        if not classify.get("success"):
            continue
        category = classify.get("result", {}).get("classification", {}).get("category", "informational")
        if category not in {"meeting", "urgent"}:
            continue  # Solo procesamos reuniones

        email_data = await tool.execute("get_email", {"email_id": mid})
        if not email_data.get("success"):
            continue
        email = email_data["result"]

        # 3) Extraer fecha propuesta
        proposed_iso = await extract_meeting_datetime(
            subject=email.get("subject", ""),
            body=email.get("body_text", ""),
        )
        if not proposed_iso:
            processed.append({
                "email_id": mid,
                "subject": email.get("subject"),
                "category": category,
                "skipped": "no se pudo extraer fecha",
            })
            continue
        proposed_dt = _parse_iso(proposed_iso)
        if not proposed_dt:
            continue

        # 4) Ver si ya tenemos una propuesta para este email
        db = SessionLocal()
        try:
            existing = db.query(MeetingProposal).filter(
                MeetingProposal.email_id_original == mid
            ).first()
            if existing and existing.status == "confirmed":
                processed.append({
                    "email_id": mid,
                    "subject": email.get("subject"),
                    "category": category,
                    "skipped": "ya confirmada",
                })
                continue
        finally:
            db.close()

        # 5) Mirar si el dia/hora esta ocupado (calendario local + Google Calendar).
        # V0.7.1 (Fase 4b, Tareas 2.3/2.4/3.3): usamos la funcion pura
        # detect_calendar_conflicts() con half-open interval [start, end), que
        # elimina el bug previo de marcar 'busy' sin filtrar por hora.
        from app.db.database import SessionLocal as _Session
        db = _Session()
        try:
            day_blocks = db.query(CalendarAvailability).filter(
                CalendarAvailability.date == datetime.combine(proposed_dt.date(), datetime.min.time())
            ).all()
        finally:
            db.close()
        gcal_events = await _gcal_events_for_date(proposed_dt.date(), gcal_cache)
        is_busy = detect_calendar_conflicts(
            proposed_dt,
            proposed_dt + timedelta(hours=1),
            day_blocks,
            gcal_events,
        )

        if not is_busy:
            # Aceptamos la fecha. Guardamos propuesta 'pending' para tracking.
            db = SessionLocal()
            try:
                if not existing:
                    prop = MeetingProposal(
                        email_id_original=mid,
                        sender=email.get("from", ""),
                        subject=email.get("subject", ""),
                        body_snippet=(email.get("body_text") or "")[:500],
                        original_proposed_datetime=proposed_dt,
                        status="pending",
                        notes="fecha libre, sin necesidad de reasignar",
                    )
                    db.add(prop)
                    db.commit()
                processed.append({
                    "email_id": mid,
                    "subject": email.get("subject"),
                    "category": category,
                    "original_date": proposed_iso,
                    "free": True,
                    "action": "ninguno (fecha disponible)",
                })
            finally:
                db.close()
            continue

        # 6) Fecha ocupada -> buscar huecos libres
        date_str = proposed_dt.date().isoformat()
        cal_resp = await _calendar_find_free_slots(creds, date_str)
        if not cal_resp.get("success") or not cal_resp.get("result", {}).get("slots"):
            processed.append({
                "email_id": mid,
                "subject": email.get("subject"),
                "category": category,
                "skipped": "no hay slots libres en esa fecha",
            })
            continue
        new_slot = cal_resp["result"]["slots"][0]
        new_iso = new_slot["start"]

        # 7) Generar respuesta con IA
        reply_body = await generate_meeting_reschedule_reply(
            sender=email.get("from", ""),
            subject=email.get("subject", ""),
            original_body=email.get("body_text", ""),
            original_proposed_iso=proposed_iso,
            new_proposed_iso=new_iso,
        )

        # 8) Enviar respuesta
        to_addr = _extract_email_address(email.get("from", ""))
        subject_reply = email.get("subject", "") if email.get("subject", "").lower().startswith("re:") else f"Re: {email.get('subject', '')}"
        send_result = await tool.execute("send_email", {
            "to": to_addr,
            "subject": subject_reply,
            "body": reply_body,
        })
        if not send_result.get("success"):
            processed.append({
                "email_id": mid,
                "subject": email.get("subject"),
                "category": category,
                "skipped": f"error enviando: {send_result.get('error')}",
            })
            continue

        # 9) Guardar propuesta
        db = SessionLocal()
        try:
            if existing:
                existing.counter_proposed_datetime = _parse_iso(new_iso)
                existing.reply_email_id = (send_result.get("result") or {}).get("message_id")
                existing.status = "counter_sent"
                existing.notes = "reasignado por ocupacion"
                existing.updated_at = datetime.utcnow()
                prop_id = existing.id
            else:
                prop = MeetingProposal(
                    email_id_original=mid,
                    sender=email.get("from", ""),
                    subject=email.get("subject", ""),
                    body_snippet=(email.get("body_text") or "")[:500],
                    original_proposed_datetime=proposed_dt,
                    counter_proposed_datetime=_parse_iso(new_iso),
                    status="counter_sent",
                    reply_email_id=(send_result.get("result") or {}).get("message_id"),
                    notes="reasignado por ocupacion",
                )
                db.add(prop)
                db.commit()
                db.refresh(prop)
                prop_id = prop.id
        finally:
            db.close()

        processed.append({
            "email_id": mid,
            "subject": email.get("subject"),
            "category": category,
            "original_date": proposed_iso,
            "new_date": new_iso,
            "sent_reply": True,
            "reply_message_id": (send_result.get("result") or {}).get("message_id"),
            "proposal_id": prop_id,
        })

    return {"processed": processed, "count": len(processed)}


@router.post("/check-confirmations")
async def check_confirmations(max_emails: int = Query(20, ge=1, le=50)):
    """V0.7 extra: revisa emails recientes buscando confirmaciones de propuestas
    pendientes. Si encuentra una confirmacion:
      - Marca el dia/hora como 'busy' en calendar_availability
      - Actualiza MeetingProposal.status = 'confirmed'
      - Loguea en EmailActivityLog para que aparezca en el dashboard
    """
    if not google_auth.is_connected():
        raise HTTPException(status_code=503, detail="Google no conectado.")

    creds = google_auth.get_credentials()
    tool = _email_tool()

    list_result = await tool.execute("list_inbox", {"max_results": max_emails})
    if not list_result.get("success"):
        raise HTTPException(status_code=500, detail=list_result.get("error"))
    msg_ids = [m["id"] for m in (list_result.get("result", {}).get("messages") or [])]

    db = SessionLocal()
    try:
        pending = db.query(MeetingProposal).filter(
            MeetingProposal.status.in_(["counter_sent", "pending"])
        ).all()
        pending_by_sender = {}
        for p in pending:
            email = _extract_email_address(p.sender)
            if email:
                pending_by_sender.setdefault(email, []).append(p)
    finally:
        db.close()

    if not pending_by_sender:
        return {"checked": 0, "confirmed": []}

    confirmed = []
    checked = 0
    for mid in msg_ids[:max_emails]:
        checked += 1
        email_resp = await tool.execute("get_email", {"email_id": mid})
        if not email_resp.get("success"):
            continue
        email = email_resp["result"]
        sender_addr = _extract_email_address(email.get("from", ""))
        if not sender_addr or sender_addr not in pending_by_sender:
            continue
        confirmed_flag, new_dt_iso, reason = await detect_meeting_confirmation(
            sender_addr, email.get("subject", ""), email.get("body_text", "")
        )
        if not confirmed_flag:
            continue

        for prop in pending_by_sender[sender_addr]:
            target_dt = None
            if new_dt_iso:
                target_dt = _parse_iso(new_dt_iso)
            elif prop.counter_proposed_datetime:
                target_dt = prop.counter_proposed_datetime
            elif prop.original_proposed_datetime:
                target_dt = prop.original_proposed_datetime

            if not target_dt:
                continue

            db = SessionLocal()
            try:
                prop.status = "confirmed"
                prop.confirmation_email_id = mid
                prop.confirmed_at = datetime.utcnow()
                prop.updated_at = datetime.utcnow()
                prop.notes = f"Confirmado por email: {reason or 'si'}"

                block = CalendarAvailability(
                    date=datetime.combine(target_dt.date(), datetime.min.time()),
                    hour_start=target_dt.hour,
                    hour_end=target_dt.hour + 1,
                    status="busy",
                    label=f"Reunion: {prop.subject[:100]}",
                )
                db.add(block)
                db.commit()

                # V0.7 extra: log en dashboard
                log_activity(
                    action_type="meeting_confirmed",
                    sender=prop.sender,
                    subject=prop.subject,
                    snippet=(email.get("body_text") or "")[:300],
                    details={
                        "proposal_id": prop.id,
                        "confirmed_datetime": target_dt.isoformat(),
                        "block_id": block.id,
                        "reason": reason,
                    },
                )

                confirmed.append({
                    "proposal_id": prop.id,
                    "sender": prop.sender,
                    "subject": prop.subject,
                    "confirmed_datetime": target_dt.isoformat(),
                    "block_id": block.id,
                    "reason": reason,
                })
            except Exception as e:
                db.rollback()
                print(f"[check-confirmations] error: {e}")
            finally:
                db.close()

    return {"checked": checked, "confirmed": confirmed, "count": len(confirmed)}


# ----------------------------------------------------------------------
# V0.7 extra (FIX): Dashboard endpoints - persistencia y stats
# ----------------------------------------------------------------------


@router.get("/proposals")
async def list_proposals(status: Optional[str] = Query(None)):
    """V0.7 extra: lista las propuestas de reunion (todas o filtradas por status)."""
    db = SessionLocal()
    try:
        q = db.query(MeetingProposal).order_by(MeetingProposal.created_at.desc())
        if status:
            q = q.filter(MeetingProposal.status == status)
        props = q.limit(200).all()
        return {
            "proposals": [
                {
                    "id": p.id,
                    "email_id_original": p.email_id_original,
                    "sender": p.sender,
                    "subject": p.subject,
                    "body_snippet": (p.body_snippet or "")[:200],
                    "original_proposed_datetime": p.original_proposed_datetime.isoformat() if p.original_proposed_datetime else None,
                    "counter_proposed_datetime": p.counter_proposed_datetime.isoformat() if p.counter_proposed_datetime else None,
                    "status": p.status,
                    "reply_email_id": p.reply_email_id,
                    "confirmation_email_id": p.confirmation_email_id,
                    "notes": p.notes,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
                }
                for p in props
            ],
            "count": len(props),
        }
    finally:
        db.close()


@router.delete("/proposals/{proposal_id}", status_code=204)
async def delete_proposal(proposal_id: int):
    db = SessionLocal()
    try:
        p = db.query(MeetingProposal).filter(MeetingProposal.id == proposal_id).first()
        if not p:
            raise HTTPException(status_code=404, detail=f"propuesta no encontrada: id={proposal_id}")
        db.delete(p)
        db.commit()
        return None
    finally:
        db.close()