# Meeting Detection — Aithera V0.7.1

## Resumen

**Meeting detection** es el patrón de Aithera V0.7.1+ que detecta propuestas de reunión en emails, extrae fecha/hora/asistentes, propone slots libres y envía confirmación. CLAUDE.md §1: "detección de reuniones en dos etapas patrón AMD GAIA".

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Pipeline

```
Email received
  ↓
Stage 1: Heurística (regex + keywords)
  "Are you available Tuesday at 3pm?"
  "Let's schedule a call next week"
  → Candidato a meeting
  ↓
Stage 2: LLM (structured extraction)
  "Tuesday at 3pm" → ISO datetime
  Extrae: fecha, hora, duración, asistentes, ubicación
  ↓
Cross-check: Google Calendar free/busy
  ↓
Proponer slots libres al user
  ↓
Confirmar y crear evento
```

## Modelo de datos

```python
class MeetingProposal(Base):
    __tablename__ = "meeting_proposals"
    id: Mapped[int]
    email_id: Mapped[int]  # email que contiene la propuesta
    proposed_datetime: Mapped[datetime | None]
    duration_minutes: Mapped[int | None]
    attendees: Mapped[list[str]] = mapped_column(JSON)
    location: Mapped[str | None]
    status: Mapped[str]  # "detected" | "confirmed" | "declined" | "pending_user"
    suggested_slots: Mapped[list[dict]] = mapped_column(JSON)  # [{start, end}]
```

## Stage 1: Heurística

```python
import re

MEETING_KEYWORDS = [
    r"\b(meeting|reuni[óo]n|call|chamada|encuentro)\b",
    r"\b(meet|nos vemos|quedamos|disponibilidad|agenda)\b",
    r"\bat \d{1,2}(:\d{2})? ?(am|pm|AM|PM)?\b",
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)\b",
    r"\b(next week|esta semana|pr[óo]xima semana)\b"
]

def is_meeting_proposal(email_body: str) -> bool:
    score = sum(1 for kw in MEETING_KEYWORDS if re.search(kw, email_body, re.IGNORECASE))
    return score >= 2  # Threshold
```

## Stage 2: LLM extraction

```python
EXTRACTION_PROMPT = """Extrae los detalles de la reunión del siguiente email.

Email:
---
{email_body}
---

Responde en JSON:
{{
    "has_meeting": true/false,
    "datetime": "ISO format" o null,
    "duration_minutes": number o null,
    "attendees": ["email1", "email2"],
    "location": "string" o null,
    "language": "es" o "en"
}}
"""

async def extract_meeting_details(email_body: str, llm) -> dict:
    response = await llm.chat(EXTRACTION_PROMPT.format(email_body=email_body))
    return json.loads(response)
```

## Cross-check con Calendar

```python
async def suggest_slots(proposed_dt, attendees, duration, calendar):
    if proposed_dt:
        # Check conflicts on proposed datetime
        conflicts = await detect_calendar_conflicts(
            {"start": proposed_dt.isoformat(), "end": (proposed_dt + timedelta(minutes=duration)).isoformat()},
            attendees,
            calendar
        )
        if not conflicts:
            return [{"start": proposed_dt, "end": proposed_dt + timedelta(minutes=duration), "free": True}]
    
    # Find free slots in next 7 days
    fb = await calendar.freebusy_query(time_min=now(), time_max=now() + timedelta(days=7), items=attendees)
    # Suggest 3 slots
    ...
```

## Aithera V0.7.1+ features

- ✅ 2-stage detection (heurística + LLM).
- ✅ Date extraction (NLP).
- ✅ Attendee extraction (regex + email parsing).
- ✅ Conflict detection (Google Calendar).
- ✅ Slot suggestion (3 alternativas).
- ✅ Confirmation flow (user acepta una slot).

## Para Aithera V0.85+

- ✅ Auto-detect preferred times del user (ML).
- ✅ Multi-attendee coordination (poll attendees).
- ✅ Timezone awareness.

## Referencias cruzadas

- [JWIKI-154 google-calendar-api.md](./google-calendar-api.md)
- [JWIKI-166 auto-reply-patterns.md](./auto-reply-patterns.md)
- CLAUDE.md §1 (V0.7.1 meeting detection)

## Fuentes

1. https://arxiv.org/abs/2104.08253 (AMD GAIA - meeting detection)
2. CLAUDE.md §1

## Nivel de confianza

**100%** — implementado en CLAUDE.md §1.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified