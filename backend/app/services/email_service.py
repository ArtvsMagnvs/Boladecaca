# app/services/email_service.py — logica compartida del dominio email
#
# V0.7.2 (Sprint 2, PLAN_MAESTRO_2026 B4): helpers extraidos del
# god-endpoint email_assistant.py. Primer inquilino real de app/services/
# (deuda CLAUDE.md 16.3).
#
# FIX (bug latente V0.7): el modulo original importaba `json as _json`
# pero log_activity/list_activity usaban `json.` a secas -> NameError
# silenciado por try/except. Resultado: EmailActivityLog NUNCA persistia.
# Aqui json se importa correctamente y log_activity funciona.

import json
from typing import Optional, Dict, Any
from datetime import datetime, time

from app.integrations import google_auth
from app.tools.email_tool import EmailTool, _extract_email_address
from app.db.database import SessionLocal
from app.db.models import EmailActivityLog

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _email_tool() -> EmailTool:
    """Helper: devuelve una instancia nueva de EmailTool (no tiene estado).
    El ToolManager singleton ya tiene una registrada pero necesitamos
    acceso directo aqui para invocar acciones especificas.
    """
    return EmailTool()

#      detecta -> si confirma, marca el dia como busy + status='confirmed'

def _parse_iso(s: str) -> Optional[datetime]:
    """Parsea ISO datetime (con o sin timezone)."""
    if not s:
        return None
    try:
        s = s.replace("Z", "")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def detect_calendar_conflicts(
    start: datetime,
    end: datetime,
    availability_blocks: list,
    google_events: Optional[list] = None,
) -> bool:
    """V0.7.1 (Fase 4b, patron GAIA, Tarea 3.3 + 2.4): funcion pura y testeable.

    Detecta si el intervalo [start, end) tiene conflicto contra:
      1) los bloques manuales de CalendarAvailability (status busy/unavailable)
      2) los eventos de Google Calendar (si se pasan)

    Half-open interval: dos reuniones consecutivas (back-to-back) NO son
    conflicto; solo el solapamiento real lo es.
    """
    # 1) Bloques locales de disponibilidad
    for block in (availability_blocks or []):
        if block.status not in {"unavailable", "busy"}:
            continue
        block_date = block.date.date() if hasattr(block.date, "date") else block.date
        block_start = datetime.combine(block_date, time(block.hour_start))
        # hour_end puede ser 24 (fin de dia); time(24) es invalido -> clamp.
        if block.hour_end >= 24:
            block_end = datetime.combine(block_date, time(23, 59, 59))
        else:
            block_end = datetime.combine(block_date, time(block.hour_end))
        if block_start < end and start < block_end:  # solapamiento half-open
            return True

    # 2) Eventos de Google Calendar
    for ev in (google_events or []):
        ev_start = _parse_iso(ev.get("start", ""))
        ev_end = _parse_iso(ev.get("end", ""))
        if ev_start and ev_end and ev_start < end and start < ev_end:
            return True

    return False


async def _gcal_events_for_date(target_date, cache: Dict[str, Any]) -> list:
    """V0.7.1 (Fase 4b, Tarea 2.4): eventos de Google Calendar para un dia.

    list_events() no acepta date_filter, asi que pedimos una ventana amplia y
    filtramos por fecha en Python. Cachea por fecha (para no llamar a la API por
    cada email del mismo dia dentro del loop). Fail-soft: si Google no esta
    conectado o la llamada falla, devuelve [] y se usa solo el calendario local.
    """
    key = target_date.isoformat()
    if key in cache:
        return cache[key]
    events: list = []
    try:
        if google_auth.is_connected():
            from app.tools.calendar_tool import CalendarTool as _CalendarTool
            ct = _CalendarTool()
            today = datetime.utcnow().date()
            days_ahead = max(1, (target_date - today).days + 1)
            resp = await ct.execute("list_events", {"days_ahead": days_ahead, "max_results": 100})
            if resp.get("success"):
                for ev in (resp.get("result") or {}).get("events", []):
                    ev_start = _parse_iso(ev.get("start", ""))
                    if ev_start and ev_start.date() == target_date:
                        events.append({"start": ev.get("start", ""), "end": ev.get("end", "")})
    except Exception as e:
        print(f"[email] _gcal_events_for_date fallo (uso solo calendario local): {e}")
        events = []
    cache[key] = events
    return events


