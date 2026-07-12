# Email Tool — V0.7.3

## Resumen

**Email tool** (`backend/app/tools/email_tool.py`, **44KB**) es el tool más grande de Aithera. Implementa Gmail REST API + auto-reply + meeting detection.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Capabilities

- ✅ `list_inbox(max_results, query)` — listar emails.
- ✅ `get_message(message_id)` — obtener mensaje completo.
- ✅ `send(to, subject, body, reply_to)` — enviar.
- ✅ `mark_as_read(message_id)` — marcar como leído.
- ✅ `mark_as_spam(message_id)` — marcar spam.
- ✅ `create_label(name)` — crear Gmail label.
- ✅ `apply_label(message_id, label_id)` — aplicar label.
- ✅ `triage_inbox()` — clasificar 7 categorías.
- ✅ `detect_meeting_proposals(body)` — detectar reuniones.
- ✅ `send_auto_reply(rule, email)` — auto-reply.

## Architecture

```python
class EmailTool(BaseTool):
    name = "email"
    description = "Gmail operations + auto-reply + meeting detection"
    
    def __init__(self, gmail_service, ai_manager, memory):
        self.gmail = gmail_service
        self.ai = ai_manager
        self.memory = memory
    
    async def list_inbox(self, max_results=20, query=None) -> list[Email]:
        results = self.gmail.users().messages().list(
            userId="me", maxResults=max_results, q=query
        ).execute()
        return [await self._get_email(m["id"]) for m in results.get("messages", [])]
    
    async def send(self, to: str, subject: str, body: str, reply_to: str | None = None):
        message = create_message(to, subject, body)
        sent = self.gmail.users().messages().send(userId="me", body=message).execute()
        await self.log_activity("send", sent["id"], to)
        return sent
```

## Aithera V0.7.3 Email Assistant

CLAUDE.md §1: "Email Assistant TERMINADO":
- ✅ 7 categorías de triaje (heurística + LLM).
- ✅ Auto-reply rules (autonomía gradual).
- ✅ Meeting detection (2 etapas AMD GAIA).
- ✅ Activity log (digest diario).
- ✅ Bug fix V0.7.2 (json/log_activity).

## Integrations

- **Gmail API**: full CRUD.
- **Google Calendar**: cross-check conflicts.
- **ChromaDB**: search past emails.
- **AI Manager**: classify + extract meeting details.

## Para Aithera

- ✅ V0.7.3: email_tool completo (44KB).
- ⏳ V0.85+: Pub/Sub push notifications.
- ⏳ V1.0+: smart compose.

## Referencias cruzadas

- [JWIKI-153 gmail-api.md](../09_INTEGRATIONS/gmail-api.md)
- [JWIKI-166 auto-reply-patterns.md](../09_INTEGRATIONS/auto-reply-patterns.md)
- CLAUDE.md §1, §8

## Fuentes

1. CLAUDE.md §1, §8

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified