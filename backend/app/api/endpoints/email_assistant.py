# /api/email - Email Assistant (V0.7 Fase 4)
#
# Endpoints:
#   GET    /api/email/status                      -> { connected, email, has_credentials, libs_available }
#   POST   /api/email/auth/credentials           -> guarda client_id / client_secret en BD
#   GET    /api/email/auth/start                 -> inicia OAuth (abre browser)
#   DELETE /api/email/auth                       -> desconecta (borra token)
#
#   GET    /api/email/inbox                      -> lista emails (requiere OAuth)
#   GET    /api/email/{id}                       -> email completo (requiere OAuth)
#   GET    /api/email/search?q=...               -> busqueda (requiere OAuth)
#   POST   /api/email/draft                      -> crear borrador (requiere OAuth)
#   POST   /api/email/send                       -> enviar (requiere OAuth + body {confirmed: true})
#   GET    /api/email/summary                    -> resumen IA de los ultimos 20 emails
#
#   GET    /api/email/auto-reply/rules           -> lista reglas de auto-respuesta
#   POST   /api/email/auto-reply/rules           -> crea regla
#   PATCH  /api/email/auto-reply/rules/{id}      -> actualiza regla
#   DELETE /api/email/auto-reply/rules/{id}      -> elimina regla
#   POST   /api/email/auto-reply/test            -> prueba si un email matchea alguna regla
#   POST   /api/email/auto-reply/send            -> envia la respuesta de la regla (sin confirmacion)

import json as _json
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


router = APIRouter(prefix="/email", tags=["email"])


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _email_tool() -> EmailTool:
    """Helper: devuelve una instancia nueva de EmailTool (no tiene estado).
    El ToolManager singleton ya tiene una registrada pero necesitamos
    acceso directo aqui para invocar acciones especificas.
    """
    return EmailTool()


# ----------------------------------------------------------------------
# Auth / status
# ----------------------------------------------------------------------

@router.get("/status")
def get_status():
    return {
        "connected": google_auth.is_connected(),
        "email": google_auth.get_connected_email(),
        "has_credentials": google_auth.has_client_credentials(),
        "libs_available": google_auth.is_google_libs_available(),
        # V0.7 extra: indica de donde vienen las credenciales (env / db / none).
        # Asi el frontend sabe si el usuario las metio en .env o en la BD.
        "credentials_source": google_get_credentials_source(),
    }


class CredentialsPayload(BaseModel):
    client_id: str
    client_secret: str


@router.post("/auth/credentials")
def save_credentials(payload: CredentialsPayload):
    if not payload.client_id.strip() or not payload.client_secret.strip():
        raise HTTPException(status_code=400, detail="client_id y client_secret son obligatorios")
    ok = google_auth.save_client_credentials(payload.client_id.strip(), payload.client_secret.strip())
    if not ok:
        raise HTTPException(status_code=500, detail="no se pudieron guardar las credenciales")
    return {"saved": True}


@router.delete("/auth/credentials", status_code=204)
def delete_credentials():
    """V0.7 extra: borra las credenciales de la BD (no afecta a .env)."""
    from app.db.database import SessionLocal
    from app.db.models import Config
    db = SessionLocal()
    try:
        for key in ("google_client_id", "google_client_secret"):
            row = db.query(Config).filter(Config.key == key).first()
            if row:
                db.delete(row)
        db.commit()
        # Si hay token guardado, tambien lo borramos para empezar de cero.
        google_auth.disconnect()
        return None
    finally:
        db.close()


@router.post("/auth/start")
async def start_oauth():
    """Inicia el flujo OAuth abriendo el browser."""
    result = google_auth.start_oauth_flow()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "error desconocido"))
    return {"connected": True, "email": result.get("email")}


@router.delete("/auth", status_code=204)
def disconnect():
    google_auth.disconnect()
    return None


# ----------------------------------------------------------------------
# Gmail (requieren OAuth)
# ----------------------------------------------------------------------

@router.get("/inbox")
async def list_inbox(max_results: int = Query(20, ge=1, le=100), label: str = Query("INBOX")):
    tool = _email_tool()
    result = await tool.execute("list_inbox", {"max_results": max_results, "label": label})
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    # Para el inbox, queremos enriquecer con subject/sender/from. Para
    # no hacer N llamadas adicionales, dejamos que el frontend pida get_email
    # cuando quiera ver el detalle.
    return result["result"]


@router.get("/inbox/preview")
async def inbox_preview(max_emails: int = Query(15, ge=1, le=50)):
    """V0.7.1 (Fase 4b): bandeja de entrada enriquecida para la UI.

    Devuelve los ultimos emails con asunto, remitente, fecha, snippet y si estan
    sin leer (label UNREAD de Gmail). Read-only: no modifica nada.
    """
    if not google_auth.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Google no conectado. Conecta Google en Settings primero.",
        )
    tool = _email_tool()
    result = await tool.execute("list_inbox_preview", {"max_results": max_emails})
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


# V0.7 extra (FIX): ruta mas especifica (/email/{email_id}) para evitar
# conflictos con /activity y /proposals que antes se matcheaban como email_id.
@router.get("/email/{email_id}")
async def get_email(email_id: str):
    tool = _email_tool()
    result = await tool.execute("get_email", {"email_id": email_id})
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


@router.get("/search/query")
async def search_emails(q: str = Query(..., min_length=1), max_results: int = Query(20, ge=1, le=100)):
    tool = _email_tool()
    result = await tool.execute("search_emails", {"query": q, "max_results": max_results})
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


class DraftPayload(BaseModel):
    to: str
    subject: str
    body: str


@router.post("/draft")
async def create_draft(payload: DraftPayload):
    tool = _email_tool()
    result = await tool.execute("create_draft", payload.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


class SendPayload(BaseModel):
    to: str
    subject: str
    body: str
    confirmed: bool = False  # el frontend tiene que poner True para enviar


@router.post("/send")
async def send_email(payload: SendPayload):
    if not payload.confirmed:
        raise HTTPException(
            status_code=400,
            detail="El envio requiere confirmacion explicita (campo 'confirmed': true en el body).",
        )
    tool = _email_tool()
    result = await tool.execute("send_email", payload.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


@router.get("/summary")
async def summary():
    """Lee los ultimos 20 emails, los clasifica con IA y devuelve un resumen."""
    if not google_auth.is_connected():
        raise HTTPException(status_code=503, detail="Google no conectado")
    creds = google_auth.get_credentials()

    # 1) Listar 20 emails
    from googleapiclient.discovery import build

    def _list():
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=20).execute()

    listing = await asyncio_run_sync(_list)
    msg_ids = [m["id"] for m in listing.get("messages", [])]

    if not msg_ids:
        return {"summary": "No hay emails en INBOX.", "classified": []}

    # 2) Para cada email, sacar subject + from + snippet
    tool = _email_tool()
    classified = []
    for mid in msg_ids[:10]:  # top 10 para no tardar demasiado
        r = await tool.execute("get_email", {"email_id": mid})
        if r["success"]:
            email = r["result"]
            classification = await tool.execute("classify_email", {"email_id": mid})
            classified.append({
                "id": mid,
                "from": email.get("from"),
                "subject": email.get("subject"),
                "snippet": email.get("snippet"),
                "category": classification.get("result", {}).get("classification", {}).get("category", "informational") if classification.get("success") else "informational",
            })

    # 3) Resumen IA
    from app.ai.ai_manager import ai_manager
    lines = [f"- [{c['category']}] De {c['from']}: {c['subject']}" for c in classified]
    prompt = (
        "Dame un resumen ejecutivo (max 200 palabras) de estos emails. "
        "Destaca los urgentes y los follow-ups pendientes.\n\n"
        + "\n".join(lines)
    )
    ai_resp = await ai_manager.chat(
        message=prompt,
        system_prompt="Eres un asistente que resume bandejas de entrada de forma concisa.",
    )
    return {
        "summary": ai_resp.get("response", ""),
        "classified": classified,
    }


# ----------------------------------------------------------------------
# Auto-reply rules (NO requieren OAuth)
# ----------------------------------------------------------------------

@router.get("/auto-reply/rules")
async def list_auto_reply_rules():
    tool = _email_tool()
    result = await tool.execute("list_auto_reply_rules", {})
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


class AutoReplyRulePayload(BaseModel):
    """V0.7 extra (refactor): payload mas intuitivo.

    El usuario ya no tiene que entender "matching + pattern". En su lugar:
      - sender_emails: lista de emails exactos
      - sender_domains: lista de dominios
    Y elige la accion a tomar:
      - auto_send | create_draft | alert_only

    Los campos legacy (matching + pattern) se mantienen por compatibilidad,
    pero si se pasan sender_emails o sender_domains, esos tienen prioridad.
    """
    name: str
    # V0.7 extra: matching por listas (mas intuitivo)
    sender_emails: List[str] = []
    sender_domains: List[str] = []
    # V0.7 extra: accion a tomar
    action: str = "auto_send"  # auto_send | create_draft | alert_only
    detect_meeting_with_ia: bool = True
    # Legacy V0.7 (compatibilidad)
    matching: Optional[str] = None
    pattern: Optional[str] = None
    # Siempre presentes
    reply_template: str
    enabled: bool = True


@router.post("/auto-reply/rules", status_code=201)
async def add_auto_reply_rule(payload: AutoReplyRulePayload):
    tool = _email_tool()
    result = await tool.execute("add_auto_reply_rule", payload.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


@router.patch("/auto-reply/rules/{rule_id}")
async def update_auto_reply_rule(rule_id: int, payload: Dict[str, Any]):
    payload = {**payload, "id": rule_id}
    tool = _email_tool()
    result = await tool.execute("update_auto_reply_rule", payload)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


@router.delete("/auto-reply/rules/{rule_id}", status_code=204)
async def delete_auto_reply_rule(rule_id: int):
    tool = _email_tool()
    result = await tool.execute("delete_auto_reply_rule", {"id": rule_id})
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return None


class AutoReplyTestPayload(BaseModel):
    sender: str
    subject: str
    body: str = ""


@router.post("/auto-reply/test")
async def test_auto_reply(payload: AutoReplyTestPayload):
    """Devuelve que regla matchearia (si alguna) sin enviar nada."""
    tool = _email_tool()
    result = await tool.execute("test_auto_reply", payload.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result["result"]


class AutoReplySendPayload(BaseModel):
    sender: str
    subject: str
    body: str = ""
    """Si una regla matchea, envia la respuesta automaticamente.
    Devuelve que regla se uso y el resultado del envio."""
    email_id: Optional[str] = None


@router.post("/auto-reply/send")
async def send_auto_reply(payload: AutoReplySendPayload):
    """Envia la respuesta de la regla que matchea el email. NO pide confirmacion
    porque el usuario ya configuro la regla previamente (eso es el consentimiento).

    Si no hay regla que matchea, devuelve 200 con sent=False (no es error).
    Si hay regla y Google esta conectado, envia via Gmail.
    """
    match = check_auto_reply_match(
        sender=payload.sender,
        subject=payload.subject,
        body=payload.body,
    )
    if not match:
        return {
            "sent": False,
            "reason": "ninguna regla de auto-reply matchea este email",
        }
    # Tenemos una regla que matchea. Enviamos via Gmail.
    if not google_auth.is_connected():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Regla '{match['name']}' matchea pero Google no esta conectado. "
                "Conecta Google en Settings para que la auto-respuesta funcione."
            ),
        )
    # Invertimos el email: si me escribio mi jefe, yo respondo a mi jefe
    to_addr = _extract_email_address(payload.sender)
    subject_reply = payload.subject if payload.subject.lower().startswith("re:") else f"Re: {payload.subject}"
    body_reply = match["reply_text"]

    tool = _email_tool()
    send_result = await tool.execute("send_email", {
        "to": to_addr,
        "subject": subject_reply,
        "body": body_reply,
    })
    if not send_result.get("success"):
        return {
            "sent": False,
            "rule_used": match,
            "send_error": send_result.get("error"),
        }
    return {
        "sent": True,
        "rule_used": match,
        "send_result": send_result.get("result"),
    }


# ----------------------------------------------------------------------
# V0.7 extra (FIX del usuario): endpoint unificado que procesa el inbox
# combinando auto-reply rules + deteccion IA de reuniones en una sola pasada
# ----------------------------------------------------------------------

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
                "action": getattr(r, "action", "auto_send"),
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
#   4) Cuando el remitente responde /api/email/check-confirmations lo
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


async def _calendar_find_free_slots(creds, date_str: str, duration_minutes: int = 60) -> Dict[str, Any]:
    """Wrapper para llamar al CalendarTool.find_free_slots."""
    from app.tools.calendar_tool import CalendarTool
    ct = CalendarTool()
    return await ct.execute("find_free_slots", {
        "date": date_str,
        "duration_minutes": duration_minutes,
    })


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