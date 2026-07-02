# email_processing.py — /api/email pipeline: process-inbox + process-test
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
    effective_rule_action,
    _email_tool,
    _parse_iso,
    detect_calendar_conflicts,
    _gcal_events_for_date,
    log_activity,
    _calendar_find_free_slots,
)

router = APIRouter(prefix="/email", tags=["email"])

@router.post("/process-inbox")
async def process_inbox(max_emails: int = Query(30, ge=1, le=100)):
    """V0.7 extra (FIX): procesa el inbox aplicando TODAS las reglas automaticas.

    Para cada email reciente:
      1) Carga todas las auto-reply rules habilitadas
      2) Comprueba si alguna matchea (por sender_emails o sender_domains)
      3) Si matchea:
         a) Si detect_meeting_with_ia=True: usa IA para detectar si propone reunion
            - Si es reunion + calendario ocupado: genera respuesta con nueva fecha
              (workflow de propuestas existente)
            - Si es reunion + calendario libre: guarda propuesta como 'pending'
         b) Si NO es reunion: usa reply_template
         c) Aplica la 'action' configurada:
            - auto_send: envia el email
            - create_draft: crea un borrador
            - alert_only: solo registra el evento

    Devuelve lista detallada de lo que se hizo con cada email.
    """
    if not google_auth.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Google no conectado. Conecta Google en Settings primero.",
        )

    creds = google_auth.get_credentials()
    tool = _email_tool()

    # 1) Listar inbox
    list_result = await tool.execute("list_inbox", {"max_results": max_emails})
    if not list_result.get("success"):
        raise HTTPException(status_code=500, detail=list_result.get("error"))
    msg_ids = [m["id"] for m in (list_result.get("result", {}).get("messages") or [])]

    if not msg_ids:
        return {"processed": [], "count": 0, "message": "Inbox vacio"}

    # 2) Cargar auto-reply rules habilitadas
    from app.db.database import SessionLocal as _SessionLocal
    from app.db.models import EmailAutoReplyRule
    db = _SessionLocal()
    try:
        # FIX (Fase 4b): 'app.utils.logger' no existe en el proyecto y hacia que
        # /process-inbox devolviera siempre 500. Usamos el logging estandar.
        import logging
        _logger = logging.getLogger("aithera.email_assistant")
        _logger.info("[process-inbox] INICIO carga de reglas")
        rules = db.query(EmailAutoReplyRule).filter(
            EmailAutoReplyRule.enabled == True  # noqa: E712
        ).all()
        _logger.info(f"[process-inbox] reglas encontradas: {len(rules)}")
        rules_data = []
        for r in rules:
            _logger.info(f"[process-inbox] rule id={r.id} sender_emails raw={r.sender_emails!r}")
            try:
                emails = json.loads(r.sender_emails or "[]")
            except Exception as ex:
                _logger.error(f"[process-inbox] json.loads fallo: {ex!r}")
                emails = []
            try:
                domains = json.loads(r.sender_domains or "[]")
            except Exception:
                domains = []
            _logger.info(f"[process-inbox] rule id={r.id} parsed emails={emails!r}")
            rules_data.append({
                "id": r.id,
                "name": r.name,
                "sender_emails": emails,
                "sender_domains": domains,
                "matching": r.matching,
                "pattern": r.pattern,
                "reply_template": r.reply_template,
                # V0.7.3 (Sprint 4, B6): gating de autonomia. Una regla en
                # 'propose' con auto_send se degrada a create_draft: el
                # usuario aprueba el borrador en Gmail antes de que salga.
                "action": effective_rule_action(
                    getattr(r, "action", "auto_send"),
                    getattr(r, "autonomy", "auto"),
                ),
                "raw_action": getattr(r, "action", "auto_send"),
                "autonomy": getattr(r, "autonomy", "auto") or "auto",
                "detect_meeting_with_ia": getattr(r, "detect_meeting_with_ia", True),
            })
    finally:
        db.close()

    processed = []
    # V0.7.1 (Fase 4b, Tarea 2.1): cap de rendimiento para la clasificacion IA
    # de emails SIN regla. classify_email() llama al LLM, asi que limitamos
    # cuantos emails sin regla clasificamos por pasada para no disparar la
    # latencia. La heuristica determinista (Oleada 3) reduce mas este coste.
    MAX_NO_RULE_CLASSIF = 10
    no_rule_classified = 0
    # Cache de eventos de Google Calendar por fecha (Tarea 2.4): evita llamar a
    # la API una vez por cada email que proponga reunion el mismo dia.
    gcal_cache: Dict[str, Any] = {}
    for mid in msg_ids[:max_emails]:
        # Obtener email
        email_resp = await tool.execute("get_email", {"email_id": mid})
        if not email_resp.get("success"):
            log_activity(
                action_type="error",
                sender="",
                subject="(error leyendo email)",
                details={"email_id": mid, "reason": email_resp.get("error")},
                email_id=mid,
            )
            continue
        email = email_resp["result"]
        sender = email.get("from", "")
        subject = email.get("subject", "")
        body = email.get("body_text", "")
        sender_email = _extract_email_address(sender)
        sender_domain = _extract_domain(sender)

        # 3) Buscar rule que matchee (multi-fuente, con prioridad)
        # V0.7 extra (FIX): orden de prioridad
        #   1) Reglas con sender_emails exactos (las mas especificas)
        #   2) Reglas con sender_domains
        #   3) Reglas legacy con matching+pattern (compatibilidad)
        # Esto evita que reglas legacy antiguas ganen a reglas nuevas mas
        # especificas que usan los nuevos campos.
        matched_rule = None
        # Primero: sender_emails exactos
        for r in rules_data:
            if r["sender_emails"] and sender_email in r["sender_emails"]:
                matched_rule = r
                break
        # Segundo: sender_domains
        if not matched_rule:
            for r in rules_data:
                if r["sender_domains"] and sender_domain in r["sender_domains"]:
                    matched_rule = r
                    break
        # Tercero: matching legacy (solo si NO hay reglas con sender_emails
        # o sender_domains activas que matcheen al sender)
        if not matched_rule:
            legacy_count = sum(1 for r in rules_data if r["sender_emails"] or r["sender_domains"])
            # Solo usar legacy si NO hay reglas con listas (las legacy son fallback)
            if legacy_count == 0:
                for r in rules_data:
                    if r["pattern"] and r["pattern"] != "*":
                        if r["matching"] == "sender_contains" and r["pattern"].lower() in sender.lower():
                            matched_rule = r
                            break
                        if r["matching"] == "subject_contains" and r["pattern"].lower() in subject.lower():
                            matched_rule = r
                            break
                        if r["matching"] == "sender_domain" and (
                            r["pattern"].lower() in sender_domain or sender_domain == r["pattern"].lower()
                        ):
                            matched_rule = r
                            break

        if not matched_rule:
            # B-04 (Fase 4b): antes de descartar un email sin regla, lo clasificamos
            # con IA. Si la IA lo marca como 'urgent' o 'meeting', lo registramos como
            # action='alert' (visible en el dashboard) en vez de 'skipped', para que
            # un email urgente/reunion sin regla no sea invisible. El resto sigue como
            # 'skipped'. Cap de rendimiento: primeros MAX_NO_RULE_CLASSIF sin regla.
            if no_rule_classified < MAX_NO_RULE_CLASSIF:
                no_rule_classified += 1
                classify_result = await tool.execute("classify_email", {"email_id": mid})
                if classify_result.get("success"):
                    classification = (classify_result.get("result") or {}).get("classification", {})
                    category = classification.get("category", "informational")
                    if category in ("urgent", "meeting"):
                        reason = classification.get("reason", "")
                        activity_id = log_activity(
                            action_type="alert",
                            sender=sender,
                            subject=subject,
                            snippet=body[:300],
                            details={
                                "reason": reason,
                                "category": category,
                                "no_rule_match": True,
                            },
                            email_id=mid,
                        )
                        processed.append({
                            "email_id": mid,
                            "subject": subject,
                            "sender": sender,
                            "action_taken": "alerta_sin_regla",
                            "alert": (
                                f"Email {'urgente' if category == 'urgent' else 'con reunion'} "
                                f"de {sender_email}: {subject}"
                            ),
                            "activity_id": activity_id,
                        })
                        continue
            # Sin regla y no urgente/reunion: se omite (no persistimos, seria ruido)
            processed.append({
                "email_id": mid,
                "subject": subject,
                "sender": sender,
                "skipped": "no hay regla que matchee",
            })
            continue

        # 4) Determinar si es reunion usando IA (independiente del clasificador)
        is_meeting = False
        meeting_dt = None
        meeting_reason = ""
        if matched_rule.get("detect_meeting_with_ia"):
            detection = await detect_meeting_proposal(subject=subject, body=body)
            is_meeting = detection.is_meeting_request
            meeting_dt = detection.datetime_iso
            meeting_reason = detection.reason

        # V0.7 extra (FIX usuario): si es reunion y detect_meeting_with_ia=True,
        # la IA SIEMPRE genera la respuesta completa (no usa plantilla).
        # Solo si NO es reunion, usamos la plantilla.

        # 5) Si es reunion: workflow de propuestas
        if is_meeting and meeting_dt:
            from app.tools.email_tool import (
                extract_meeting_datetime,
                generate_meeting_reschedule_reply,
                generate_meeting_accept_reply,
            )
            from app.db.models import MeetingProposal, CalendarAvailability
            proposed_dt = _parse_iso(meeting_dt) or _parse_iso(
                await extract_meeting_datetime(subject, body) or ""
            )
            if not proposed_dt:
                processed.append({
                    "email_id": mid,
                    "subject": subject,
                    "rule_used": matched_rule["name"],
                    "skipped": "IA detecto reunion pero no se pudo extraer fecha",
                })
                log_activity(
                    action_type="error",
                    sender=sender,
                    subject=subject,
                    snippet=body[:300],
                    details={"reason": "IA detecto reunion pero fecha invalida", "meeting_reason": meeting_reason},
                    rule_id=matched_rule["id"],
                    rule_name=matched_rule["name"],
                    email_id=mid,
                )
                continue

            # Verificar si ya tenemos propuesta confirmada
            db = SessionLocal()
            try:
                existing = db.query(MeetingProposal).filter(
                    MeetingProposal.email_id_original == mid
                ).first()
                if existing and existing.status == "confirmed":
                    processed.append({
                        "email_id": mid,
                        "subject": subject,
                        "rule_used": matched_rule["name"],
                        "skipped": "ya confirmada",
                    })
                    continue
            finally:
                db.close()

            # Comprobar disponibilidad (calendario local + Google Calendar).
            db = SessionLocal()
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
                # Fecha libre: IA genera aceptacion
                accept_body = await generate_meeting_accept_reply(
                    sender=sender,
                    subject=subject,
                    original_body=body,
                    confirmed_datetime_iso=meeting_dt,
                )
                if matched_rule["action"] == "auto_send":
                    send_result = await tool.execute("send_email", {
                        "to": sender_email,
                        "subject": f"Re: {subject}" if not subject.lower().startswith("re:") else subject,
                        "body": accept_body,
                    })
                    log_activity(
                        action_type="sent",
                        sender=sender,
                        subject=subject,
                        snippet=body[:300],
                        details={
                            "rule_id": matched_rule["id"],
                            "rule_name": matched_rule["name"],
                            "is_meeting": True,
                            "calendar_status": "libre",
                            "accepted_date": meeting_dt,
                            "reply_body_preview": accept_body[:200],
                            "message_id": (send_result.get("result") or {}).get("message_id"),
                            "sent": send_result.get("success", False),
                        },
                        rule_id=matched_rule["id"],
                        rule_name=matched_rule["name"],
                        email_id=mid,
                    )
                    processed.append({
                        "email_id": mid,
                        "subject": subject,
                        "rule_used": matched_rule["name"],
                        "is_meeting": True,
                        "calendar_status": "libre",
                        "action_taken": "aceptacion_enviada",
                        "sent": send_result.get("success", False),
                    })
                elif matched_rule["action"] == "create_draft":
                    draft_result = await tool.execute("create_draft", {
                        "to": sender_email,
                        "subject": f"Re: {subject}" if not subject.lower().startswith("re:") else subject,
                        "body": accept_body,
                    })
                    log_activity(
                        action_type="draft",
                        sender=sender,
                        subject=subject,
                        snippet=body[:300],
                        details={
                            "rule_id": matched_rule["id"],
                            "rule_name": matched_rule["name"],
                            "is_meeting": True,
                            "calendar_status": "libre",
                            "accepted_date": meeting_dt,
                            "reply_body_preview": accept_body[:200],
                            "draft_id": (draft_result.get("result") or {}).get("draft_id"),
                        },
                        rule_id=matched_rule["id"],
                        rule_name=matched_rule["name"],
                        email_id=mid,
                    )
                    processed.append({
                        "email_id": mid,
                        "subject": subject,
                        "rule_used": matched_rule["name"],
                        "is_meeting": True,
                        "calendar_status": "libre",
                        "action_taken": "borrador_creado",
                        "draft_id": (draft_result.get("result") or {}).get("draft_id"),
                    })
                else:  # alert_only
                    log_activity(
                        action_type="alert",
                        sender=sender,
                        subject=subject,
                        snippet=body[:300],
                        details={
                            "rule_id": matched_rule["id"],
                            "rule_name": matched_rule["name"],
                            "is_meeting": True,
                            "calendar_status": "libre",
                            "proposed_date": meeting_dt,
                            "reason": "Reunion propuesta, accion configurada como alert_only",
                            "preview_reply": accept_body[:300],
                        },
                        rule_id=matched_rule["id"],
                        rule_name=matched_rule["name"],
                        email_id=mid,
                    )
                    processed.append({
                        "email_id": mid,
                        "subject": subject,
                        "rule_used": matched_rule["name"],
                        "is_meeting": True,
                        "calendar_status": "libre",
                        "action_taken": "alerta_reunion_libre",
                        "alert": f"Reunion propuesta por {sender_email} para {proposed_dt.strftime('%d/%m %H:%M')} (estas libre)",
                    })
                continue

            # Fecha ocupada: buscar huecos libres
            from app.tools.calendar_tool import CalendarTool as _CalendarTool
            ct = _CalendarTool()
            cal_resp = await ct.execute("find_free_slots", {
                "date": proposed_dt.date().isoformat(),
                "duration_minutes": 60,
            })
            new_iso = None
            if cal_resp.get("success") and cal_resp.get("result", {}).get("slots"):
                new_iso = cal_resp["result"]["slots"][0]["start"]
            else:
                # Si no hay slots HOY, buscar manana / otros dias
                for offset in range(1, 14):
                    alt_date = (proposed_dt + timedelta(days=offset)).date()
                    alt_resp = await ct.execute("find_free_slots", {
                        "date": alt_date.isoformat(),
                        "duration_minutes": 60,
                    })
                    if alt_resp.get("success") and alt_resp.get("result", {}).get("slots"):
                        new_iso = alt_resp["result"]["slots"][0]["start"]
                        break

            if not new_iso:
                log_activity(
                    action_type="alert",
                    sender=sender,
                    subject=subject,
                    snippet=body[:300],
                    details={
                        "rule_id": matched_rule["id"],
                        "rule_name": matched_rule["name"],
                        "is_meeting": True,
                        "calendar_status": "ocupado",
                        "proposed_date": meeting_dt,
                        "reason": "ocupado y sin huecos libres en 14 dias",
                    },
                    rule_id=matched_rule["id"],
                    rule_name=matched_rule["name"],
                    email_id=mid,
                )
                processed.append({
                    "email_id": mid,
                    "subject": subject,
                    "rule_used": matched_rule["name"],
                    "skipped": "no hay huecos libres en 14 dias",
                })
                continue

            reschedule_body = await generate_meeting_reschedule_reply(
                sender=sender,
                subject=subject,
                original_body=body,
                original_proposed_iso=meeting_dt,
                new_proposed_iso=new_iso,
            )

            if matched_rule["action"] == "auto_send":
                send_result = await tool.execute("send_email", {
                    "to": sender_email,
                    "subject": f"Re: {subject}" if not subject.lower().startswith("re:") else subject,
                    "body": reschedule_body,
                })
                # Guardar propuesta
                db = SessionLocal()
                try:
                    prop = MeetingProposal(
                        email_id_original=mid,
                        sender=sender,
                        subject=subject,
                        body_snippet=(body or "")[:500],
                        original_proposed_datetime=proposed_dt,
                        counter_proposed_datetime=_parse_iso(new_iso),
                        status="counter_sent",
                        reply_email_id=((send_result.get("result") or {}).get("message_id")),
                        notes=f"auto-reasignado por regla '{matched_rule['name']}'",
                    )
                    db.add(prop)
                    db.commit()
                    prop_id = prop.id
                finally:
                    db.close()
                log_activity(
                    action_type="meeting_proposal",
                    sender=sender,
                    subject=subject,
                    snippet=body[:300],
                    details={
                        "rule_id": matched_rule["id"],
                        "rule_name": matched_rule["name"],
                        "is_meeting": True,
                        "calendar_status": "ocupado",
                        "original_date": meeting_dt,
                        "proposed_new_date": new_iso,
                        "reply_body_preview": reschedule_body[:200],
                        "proposal_id": prop_id,
                        "message_id": (send_result.get("result") or {}).get("message_id"),
                        "sent": send_result.get("success", False),
                    },
                    rule_id=matched_rule["id"],
                    rule_name=matched_rule["name"],
                    email_id=mid,
                )
                processed.append({
                    "email_id": mid,
                    "subject": subject,
                    "rule_used": matched_rule["name"],
                    "is_meeting": True,
                    "calendar_status": "ocupado",
                    "new_date_proposed": new_iso,
                    "action_taken": "contrapropuesta_enviada",
                    "sent": send_result.get("success", False),
                    "proposal_id": prop_id,
                })
            elif matched_rule["action"] == "create_draft":
                draft_result = await tool.execute("create_draft", {
                    "to": sender_email,
                    "subject": f"Re: {subject}" if not subject.lower().startswith("re:") else subject,
                    "body": reschedule_body,
                })
                db = SessionLocal()
                try:
                    prop = MeetingProposal(
                        email_id_original=mid,
                        sender=sender,
                        subject=subject,
                        body_snippet=(body or "")[:500],
                        original_proposed_datetime=proposed_dt,
                        counter_proposed_datetime=_parse_iso(new_iso),
                        status="draft",
                        notes=f"borrador de contrapropuesta por regla '{matched_rule['name']}'",
                    )
                    db.add(prop)
                    db.commit()
                    prop_id = prop.id
                finally:
                    db.close()
                log_activity(
                    action_type="draft",
                    sender=sender,
                    subject=subject,
                    snippet=body[:300],
                    details={
                        "rule_id": matched_rule["id"],
                        "rule_name": matched_rule["name"],
                        "is_meeting": True,
                        "calendar_status": "ocupado",
                        "original_date": meeting_dt,
                        "proposed_new_date": new_iso,
                        "reply_body_preview": reschedule_body[:200],
                        "draft_id": (draft_result.get("result") or {}).get("draft_id"),
                        "proposal_id": prop_id,
                    },
                    rule_id=matched_rule["id"],
                    rule_name=matched_rule["name"],
                    email_id=mid,
                )
                processed.append({
                    "email_id": mid,
                    "subject": subject,
                    "rule_used": matched_rule["name"],
                    "is_meeting": True,
                    "calendar_status": "ocupado",
                    "new_date_proposed": new_iso,
                    "action_taken": "borrador_contrapropuesta",
                    "draft_id": (draft_result.get("result") or {}).get("draft_id"),
                })
            else:  # alert_only
                log_activity(
                    action_type="alert",
                    sender=sender,
                    subject=subject,
                    snippet=body[:300],
                    details={
                        "rule_id": matched_rule["id"],
                        "rule_name": matched_rule["name"],
                        "is_meeting": True,
                        "calendar_status": "ocupado",
                        "original_date": meeting_dt,
                        "proposed_new_date": new_iso,
                        "reason": f"ESTAS OCUPADO el {meeting_dt}. Alternativa sugerida: {new_iso}",
                        "preview_reply": reschedule_body[:300],
                    },
                    rule_id=matched_rule["id"],
                    rule_name=matched_rule["name"],
                    email_id=mid,
                )
                processed.append({
                    "email_id": mid,
                    "subject": subject,
                    "rule_used": matched_rule["name"],
                    "is_meeting": True,
                    "calendar_status": "ocupado",
                    "new_date_proposed": new_iso,
                    "action_taken": "alerta_reunion_ocupado",
                    "alert": (
                        f"Reunion propuesta por {sender_email} para {proposed_dt.strftime('%d/%m %H:%M')} "
                        f"- ESTAS OCUPADO. Alternativa sugerida: {new_iso}"
                    ),
                })
            continue

        # 6) No es reunion: usar reply_template
        if not matched_rule.get("reply_template"):
            log_activity(
                action_type="skipped",
                sender=sender,
                subject=subject,
                snippet=body[:300],
                details={
                    "rule_id": matched_rule["id"],
                    "rule_name": matched_rule["name"],
                    "reason": "no es reunion y la regla no tiene plantilla",
                },
                rule_id=matched_rule["id"],
                rule_name=matched_rule["name"],
                email_id=mid,
            )
            processed.append({
                "email_id": mid,
                "subject": subject,
                "rule_used": matched_rule["name"],
                "skipped": "no es reunion y no hay plantilla",
            })
            continue

        reply_text = _render_template(matched_rule["reply_template"], sender, subject, body)
        if matched_rule["action"] == "auto_send":
            send_result = await tool.execute("send_email", {
                "to": sender_email,
                "subject": f"Re: {subject}" if not subject.lower().startswith("re:") else subject,
                "body": reply_text,
            })
            log_activity(
                action_type="sent",
                sender=sender,
                subject=subject,
                snippet=body[:300],
                details={
                    "rule_id": matched_rule["id"],
                    "rule_name": matched_rule["name"],
                    "is_meeting": False,
                    "reply_body_preview": reply_text[:200],
                    "message_id": (send_result.get("result") or {}).get("message_id"),
                    "sent": send_result.get("success", False),
                },
                rule_id=matched_rule["id"],
                rule_name=matched_rule["name"],
                email_id=mid,
            )
            processed.append({
                "email_id": mid,
                "subject": subject,
                "rule_used": matched_rule["name"],
                "is_meeting": False,
                "action_taken": "respuesta_enviada",
                "sent": send_result.get("success", False),
            })
        elif matched_rule["action"] == "create_draft":
            draft_result = await tool.execute("create_draft", {
                "to": sender_email,
                "subject": f"Re: {subject}" if not subject.lower().startswith("re:") else subject,
                "body": reply_text,
            })
            log_activity(
                action_type="draft",
                sender=sender,
                subject=subject,
                snippet=body[:300],
                details={
                    "rule_id": matched_rule["id"],
                    "rule_name": matched_rule["name"],
                    "is_meeting": False,
                    "reply_body_preview": reply_text[:200],
                    "draft_id": (draft_result.get("result") or {}).get("draft_id"),
                },
                rule_id=matched_rule["id"],
                rule_name=matched_rule["name"],
                email_id=mid,
            )
            processed.append({
                "email_id": mid,
                "subject": subject,
                "rule_used": matched_rule["name"],
                "is_meeting": False,
                "action_taken": "borrador_creado",
                "draft_id": (draft_result.get("result") or {}).get("draft_id"),
            })
        else:  # alert_only
            log_activity(
                action_type="alert",
                sender=sender,
                subject=subject,
                snippet=body[:300],
                details={
                    "rule_id": matched_rule["id"],
                    "rule_name": matched_rule["name"],
                    "is_meeting": False,
                    "reason": "email matchea regla con accion alert_only",
                    "preview_reply": reply_text[:300],
                },
                rule_id=matched_rule["id"],
                rule_name=matched_rule["name"],
                email_id=mid,
            )
            processed.append({
                "email_id": mid,
                "subject": subject,
                "rule_used": matched_rule["name"],
                "is_meeting": False,
                "action_taken": "alerta_solo",
                "alert": f"Email de {sender_email}: {subject}",
                "preview_reply": reply_text,
            })

    return {"processed": processed, "count": len(processed)}


# ----------------------------------------------------------------------
# V0.7 extra (FIX): endpoint de test para diagnosticar sin Google
# ----------------------------------------------------------------------

class ProcessTestPayload(BaseModel):
    """Simula un email entrante sin necesidad de Google conectado.
    Util para debug y para que el usuario pruebe el flujo de auto-reply
    antes de configurar Google."""
    sender: str
    subject: str
    body: str = ""
    rule_id: Optional[int] = None  # Si se especifica, usa esta regla


@router.post("/process-test")
async def process_test_email(payload: ProcessTestPayload):
    """V0.7 extra: simula el procesamiento de un email SIN Google.

    Pasos que ejecuta:
      1) Busca la regla que matchee el sender
      2) Si tiene detect_meeting_with_ia=True, pregunta a la IA si es reunion
      3) Si es reunion, mira calendario y propone contrapropuesta si ocupado
      4) Muestra exactamente que PASARIA si procesamos este email real

    NO envia emails ni crea drafts en Gmail. Solo hace el analisis.
    """
    from app.tools.email_tool import (
        detect_meeting_proposal,
        extract_meeting_datetime,
        generate_meeting_reschedule_reply,
        generate_meeting_accept_reply,
    )
    from app.tools.calendar_tool import CalendarTool as _CalendarTool
    from app.db.models import EmailAutoReplyRule
    from app.db.database import SessionLocal as _SessionLocal

    sender_email = _extract_email_address(payload.sender)
    sender_domain = _extract_domain(payload.sender)

    # 1) Buscar reglas que matcheen
    db = _SessionLocal()
    try:
        if payload.rule_id:
            rules = db.query(EmailAutoReplyRule).filter(
                EmailAutoReplyRule.id == payload.rule_id
            ).all()
        else:
            rules = db.query(EmailAutoReplyRule).filter(
                EmailAutoReplyRule.enabled == True  # noqa: E712
            ).all()
        matched_rules = []
        # V0.7 extra (FIX): orden de prioridad en el matching
        # 1) sender_emails exactos, 2) sender_domains, 3) legacy matching+pattern
        # Si multiples reglas matchean, gana la primera segun este orden.
        for r in rules:
            emails = _json.loads(r.sender_emails or "[]")
            domains = _json.loads(r.sender_domains or "[]")
            if emails and sender_email in emails:
                matched_rules.append({
                    "id": r.id, "name": r.name, "action": r.action,
                    "detect_meeting_with_ia": r.detect_meeting_with_ia,
                    "match_type": "sender_email",
                    "priority": 1,
                })
                continue
            if domains and sender_domain in domains:
                matched_rules.append({
                    "id": r.id, "name": r.name, "action": r.action,
                    "detect_meeting_with_ia": r.detect_meeting_with_ia,
                    "match_type": "sender_domain",
                    "priority": 2,
                })
                continue
            if r.pattern and r.pattern != "*":
                if r.matching == "sender_contains" and r.pattern.lower() in payload.sender.lower():
                    matched_rules.append({
                        "id": r.id, "name": r.name, "action": r.action,
                        "detect_meeting_with_ia": r.detect_meeting_with_ia,
                        "match_type": "sender_contains",
                        "priority": 3,
                    })
    finally:
        db.close()

    result = {
        "sender_parsed": {"email": sender_email, "domain": sender_domain},
        "matched_rules": matched_rules,
        "matched_rule": None,
        "steps": [],
    }
    # V0.7 extra (FIX): ordenar por prioridad (menor = mas especifica)
    if matched_rules:
        matched_rules.sort(key=lambda x: x.get("priority", 99))
        result["matched_rule"] = matched_rules[0]

    if not matched_rules:
        result["steps"].append({
            "step": "matching",
            "result": "NO_RULE_MATCHED",
            "explanation": f"Ninguna regla activa matchea el sender {sender_email}",
        })
        return result

    # Tomar la primera regla que matchee
    matched_rule_id = matched_rules[0]["id"]
    db = _SessionLocal()
    try:
        r = db.query(EmailAutoReplyRule).filter(EmailAutoReplyRule.id == matched_rule_id).first()
        rule_full = {
            "id": r.id, "name": r.name, "action": r.action,
            "detect_meeting_with_ia": r.detect_meeting_with_ia,
            "reply_template": r.reply_template,
            "sender_emails": json.loads(r.sender_emails or "[]"),
            "sender_domains": json.loads(r.sender_domains or "[]"),
        }
    finally:
        db.close()
    result["rule_used"] = rule_full

    # 2) Detectar si es reunion con IA
    if rule_full["detect_meeting_with_ia"]:
        detection = await detect_meeting_proposal(
            subject=payload.subject,
            body=payload.body,
        )
        # V0.7.1 (Fase 4b): detection es un MeetingDetection (dataclass frozen).
        # Lo serializamos con asdict() para la respuesta HTTP.
        import dataclasses as _dataclasses
        result["meeting_detection"] = _dataclasses.asdict(detection)
        result["steps"].append({
            "step": "ia_meeting_detection",
            "result": "IS_MEETING" if detection.is_meeting_request else "NOT_MEETING",
            "method": detection.method,
            "datetime_iso": detection.datetime_iso,
            "confidence": detection.confidence,
            "reason": detection.reason,
        })

        if not detection.is_meeting_request:
            result["final_action"] = {
                "would_do": "send_reply_with_template" if rule_full["reply_template"] else "skip",
                "action": rule_full["action"],
            }
            return result

        # 3) Es reunion: extraer fecha y mirar calendario
        dt_iso = detection.datetime_iso
        if not dt_iso:
            dt_iso = await extract_meeting_datetime(payload.subject, payload.body)
        if not dt_iso:
            result["steps"].append({
                "step": "calendar_check",
                "result": "NO_DATE_FOUND",
                "explanation": "IA detecto reunion pero no se pudo extraer fecha",
            })
            return result

        from datetime import datetime as _dt
        proposed_dt = _dt.fromisoformat(dt_iso.replace("Z", ""))

        # Mirar disponibilidad
        db = _SessionLocal()
        try:
            blocks = db.query(CalendarAvailability).filter(
                CalendarAvailability.date == _dt.combine(proposed_dt.date(), _dt.min.time())
            ).all()
            is_busy = any(
                b.status in {"unavailable", "busy"} and b.hour_start <= proposed_dt.hour < b.hour_end
                for b in blocks
            )
            day_blocks_info = [
                {"hour_start": b.hour_start, "hour_end": b.hour_end, "status": b.status, "label": b.label}
                for b in blocks
            ]
        finally:
            db.close()

        result["steps"].append({
            "step": "calendar_check",
            "proposed_date": dt_iso,
            "day_blocks": day_blocks_info,
            "is_busy": is_busy,
            "result": "BUSY" if is_busy else "FREE",
        })

        if not is_busy:
            # Libre: generar aceptacion
            accept_body = await generate_meeting_accept_reply(
                sender=payload.sender,
                subject=payload.subject,
                original_body=payload.body,
                confirmed_datetime_iso=dt_iso,
            )
            result["final_action"] = {
                "would_do": "send_accept_or_draft",
                "action": rule_full["action"],
                "ai_reply_preview": accept_body,
            }
            return result

        # Ocupado: buscar huecos libres
        ct = _CalendarTool()
        cal_resp = await ct.execute("find_free_slots", {
            "date": proposed_dt.date().isoformat(),
            "duration_minutes": 60,
        })
        new_iso = None
        if cal_resp.get("success") and cal_resp.get("result", {}).get("slots"):
            new_iso = cal_resp["result"]["slots"][0]["start"]
        else:
            for offset in range(1, 14):
                alt_date = (proposed_dt + timedelta(days=offset)).date()
                alt_resp = await ct.execute("find_free_slots", {
                    "date": alt_date.isoformat(),
                    "duration_minutes": 60,
                })
                if alt_resp.get("success") and alt_resp.get("result", {}).get("slots"):
                    new_iso = alt_resp["result"]["slots"][0]["start"]
                    break

        if not new_iso:
            result["steps"].append({
                "step": "find_free_slots",
                "result": "NO_FREE_SLOTS_IN_14_DAYS",
                "explanation": "Estas ocupado y no hay huecos libres en los proximos 14 dias",
            })
            result["final_action"] = {
                "would_do": "alert_only",
                "reason": "sin huecos libres",
            }
            return result

        result["steps"].append({
            "step": "find_free_slots",
            "result": "FOUND_SLOT",
            "proposed_new_date": new_iso,
        })

        reschedule_body = await generate_meeting_reschedule_reply(
            sender=payload.sender,
            subject=payload.subject,
            original_body=payload.body,
            original_proposed_iso=dt_iso,
            new_proposed_iso=new_iso,
        )
        result["final_action"] = {
            "would_do": "send_reschedule_or_draft",
            "action": rule_full["action"],
            "ai_reply_preview": reschedule_body,
        }
        return result
    else:
        # No detecta reuniones: usa plantilla
        if rule_full["reply_template"]:
            result["final_action"] = {
                "would_do": "send_with_template",
                "action": rule_full["action"],
                "reply_template": rule_full["reply_template"],
            }
        else:
            result["final_action"] = {
                "would_do": "skip",
                "reason": "detect_meeting_with_ia=False y sin plantilla",
            }
        return result


# ----------------------------------------------------------------------
# V0.7 extra: Workflow de propuestas de reunion automaticas
# ----------------------------------------------------------------------
#
# Flujo completo:
#   1) Llega email pidiendo reunion -> se clasifica
#   2) /api/email/process-meetings lo lee, extrae la fecha, mira calendario
#   3) Si esta ocupado -> genera respuesta IA con nueva fecha disponible
#      -> la envia -> guarda MeetingProposal con status='counter_sent'
