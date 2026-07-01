# backend/app/tools/calendar_tool.py
#
# V0.7 (Fase 4 Email + Calendar): herramienta de Google Calendar + disponibilidad manual.
#
# Acciones:
#   list_events             -> lista eventos proximos (Google Calendar)
#   get_event               -> evento especifico por id (Google)
#   create_event            -> crea evento (Google, requiere confirmacion)
#   find_free_slots         -> busca huecos libres respetando availability local + eventos Google
#   sync_to_aithera         -> sincroniza eventos Google -> BD local (calendar_events)
#   set_availability        -> anade/actualiza configuracion manual de disponibilidad
#   list_availability       -> lista bloques de disponibilidad manual configurados
#   delete_availability     -> elimina un bloque
#   clear_availability      -> borra toda la disponibilidad manual (reset)
#   get_day_status          -> estado agregado de un dia (libre / ocupado / mixto)
#
# DISENO: las acciones de disponibilidad (set/list/delete/clear/get_day_status)
# NO requieren Google OAuth. Funcionan contra la tabla local calendar_availability.
# Asi el usuario puede marcar sus bloques de tiempo libre/ocupado desde la UI
# o el chat sin tener cuenta Google.

import os
import json
import base64
from datetime import datetime, timedelta, time as dt_time, date as dt_date
from typing import Dict, Any, List, Optional

from .base import BaseTool
from app.integrations import google_auth
from app.db.database import SessionLocal
from app.db.models import CalendarAvailability, CalendarEvent