def log_activity(
    action_type: str,
    sender: str = "",
    subject: str = "",
    snippet: str = "",
    details: Optional[Dict[str, Any]] = None,
    rule_id: Optional[int] = None,
    rule_name: Optional[str] = None,
    email_id: Optional[str] = None,
) -> Optional[int]:
    """V0.7 extra (FIX): persiste una accion en EmailActivityLog.

    Es el corazon del dashboard: cada vez que el sistema hace algo con un
    email, lo anota aqui para que el usuario lo vea.

    V0.7.1 (Fase 4b, Tarea 2.2): devuelve el ID de la entrada creada (o None
    si fallo) para que quien procesa el inbox pueda enlazar el item de
    'processed' con su entrada del dashboard.
    """
    sender_email = _extract_email_address(sender) if sender else ""
    db = SessionLocal()
    try:
        entry = EmailActivityLog(
            timestamp=datetime.utcnow(),
            action_type=action_type,
            sender=sender[:300] if sender else None,
            sender_email=sender_email[:300] if sender_email else None,
            subject=subject[:500] if subject else None,
            snippet=(snippet or "")[:1000],
            details=json.dumps(details or {}, ensure_ascii=False),
            rule_id=rule_id,
            rule_name=rule_name,
            email_id=email_id,
            read=False,
        )
        db.add(entry)
        db.commit()
        return entry.id
    except Exception as e:
        db.rollback()
        print(f"[email] log_activity error: {e}")
        return None
    finally:
        db.close()

async def _calendar_find_free_slots(creds, date_str: str, duration_minutes: int = 60) -> Dict[str, Any]:
    """Wrapper para llamar al CalendarTool.find_free_slots."""
    from app.tools.calendar_tool import CalendarTool
    ct = CalendarTool()
    return await ct.execute("find_free_slots", {
        "date": date_str,
        "duration_minutes": duration_minutes,
    })




# ----------------------------------------------------------------------
# Triaje del inbox — V0.7.3 (Sprint 3 PLAN_MAESTRO_2026, B5)
#
# Patron Inbox Zero + dos etapas (como meeting detection / AMD GAIA):
#   Etapa 1: heuristica barata (remitente + asunto + snippet), 0 coste.
#   Etapa 2: LLM (proveedor activo) SOLO para los ambiguos.
# Fail-soft: si el LLM no responde o responde basura -> 'fyi' con
# method='fallback'. El triaje nunca rompe el procesamiento del inbox.
# ----------------------------------------------------------------------

TRIAGE_CATEGORIES = (
    "urgente", "responder", "reunion", "newsletter",
    "factura", "spam-social", "fyi",
)

# Keywords por categoria (es + en). Orden de evaluacion = prioridad.
_TRIAGE_KEYWORDS = [
    ("urgente", (
        "urgent", "urgente", "asap", "immediately", "action required",
        "accion requerida", "warning", "alerta", "alert", "deletion",
        "suspended", "suspendida", "security", "seguridad", "deadline",
        "vence", "expira", "last chance", "ultimo aviso",
    )),
    ("factura", (
        "factura", "invoice", "receipt", "recibo", "payment", "pago",
        "billing", "cobro", "renovacion", "renewal", "presupuesto",
        "transferencia", "iban",
    )),
    ("reunion", (
        "meeting", "reunion", "reunión", "quedamos", "agendar", "cita",
        "llamada", "call", "zoom.us", "meet.google", "teams.microsoft",
        "calendar invite", "invitacion",
    )),
    ("spam-social", (
        "facebook", "instagram", "twitter", "linkedin", "tiktok",
        "te ha mencionado", "followed you", "liked your", "new follower",
        "comento tu", "friend request",
    )),
    ("newsletter", (
        "unsubscribe", "darse de baja", "cancelar suscripcion",
        "newsletter", "boletin", "boletín", "digest", "weekly update",
        "no-reply", "noreply", "mailing",
    )),
]


def heuristic_triage(subject: str, sender: str, snippet: str = "") -> Optional[str]:
    """Etapa 1: clasificacion por keywords. Devuelve None si es ambiguo
    (y por tanto debe decidir el LLM)."""
    text = f"{subject or ''} {sender or ''} {snippet or ''}".lower()
    for category, keywords in _TRIAGE_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return category
    return None


_TRIAGE_PROMPT = (
    "Clasifica este email en UNA de estas categorias exactas: "
    "urgente, responder, reunion, newsletter, factura, spam-social, fyi.\n"
    "- urgente: requiere atencion inmediata\n"
    "- responder: una persona espera respuesta del usuario\n"
    "- reunion: propone/confirma una reunion o llamada\n"
    "- newsletter: boletin o lista de correo\n"
    "- factura: factura, recibo o pago\n"
    "- spam-social: notificacion de red social o promocion\n"
    "- fyi: informativo, sin accion\n"
    "Responde SOLO con la palabra de la categoria, nada mas.\n\n"
    "De: {sender}\nAsunto: {subject}\nExtracto: {snippet}"
)


async def llm_triage(subject: str, sender: str, snippet: str = "") -> Optional[str]:
    """Etapa 2: pregunta al proveedor IA activo. Devuelve None si falla o
    la respuesta no es una categoria valida (el caller decide el fallback)."""
    try:
        from app.ai.ai_manager import ai_manager
        result = await ai_manager.chat(
            _TRIAGE_PROMPT.format(
                sender=(sender or "")[:200],
                subject=(subject or "")[:200],
                snippet=(snippet or "")[:300],
            ),
            system_prompt="Eres un clasificador de emails. Respondes con una sola palabra.",
        )
        if result.get("error"):
            return None
        answer = (result.get("response") or "").strip().lower()
        # tolerar respuestas tipo "categoria: reunion" o con puntuacion
        for cat in TRIAGE_CATEGORIES:
            if cat in answer:
                return cat
        return None
    except Exception as e:
        print(f"[email] llm_triage fallo (fail-soft): {e}")
        return None


async def triage_email(email_id: str, subject: str, sender: str, snippet: str = ""):
    """Clasifica un email (2 etapas) y devuelve (category, method)."""
    category = heuristic_triage(subject, sender, snippet)
    if category:
        return category, "heuristic"
    category = await llm_triage(subject, sender, snippet)
    if category:
        return category, "llm"
    return "fyi", "fallback"


def save_triage(email_id: str, sender: str, subject: str, category: str, method: str) -> None:
    """Upsert de la categoria en email_triage (idempotente por email_id)."""
    from app.db.models import EmailTriage
    db = SessionLocal()
    try:
        row = db.query(EmailTriage).filter(EmailTriage.email_id == email_id).first()
        if row:
            row.category = category
            row.method = method
        else:
            db.add(EmailTriage(
                email_id=email_id,
                sender=(sender or "")[:300],
                subject=(subject or "")[:500],
                category=category,
                method=method,
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[email] save_triage error: {e}")
    finally:
        db.close()


def get_triage_map(email_ids: list) -> Dict[str, str]:
    """Devuelve {email_id: category} para los ids dados (para enriquecer
    el inbox preview sin re-clasificar)."""
    if not email_ids:
        return {}
    from app.db.models import EmailTriage
    db = SessionLocal()
    try:
        rows = db.query(EmailTriage).filter(EmailTriage.email_id.in_(email_ids)).all()
        return {r.email_id: r.category for r in rows}
    finally:
        db.close()


# ----------------------------------------------------------------------
# Autonomia gradual por regla — V0.7.3 (Sprint 4, B6, patron Inbox Zero)
# ----------------------------------------------------------------------

PROMOTE_THRESHOLD = 5  # propuestas aprobadas netas para ofrecer 'auto'


def effective_rule_action(action: str, autonomy: str) -> str:
    """Gating de autonomia: una regla 'propose' con action='auto_send' se
    degrada a 'create_draft' (nada sale sin aprobacion del usuario).
    'create_draft' y 'alert_only' no cambian: ya son seguras."""
    if (action or "auto_send") == "auto_send" and (autonomy or "propose") == "propose":
        return "create_draft"
    return action or "auto_send"


def rule_can_promote(autonomy: str, approved: int, edited: int, rejected: int) -> bool:
    """True si la regla lleva saldo suficiente de aprobaciones para
    ofrecer subirla a 'auto' (aprobadas netas >= PROMOTE_THRESHOLD)."""
    if (autonomy or "propose") != "propose":
        return False
    return (approved or 0) - (edited or 0) - (rejected or 0) >= PROMOTE_THRESHOLD


# ----------------------------------------------------------------------
# Respuesta generada por IA (por regla) — V0.7.3b (Sprint 4b)
# ----------------------------------------------------------------------

_AI_REPLY_SYSTEM = (
    "Eres el asistente de email personal del usuario y escribes en su nombre. "
    "Escribe SOLO el cuerpo de la respuesta al email recibido. "
    "Reglas: responde en el mismo idioma del email recibido; tono natural y "
    "humano; breve y directo; sin asunto; sin placeholders tipo [Tu nombre]; "
    "no digas nunca que eres una IA ni que la respuesta es automatica; "
    "no inventes datos concretos (fechas, precios) que no esten en el email "
    "o en la instruccion del usuario."
)


async def generate_ai_reply(
    ai_prompt: str,
    sender: str,
    subject: str,
    body: str = "",
    extra_context: str = "",
) -> Optional[str]:
    """Genera la respuesta con el proveedor IA activo siguiendo la instruccion
    de la regla (ai_prompt). Fail-soft: None si el LLM falla o devuelve vacio
    (el caller decide fallback: plantilla o alerta)."""
    try:
        from app.ai.ai_manager import ai_manager
        message = (
            f"Instruccion del usuario para responder: {ai_prompt}\n"
            + (f"Contexto adicional: {extra_context}\n" if extra_context else "")
            + "\n--- EMAIL RECIBIDO ---\n"
            f"De: {(sender or '')[:200]}\n"
            f"Asunto: {(subject or '')[:200]}\n"
            f"Cuerpo:\n{(body or '')[:1500]}"
        )
        result = await ai_manager.chat(message, system_prompt=_AI_REPLY_SYSTEM)
        if result.get("error"):
            return None
        # FIX (2026-07-02): sin cadena de pensamiento (<think>) en emails
        from app.tools.email_tool import strip_reasoning
        text = strip_reasoning(result.get("response") or "")
        return text or None
    except Exception as e:
        print(f"[email] generate_ai_reply fallo (fail-soft): {e}")
        return None


def local_events_for_date(target_date) -> list:
    """FIX (2026-07-02, bug reportado por el usuario): el chequeo de conflictos
    solo miraba CalendarAvailability + Google Calendar e IGNORABA los eventos
    del calendario propio de Aithera (CalendarEvent, pagina Calendario).
    Resultado: una fecha marcada como ocupada en Aithera se daba por libre y
    el email de reunion se aceptaba en vez de contraproponer otra fecha.

    Devuelve los eventos locales del dia en el mismo formato que los de
    Google ({"start","end"} ISO) para concatenarlos en detect_calendar_conflicts.
    all_day bloquea el dia entero; sin end_date se asume 1 hora.
    """
    from datetime import timedelta
    from app.db.models import CalendarEvent
    events: list = []
    db = SessionLocal()
    try:
        rows = db.query(CalendarEvent).filter(
            CalendarEvent.start_date >= datetime.combine(target_date, time.min),
            CalendarEvent.start_date <= datetime.combine(target_date, time.max),
        ).all()
        for ev in rows:
            if ev.all_day:
                start = datetime.combine(target_date, time.min)
                end = datetime.combine(target_date, time(23, 59, 59))
            else:
                start = ev.start_date
                end = ev.end_date or (ev.start_date + timedelta(hours=1))
            events.append({"start": start.isoformat(), "end": end.isoformat()})
    except Exception as e:
        print(f"[email] local_events_for_date fallo (fail-soft, solo gcal+bloques): {e}")
    finally:
        db.close()
    return events


async def respond_to_email(email_id: str, mode: str, fallback_sender: str = "",
                           fallback_subject: str = "", fallback_body: str = "") -> Dict[str, Any]:
    """Accion manual desde el dashboard (2026-07-02, peticion usuario): dado un
    email concreto, ejecuta el workflow completo de respuesta AHORA.

    mode: 'draft' (crear borrador en Gmail) | 'send' (enviar ya).
    Es una orden explicita del usuario, asi que IGNORA la autonomia de la
    regla (el click es el consentimiento). Reusa el mismo pipeline que
    process-inbox: regla -> deteccion de reunion -> calendario (bloques +
    Google + eventos locales) -> aceptar / contraproponer / ai_prompt /
    plantilla.

    Devuelve {ok, action, reply_preview, meeting, calendar_status, detail}.
    """
    from datetime import timedelta
    from app.tools.email_tool import (
        check_auto_reply_match,
        detect_meeting_proposal,
        extract_meeting_datetime,
        generate_meeting_reschedule_reply,
        generate_meeting_accept_reply,
        _render_template,
        _extract_email_address,
    )
    from app.db.models import CalendarAvailability

    if mode not in {"draft", "send"}:
        return {"ok": False, "detail": f"mode invalido: {mode!r}"}

    tool = _email_tool()

    # 1) Recuperar el email real de Gmail (fallback: datos de la entrada)
    sender, subject, body = fallback_sender, fallback_subject, fallback_body
    reply_to_header = ""
    if email_id:
        fetched = await tool.execute("get_email", {"email_id": email_id})
        if fetched.get("success"):
            data = fetched.get("result") or {}
            sender = data.get("from") or data.get("sender") or sender
            reply_to_header = data.get("reply_to") or ""
            subject = data.get("subject") or subject
            body = data.get("body_text") or data.get("body") or data.get("snippet") or body

    # FIX (2026-07-02, bug reportado): la respuesta se envio al propio usuario.
    # Resolucion blindada del destinatario, en orden:
    #   1. Header Reply-To (estandar de email)
    #   2. Header From del email
    #   3. Sender guardado en la entrada del dashboard
    # Y NUNCA la propia cuenta conectada: si un candidato es mi propia
    # direccion se descarta y se prueba el siguiente.
    own_email = (google_auth.get_connected_email() or "").strip().lower()
    # Si el From del email resuelve a MI PROPIA cuenta (p.ej. un email que yo
    # mismo envie dentro del hilo), el remitente real para matching de reglas
    # y saludo es el guardado en la entrada del dashboard.
    if own_email and _extract_email_address(sender or "").strip().lower() == own_email:
        if _extract_email_address(fallback_sender or "").strip().lower() not in ("", own_email):
            sender = fallback_sender
    # OJO: el candidato elegido es SOLO el destinatario del envio;
    # 'sender' (el From) se conserva intacto para el matching de reglas
    # y para que la IA salude a la persona correcta.
    candidates = [reply_to_header, sender, fallback_sender]
    sender_email = ""
    for cand in candidates:
        addr = _extract_email_address(cand or "").strip().lower()
        if addr and addr != own_email:
            sender_email = addr
            break
    if not sender_email:
        return {
            "ok": False,
            "detail": (
                "no se pudo determinar un destinatario valido: todos los "
                f"candidatos resuelven a tu propia cuenta ({own_email}) o estan vacios. "
                "Puede que el email original sea uno enviado por ti."
            ),
        }

    # 2) Regla que matchea (para ai_prompt / plantilla / deteccion)
    match = check_auto_reply_match(sender=sender or "", subject=subject or "", body=body or "")
    ai_prompt = (match or {}).get("ai_prompt")
    template_text = (match or {}).get("reply_text") or ""
    detect_meetings = (match or {}).get("detect_meeting_with_ia", True)

    # 3) Es una reunion?
    reply_text = None
    meeting = False
    calendar_status = None
    new_date = None
    if detect_meetings:
        detection = await detect_meeting_proposal(subject=subject or "", body=body or "")
        if detection.is_meeting_request:
            meeting = True
            proposed_dt = _parse_iso(detection.datetime_iso or "") or _parse_iso(
                await extract_meeting_datetime(subject or "", body or "") or ""
            )
            if proposed_dt:
                db = SessionLocal()
                try:
                    day_blocks = db.query(CalendarAvailability).filter(
                        CalendarAvailability.date == datetime.combine(proposed_dt.date(), time.min)
                    ).all()
                finally:
                    db.close()
                gcal = await _gcal_events_for_date(proposed_dt.date(), {})
                busy_events = gcal + local_events_for_date(proposed_dt.date())
                is_busy = detect_calendar_conflicts(
                    proposed_dt, proposed_dt + timedelta(hours=1), day_blocks, busy_events,
                )
                if is_busy:
                    calendar_status = "ocupado"
                    # buscar hueco (hoy y hasta 14 dias)
                    for offset in range(0, 14):
                        alt = (proposed_dt + timedelta(days=offset)).date()
                        resp = await _calendar_find_free_slots(None, alt.isoformat(), 60)
                        slots = (resp.get("result") or {}).get("slots") if resp.get("success") else None
                        if slots:
                            new_date = slots[0]["start"]
                            break
                    if new_date:
                        reply_text = await generate_meeting_reschedule_reply(
                            sender=sender, subject=subject, original_body=body,
                            original_proposed_iso=proposed_dt.isoformat(),
                            new_proposed_iso=new_date,
                        )
                else:
                    calendar_status = "libre"
                    reply_text = await generate_meeting_accept_reply(
                        sender=sender, subject=subject, original_body=body,
                        confirmed_datetime_iso=proposed_dt.isoformat(),
                    )

    # 4) No reunion (o sin fecha): ai_prompt -> plantilla
    if not reply_text and ai_prompt:
        extra = ""
        if meeting and calendar_status == "ocupado":
            extra = "El usuario esta OCUPADO en la fecha propuesta: propon amablemente buscar otro dia."
        reply_text = await generate_ai_reply(ai_prompt, sender, subject, body, extra_context=extra)
    if not reply_text and template_text:
        reply_text = template_text
    if not reply_text:
        return {
            "ok": False, "meeting": meeting, "calendar_status": calendar_status,
            "detail": "no se pudo generar respuesta (sin regla aplicable, sin ai_prompt y sin plantilla)",
        }

    # 5) Ejecutar
    subject_reply = subject if (subject or "").lower().startswith("re:") else f"Re: {subject}"
    action = "create_draft" if mode == "draft" else "send_email"
    result = await tool.execute(action, {
        "to": sender_email, "subject": subject_reply, "body": reply_text,
    })
    if not result.get("success"):
        return {"ok": False, "detail": f"Gmail fallo: {result.get('error')}",
                "meeting": meeting, "calendar_status": calendar_status}

    log_activity(
        action_type="draft" if mode == "draft" else "sent",
        sender=sender, subject=subject, snippet=(body or "")[:300],
        details={
            "manual_action": True, "source": "dashboard_respond",
            "sent_to": sender_email,
            "meeting": meeting, "calendar_status": calendar_status,
            "new_date_proposed": new_date,
            "reply_body_preview": reply_text[:200],
            "rule_name": (match or {}).get("name"),
        },
        rule_id=(match or {}).get("rule_id"),
        rule_name=(match or {}).get("name"),
        email_id=email_id,
    )
    return {
        "ok": True,
        "action": "borrador_creado" if mode == "draft" else "respuesta_enviada",
        "sent_to": sender_email,
        "meeting": meeting,
        "calendar_status": calendar_status,
        "new_date_proposed": new_date,
        "reply_preview": reply_text[:300],
    }
