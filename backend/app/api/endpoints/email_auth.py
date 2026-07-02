# email_auth.py — /api/email OAuth + credenciales + status
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

