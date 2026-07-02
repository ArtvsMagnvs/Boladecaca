# email_compose.py — /api/email composicion: draft + send (con confirmacion)
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

