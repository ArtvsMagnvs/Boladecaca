# email_inbox.py — /api/email lectura: inbox, preview, detalle, busqueda, summary
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
