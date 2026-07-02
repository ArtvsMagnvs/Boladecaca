# email_auto_reply.py — /api/email reglas de auto-respuesta (CRUD + test + send)
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