def _to_date(d) -> Optional[dt_date]:
    """Convierte un string/date/datetime a date."""
    if not d:
        return None
    if isinstance(d, dt_date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        try:
            # ISO format o YYYY-MM-DD
            if "T" in d:
                return datetime.fromisoformat(d).date()
            return datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _day_status_from_availability(rules: List[CalendarAvailability]) -> str:
    """Dado los bloques de un dia, devuelve el status agregado.
    Prioridad: si HAY AL MENOS un bloque unavailable -> unavailable
               si todo el dia es available -> available
               si hay bloques busy -> busy
               si no hay bloques -> neutral
    """
    if not rules:
        return "neutral"
    statuses = {r.status for r in rules}
    if "unavailable" in statuses:
        return "unavailable"
    if statuses == {"available"}:
        return "available"
    if statuses == {"busy"}:
        return "busy"
    return "mixed"


class CalendarTool(BaseTool):
    tool_id = "calendar"
    name = "Calendar Tool"
    description = (
        "Lee y crea eventos en Google Calendar. Tambien gestiona la disponibilidad "
        "manual del usuario (marcar dias/horas como available/unavailable/busy)."
    )
    requires_confirmation = False  # depende de la accion

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Acciones que NO requieren Google OAuth (availability local).
            if action == "set_availability":
                return await self._set_availability(params)
            if action == "list_availability":
                return await self._list_availability(params)
            if action == "delete_availability":
                return await self._delete_availability(params)
            if action == "clear_availability":
                return await self._clear_availability()
            if action == "get_day_status":
                return await self._get_day_status(params)

            # Acciones de Google Calendar - requieren OAuth (excepto find_free_slots
            # que mezcla eventos Google con availability local).
            handler = {
                "list_events": self._list_events,
                "get_event": self._get_event,
                "create_event": self._create_event,
                "find_free_slots": self._find_free_slots,
                "sync_to_aithera": self._sync_to_aithera,
            }.get(action)
            if not handler:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Accion desconocida: {action}",
                }
            # find_free_slots puede funcionar parcialmente sin OAuth (solo con availability).
            if action != "find_free_slots" and not google_auth.is_connected():
                return {
                    "success": False,
                    "result": None,
                    "error": "Google no esta conectado. Configura OAuth en Settings.",
                }
            creds = google_auth.get_credentials() if google_auth.is_connected() else None
            return await handler(creds, params)
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"{type(e).__name__}: {e}",
            }

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "list_events",
                "description": "Lista eventos proximos de Google Calendar.",
                "requires_confirmation": False,
                "params": {
                    "days_ahead": "int (default 7)",
                    "max_results": "int (default 20)",
                },
            },
            {
                "id": "get_event",
                "description": "Obtiene un evento por id (Google Calendar).",
                "requires_confirmation": False,
                "params": {"event_id": "string"},
            },
            {
                "id": "create_event",
                "description": "Crea un evento en Google Calendar. SIEMPRE requiere confirmacion.",
                "requires_confirmation": True,
                "params": {
                    "title": "string",
                    "start_datetime": "ISO datetime",
                    "end_datetime": "ISO datetime",
                    "description": "string opcional",
                    "attendees": "lista de emails opcional",
                },
            },
            {
                "id": "find_free_slots",
                "description": (
                    "Encuentra huecos libres en una fecha combinando eventos de Google "
                    "(si OAuth conectado) + disponibilidad manual local."
                ),
                "requires_confirmation": False,
                "params": {
                    "date": "string YYYY-MM-DD",
                    "duration_minutes": "int (default 60)",
                    "preferred_hours": "lista opcional de horas 0-23 (default [9..18])",
                },
            },
            {
                "id": "sync_to_aithera",
                "description": "Sincroniza eventos de Google Calendar a la tabla local calendar_events.",
                "requires_confirmation": False,
                "params": {"days_ahead": "int (default 30)"},
            },
            # --- Availability local (no requiere OAuth) ---
            {
                "id": "set_availability",
                "description": (
                    "Marca un bloque de tiempo como available/unavailable/busy. "
                    "Si hour_end <= hour_start o se omite, se interpreta como 'todo el dia'."
                ),
                "requires_confirmation": False,
                "params": {
                    "date": "string YYYY-MM-DD",
                    "hour_start": "int 0-23 (opcional, default 0)",
                    "hour_end": "int 1-24 (opcional, default 24)",
                    "status": "string: available | unavailable | busy",
                    "label": "string opcional (ej. 'Reunion cliente X')",
                },
            },
            {
                "id": "list_availability",
                "description": "Lista los bloques de disponibilidad manual configurados.",
                "requires_confirmation": False,
                "params": {
                    "from_date": "string YYYY-MM-DD opcional (default: hoy)",
                    "days_ahead": "int opcional (default 30)",
                },
            },
            {
                "id": "delete_availability",
                "description": "Elimina un bloque de disponibilidad por id.",
                "requires_confirmation": False,
                "params": {"id": "int"},
            },
            {
                "id": "clear_availability",
                "description": "Borra TODA la disponibilidad manual configurada.",
                "requires_confirmation": False,
                "params": {},
            },
            {
                "id": "get_day_status",
                "description": "Devuelve el estado agregado de un dia (libre/ocupado/no disponible/mixto).",
                "requires_confirmation": False,
                "params": {"date": "string YYYY-MM-DD"},
            },
        ]

    # ------------------------------------------------------------------
    # Availability local
    # ------------------------------------------------------------------

    async def _set_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        date_str = params.get("date", "")
        d = _to_date(date_str)
        if not d:
            return {"success": False, "result": None, "error": f"fecha invalida: {date_str!r}"}

        hour_start = int(params.get("hour_start", 0))
        hour_end = int(params.get("hour_end", 24))
        hour_start = max(0, min(hour_start, 23))
        hour_end = max(0, min(hour_end, 24))
        # Si hour_end <= hour_start, interpretamos como "todo el dia"
        if hour_end <= hour_start:
            hour_start, hour_end = 0, 24

        status = (params.get("status") or "available").strip()
        if status not in {"available", "unavailable", "busy"}:
            return {
                "success": False,
                "result": None,
                "error": f"status invalido: {status!r}. Valores: available, unavailable, busy",
            }

        label = (params.get("label") or "").strip() or None

        db = SessionLocal()
        try:
            # Si ya existe un bloque que cubre exactamente el mismo rango,
            # lo actualizamos. Si no, creamos uno nuevo.
            existing = db.query(CalendarAvailability).filter(
                CalendarAvailability.date == datetime.combine(d, dt_time()),
                CalendarAvailability.hour_start == hour_start,
                CalendarAvailability.hour_end == hour_end,
            ).first()
            if existing:
                existing.status = status
                existing.label = label
                existing.updated_at = datetime.utcnow()
                avail_id = existing.id
                created = False
            else:
                avail = CalendarAvailability(
                    date=datetime.combine(d, dt_time()),
                    hour_start=hour_start,
                    hour_end=hour_end,
                    status=status,
                    label=label,
                )
                db.add(avail)
                db.commit()
                db.refresh(avail)
                avail_id = avail.id
                created = True
            return {
                "success": True,
                "result": {
                    "id": avail_id,
                    "date": d.isoformat(),
                    "hour_start": hour_start,
                    "hour_end": hour_end,
                    "status": status,
                    "label": label,
                    "created": created,
                },
                "error": None,
            }
        finally:
            db.close()

    async def _list_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from_d = _to_date(params.get("from_date"))
        days_ahead = int(params.get("days_ahead", 30))
        days_ahead = max(1, min(days_ahead, 365))
        if not from_d:
            from_d = datetime.utcnow().date()
        to_d = from_d + timedelta(days=days_ahead)

        db = SessionLocal()
        try:
            blocks = db.query(CalendarAvailability).filter(
                CalendarAvailability.date >= datetime.combine(from_d, dt_time()),
                CalendarAvailability.date <= datetime.combine(to_d, dt_time()),
            ).order_by(CalendarAvailability.date.asc(), CalendarAvailability.hour_start.asc()).all()

            items = [
                {
                    "id": b.id,
                    "date": b.date.date().isoformat(),
                    "hour_start": b.hour_start,
                    "hour_end": b.hour_end,
                    "status": b.status,
                    "label": b.label,
                }
                for b in blocks
            ]
            return {
                "success": True,
                "result": {
                    "items": items,
                    "count": len(items),
                    "from_date": from_d.isoformat(),
                    "to_date": to_d.isoformat(),
                },
                "error": None,
            }
        finally:
            db.close()

    async def _delete_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        avail_id = params.get("id")
        if not avail_id:
            return {"success": False, "result": None, "error": "falta parametro: id"}
        try:
            avail_id = int(avail_id)
        except (TypeError, ValueError):
            return {"success": False, "result": None, "error": "id debe ser int"}

        db = SessionLocal()
        try:
            block = db.query(CalendarAvailability).filter(
                CalendarAvailability.id == avail_id
            ).first()
            if not block:
                return {
                    "success": False,
                    "result": None,
                    "error": f"bloque no encontrado: id={avail_id}",
                }
            db.delete(block)
            db.commit()
            return {"success": True, "result": {"id": avail_id, "deleted": True}, "error": None}
        finally:
            db.close()

    async def _clear_availability(self) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            n = db.query(CalendarAvailability).delete()
            db.commit()
            return {
                "success": True,
                "result": {"cleared": True, "count_before": int(n)},
                "error": None,
            }
        finally:
            db.close()

    async def _get_day_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        date_str = params.get("date", "")
        d = _to_date(date_str)
        if not d:
            return {"success": False, "result": None, "error": f"fecha invalida: {date_str!r}"}

        db = SessionLocal()
        try:
            rules = db.query(CalendarAvailability).filter(
                CalendarAvailability.date == datetime.combine(d, dt_time())
            ).all()
            status = _day_status_from_availability(rules)
            # Ademas, si Google esta conectado, contamos eventos de ese dia
            google_events_count = 0
            if google_auth.is_connected():
                try:
                    creds = google_auth.get_credentials()
                    from googleapiclient.discovery import build

                    def _list():
                        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
                        start = datetime.combine(d, dt_time()).isoformat() + "Z"
                        end = (datetime.combine(d, dt_time()) + timedelta(days=1)).isoformat() + "Z"
                        return service.events().list(
                            calendarId="primary",
                            timeMin=start,
                            timeMax=end,
                            singleEvents=True,
                            orderBy="startTime",
                        ).execute()

                    result = await asyncio_run_sync(_list)
                    google_events_count = len(result.get("items", []))
                except Exception:
                    pass

            return {
                "success": True,
                "result": {
                    "date": d.isoformat(),
                    "status": status,
                    "blocks": [
                        {
                            "id": r.id,
                            "hour_start": r.hour_start,
                            "hour_end": r.hour_end,
                            "status": r.status,
                            "label": r.label,
                        }
                        for r in rules
                    ],
                    "google_events_count": google_events_count,
                },
                "error": None,
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Google Calendar (requieren OAuth)
    # ------------------------------------------------------------------

    async def _list_events(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        from googleapiclient.discovery import build

        days_ahead = int(params.get("days_ahead", 7))
        days_ahead = max(1, min(days_ahead, 90))
        max_results = int(params.get("max_results", 20))
        max_results = max(1, min(max_results, 100))

        def _do():
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            now = datetime.utcnow().isoformat() + "Z"
            until = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"
            return service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=until,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

        result = await asyncio_run_sync(_do)
        events = [
            {
                "id": e["id"],
                "title": e.get("summary", ""),
                "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                "all_day": "date" in e.get("start", {}),
                "location": e.get("location"),
                "description": (e.get("description") or "")[:300],
            }
            for e in result.get("items", [])
        ]
        return {
            "success": True,
            "result": {"events": events, "count": len(events)},
            "error": None,
        }

    async def _get_event(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        from googleapiclient.discovery import build

        event_id = params.get("event_id")
        if not event_id:
            return {"success": False, "result": None, "error": "falta parametro: event_id"}

        def _do():
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            return service.events().get(calendarId="primary", eventId=event_id).execute()

        e = await asyncio_run_sync(_do)
        return {
            "success": True,
            "result": {
                "id": e["id"],
                "title": e.get("summary", ""),
                "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                "all_day": "date" in e.get("start", {}),
                "location": e.get("location"),
                "description": e.get("description", ""),
                "attendees": [a.get("email") for a in e.get("attendees", [])],
            },
            "error": None,
        }

    async def _create_event(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        from googleapiclient.discovery import build

        title = params.get("title", "")
        start_dt = params.get("start_datetime", "")
        end_dt = params.get("end_datetime", "")
        description = params.get("description", "")
        attendees = params.get("attendees", [])

        if not title or not start_dt or not end_dt:
            return {
                "success": False,
                "result": None,
                "error": "title, start_datetime y end_datetime son obligatorios",
            }

        def _do():
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            body = {
                "summary": title,
                "start": {"dateTime": start_dt},
                "end": {"dateTime": end_dt},
            }
            if description:
                body["description"] = description
            if attendees:
                body["attendees"] = [{"email": a} for a in attendees]
            return service.events().insert(calendarId="primary", body=body).execute()

        event = await asyncio_run_sync(_do)
        google_event_id = event.get("id")

        # B-05 (Fase 4b): tras crear el evento en Google Calendar, lo guardamos
        # tambien en la tabla local calendar_events (con el google_event_id) para
        # que la pagina Calendar de Aithera lo vea sin esperar a un sync manual.
        # Reglas: si ya existe una fila con ese google_event_id no creamos otra
        # (dedup). Si el guardado local falla, lo logueamos pero NO propagamos: el
        # evento ya existe en Google y eso es lo importante.
        if google_event_id:
            db = SessionLocal()
            try:
                exists = db.query(CalendarEvent).filter(
                    CalendarEvent.google_event_id == google_event_id
                ).first()
                if not exists:
                    start_local = datetime.fromisoformat(str(start_dt).replace("Z", ""))
                    end_local = datetime.fromisoformat(str(end_dt).replace("Z", ""))
                    db.add(CalendarEvent(
                        title=title,
                        description=description or None,
                        start_date=start_local,
                        end_date=end_local,
                        all_day=False,
                        google_event_id=google_event_id,
                    ))
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"[calendar_tool] _create_event: fallo al guardar en BD local "
                      f"(el evento ya existe en Google): {e}")
            finally:
                db.close()

        return {
            "success": True,
            "result": {"event_id": google_event_id, "html_link": event.get("htmlLink")},
            "error": None,
        }

    async def _find_free_slots(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        """Encuentra huecos libres combinando:
        - Eventos de Google Calendar (si OAuth conectado)
        - Bloques de disponibilidad manual del usuario (calendar_availability)
        """
        date_str = params.get("date", "")
        d = _to_date(date_str)
        if not d:
            return {"success": False, "result": None, "error": f"fecha invalida: {date_str!r}"}
        duration = int(params.get("duration_minutes", 60))
        duration = max(15, min(duration, 480))
        preferred_hours = params.get("preferred_hours")
        if preferred_hours is None:
            preferred_hours = list(range(9, 18))  # 9-17 default
        elif isinstance(preferred_hours, str):
            try:
                preferred_hours = json.loads(preferred_hours)
            except Exception:
                preferred_hours = list(range(9, 18))

        # 1) Bloques NO disponibles del usuario (availability local).
        db = SessionLocal()
        try:
            rules = db.query(CalendarAvailability).filter(
                CalendarAvailability.date == datetime.combine(d, dt_time())
            ).all()
            # Construimos set de horas marcadas como unavailable o busy
            unavailable_hours = set()
            for r in rules:
                if r.status in {"unavailable", "busy"}:
                    for h in range(r.hour_start, r.hour_end):
                        unavailable_hours.add(h)
        finally:
            db.close()

        # 2) Horas ocupadas por eventos Google (si OAuth).
        google_busy_hours = set()
        if creds:
            from googleapiclient.discovery import build

            def _list():
                service = build("calendar", "v3", credentials=creds, cache_discovery=False)
                start = datetime.combine(d, dt_time()).isoformat() + "Z"
                end = (datetime.combine(d, dt_time()) + timedelta(days=1)).isoformat() + "Z"
                return service.events().list(
                    calendarId="primary",
                    timeMin=start,
                    timeMax=end,
                    singleEvents=True,
                ).execute()

            try:
                result = await asyncio_run_sync(_list)
                for e in result.get("items", []):
                    start_str = e.get("start", {}).get("dateTime")
                    if not start_str:
                        continue
                    start_dt_obj = datetime.fromisoformat(start_str.replace("Z", ""))
                    end_str = e.get("end", {}).get("dateTime", start_str)
                    end_dt_obj = datetime.fromisoformat(end_str.replace("Z", ""))
                    # Marcamos las horas que ocupa este evento
                    cur = start_dt_obj
                    while cur < end_dt_obj:
                        google_busy_hours.add(cur.hour)
                        cur += timedelta(hours=1)
            except Exception:
                pass

        # 3) Calcular huecos libres
        all_busy = unavailable_hours | google_busy_hours
        slots = []
        i = 0
        while i < len(preferred_hours):
            h = preferred_hours[i]
            if h in all_busy:
                i += 1
                continue
            # Buscamos una racha contigua de horas libres >= duration
            j = i
            while j < len(preferred_hours) and preferred_hours[j] not in all_busy and (
                j == i or preferred_hours[j] == preferred_hours[j - 1] + 1
            ):
                j += 1
            racha_horas = j - i
            racha_minutos = racha_horas * 60
            if racha_minutos >= duration:
                slots.append({
                    "start": f"{d.isoformat()}T{preferred_hours[i]:02d}:00:00",
                    "end": f"{d.isoformat()}T{preferred_hours[i] + racha_horas:02d}:00:00",
                    "duration_minutes": racha_minutos,
                })
            i = j

        return {
            "success": True,
            "result": {
                "date": d.isoformat(),
                "duration_minutes": duration,
                "slots": slots,
                "count": len(slots),
                "unavailable_hours_local": sorted(unavailable_hours),
                "unavailable_hours_google": sorted(google_busy_hours),
            },
            "error": None,
        }

    async def _sync_to_aithera(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sincroniza eventos Google -> tabla local calendar_events."""
        from googleapiclient.discovery import build

        days_ahead = int(params.get("days_ahead", 30))
        days_ahead = max(1, min(days_ahead, 90))

        def _list():
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            now = datetime.utcnow().isoformat() + "Z"
            until = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"
            return service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=until,
                maxResults=200,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

        result = await asyncio_run_sync(_list)
        events = result.get("items", [])

        db = SessionLocal()
        try:
            inserted = 0
            updated = 0
            for e in events:
                google_id = e["id"]
                start_dt_obj = e.get("start", {}).get("dateTime")
                if not start_dt_obj:
                    continue
                start_dt_obj = datetime.fromisoformat(start_dt_obj.replace("Z", ""))
                end_dt_obj = datetime.fromisoformat(
                    (e.get("end", {}).get("dateTime") or start_dt_obj.isoformat()).replace("Z", "")
                )

                existing = db.query(CalendarEvent).filter(
                    CalendarEvent.google_event_id == google_id
                ).first()
                if existing:
                    existing.title = e.get("summary", "")
                    existing.start_date = start_dt_obj
                    existing.end_date = end_dt_obj
                    existing.location = e.get("location", "")
                    existing.description = (e.get("description") or "")[:500]
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    new_event = CalendarEvent(
                        title=e.get("summary", "(sin titulo)"),
                        start_date=start_dt_obj,
                        end_date=end_dt_obj,
                        location=e.get("location", ""),
                        description=(e.get("description") or "")[:500],
                        google_event_id=google_id,
                    )
                    db.add(new_event)
                    inserted += 1
            db.commit()
            return {
                "success": True,
                "result": {
                    "inserted": inserted,
                    "updated": updated,
                    "total_fetched": len(events),
                },
                "error": None,
            }
        finally:
            db.close()


# ----------------------------------------------------------------------
# Helpers (module-level)
# ----------------------------------------------------------------------

import asyncio as _asyncio


async def asyncio_run_sync(fn):
    return await _asyncio.get_event_loop().run_in_executor(None, fn)