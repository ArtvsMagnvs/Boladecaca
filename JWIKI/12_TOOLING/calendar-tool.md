# Calendar Tool — Aithera V0.7.3

## Resumen

**Calendar tool** (`backend/app/tools/calendar_tool.py`, 29KB) implementa Google Calendar API + availability + meeting proposals.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Capabilities

- ✅ `list_events(time_min, time_max)`
- ✅ `create_event(summary, start, end, attendees)`
- ✅ `update_event(event_id, ...)`
- ✅ `delete_event(event_id)`
- ✅ `check_availability(start, end, attendees)`
- ✅ `find_free_slots(duration_minutes, attendees)`
- ✅ `detect_conflicts(event)`

## Implementation

Ver [JWIKI-154 google-calendar-api.md](../09_INTEGRATIONS/google-calendar-api.md) para detalle completo.

## Aithera V0.7.1+ feature

CLAUDE.md §1: `detect_calendar_conflicts` con cross-check de Google Calendar:

```python
async def detect_calendar_conflicts(event, attendees, calendar):
    conflicts = []
    for attendee in attendees:
        fb = calendar.freebusy().query(body={...}).execute()
        if fb["calendars"][attendee]["busy"]:
            conflicts.append({"attendee": attendee, "conflicts": ...})
    return conflicts
```

## Para Aithera

- ✅ V0.7.3: calendar_tool completo.
- ⏳ V0.85+: recurring events.

## Referencias cruzadas

- [JWIKI-154 google-calendar-api.md](../09_INTEGRATIONS/google-calendar-api.md)
- [JWIKI-167 meeting-detection.md](../09_INTEGRATIONS/meeting-detection.md)
- CLAUDE.md §1, §8

## Fuentes

1. CLAUDE.md §1, §8

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified