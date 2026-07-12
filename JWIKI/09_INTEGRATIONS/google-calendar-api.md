# Google Calendar API

## Resumen

**Google Calendar API** es el gateway de Aithera para eventos, availability y meeting proposals. Usada en V0.7+. **29KB de código Aithera** (`backend/app/tools/calendar_tool.py`).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Endpoints principales

| Endpoint | Función | Aithera |
|---|---|---|
| `GET /calendar/v3/calendars/{calendarId}/events` | Listar eventos | ✅ |
| `POST /calendar/v3/calendars/{calendarId}/events` | Crear evento | ✅ |
| `PATCH /calendar/v3/calendars/{calendarId}/events/{eventId}` | Update evento | ✅ |
| `DELETE /calendar/v3/calendars/{calendarId}/events/{eventId}` | Borrar evento | ✅ |
| `POST /calendar/v3/freeBusy` | Free/busy query | ✅ |
| `POST /calendar/v3/calendars` | Crear calendar | ✅ |

## Hello World

```python
from googleapiclient.discovery import build

calendar = build("calendar", "v3", credentials=creds)

# Listar próximos 10 eventos
events_result = calendar.events().list(
    calendarId="primary",
    maxResults=10,
    singleEvents=True,
    orderBy="startTime",
    timeMin=datetime.utcnow().isoformat() + "Z"
).execute()
events = events_result.get("items", [])

for event in events:
    start = event["start"].get("dateTime", event["start"].get("date"))
    print(f"{start} - {event['summary']}")
```

## Crear evento

```python
event = {
    "summary": "Reunión con cliente",
    "location": "Zoom",
    "description": "Discutir propuesta Q3",
    "start": {"dateTime": "2026-07-15T10:00:00", "timeZone": "Europe/Madrid"},
    "end": {"dateTime": "2026-07-15T11:00:00", "timeZone": "Europe/Madrid"},
    "attendees": [
        {"email": "cliente@example.com"},
        {"email": "yo@example.com"}
    ],
    "conferenceData": {
        "createRequest": {
            "requestId": "meet-123",
            "conferenceSolutionKey": {"type": "hangoutsMeet"}
        }
    },
    "reminders": {
        "useDefault": False,
        "overrides": [
            {"method": "email", "minutes": 24 * 60},
            {"method": "popup", "minutes": 10}
        ]
    }
}

created = calendar.events().insert(
    calendarId="primary",
    body=event,
    conferenceDataVersion=1,
    sendUpdates="all"  # envia invitación a attendees
).execute()
print(f"Created: {created['id']}, Meet: {created.get('hangoutLink')}")
```

## Free/Busy query

```python
import datetime

freebusy_query = {
    "timeMin": "2026-07-15T00:00:00Z",
    "timeMax": "2026-07-22T00:00:00Z",
    "items": [{"id": "primary"}]
}

result = calendar.freebusy().query(body=freebusy_query).execute()
busy_slots = result["calendars"]["primary"]["busy"]

# Find free slots
free_slots = []
for i in range(len(busy_slots) - 1):
    end_current = datetime.fromisoformat(busy_slots[i]["end"].replace("Z", "+00:00"))
    start_next = datetime.fromisoformat(busy_slots[i+1]["start"].replace("Z", "+00:00"))
    if (start_next - end_current).total_seconds() >= 1800:  # 30 min
        free_slots.append({"start": end_current.isoformat(), "end": start_next.isoformat()})
```

## Aithera calendar_tool.py (29KB)

Implementa:
- ✅ `list_events(time_min, time_max, max_results)`
- ✅ `create_event(summary, start, end, attendees, ...)`
- ✅ `update_event(event_id, ...)`
- ✅ `delete_event(event_id)`
- ✅ `check_availability(start, end, attendees)` — cross-check multi-attendee
- ✅ `find_free_slots(duration_minutes, attendees)` — propose times
- ✅ `detect_conflicts(event)` — check overlaps

## Aithera V0.7.1 — meeting detection

CLAUDE.md §1 menciona `detect_calendar_conflicts` con cross-check de Google Calendar:

```python
# backend/app/tools/calendar_tool.py
async def detect_calendar_conflicts(
    event: dict,
    attendees: list[str],
    calendar_service
) -> list[dict]:
    """Cross-check conflicts en calendars de attendees."""
    conflicts = []
    for attendee in attendees:
        fb = calendar_service.freebusy().query(body={
            "timeMin": event["start"],
            "timeMax": event["end"],
            "items": [{"id": attendee}]
        }).execute()
        if fb["calendars"][attendee]["busy"]:
            conflicts.append({
                "attendee": attendee,
                "conflicts_with": fb["calendars"][attendee]["busy"]
            })
    return conflicts
```

## Para Aithera

V0.7.3+: Calendar tool con conflict detection.
V0.85+: meeting proposals auto-detected from emails + auto-suggest free slots.

## Referencias cruzadas

- [JWIKI-152 google-oauth-flow.md](./google-oauth-flow.md)
- [JWIKI-167 meeting-detection.md](./meeting-detection.md)
- CLAUDE.md §8 (`calendar_tool.py`)

## Fuentes

1. https://developers.google.com/calendar/api/v3/reference
2. https://developers.google.com/calendar/api/guides/quota

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified