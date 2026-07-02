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


