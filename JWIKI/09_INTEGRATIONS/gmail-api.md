# Gmail REST API

## Resumen

**Gmail API** es el gateway de Aithera para leer, buscar y enviar emails. Usada en V0.7+. **44KB de código Aithera** (`backend/app/tools/email_tool.py`).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Endpoints principales

| Endpoint | Función | Aithera |
|---|---|---|
| `GET /gmail/v1/users/me/messages` | Listar mensajes | ✅ |
| `GET /gmail/v1/users/me/messages/{id}` | Obtener mensaje | ✅ |
| `GET /gmail/v1/users/me/threads` | Listar threads | ✅ |
| `POST /gmail/v1/users/me/messages/send` | Enviar email | ✅ |
| `POST /gmail/v1/users/me/labels` | Crear label | ✅ |
| `GET /gmail/v1/users/me/profile` | User profile | ✅ |

## Hello World

```python
from googleapiclient.discovery import build

gmail = build("gmail", "v1", credentials=creds)

# Listar últimos 10 mensajes
results = gmail.users().messages().list(userId="me", maxResults=10).execute()
messages = results.get("messages", [])

for msg in messages:
    full = gmail.users().messages().get(userId="me", id=msg["id"]).execute()
    print(f"From: {full['payload']['headers'][0]['value']}")
    print(f"Subject: {full['snippet']}")
```

## Enviar email

```python
import base64
from email.mime.text import MIMEText

def create_message(to: str, subject: str, body: str) -> dict:
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}

sent = gmail.users().messages().send(
    userId="me",
    body=create_message("to@example.com", "Subject", "Body")
).execute()
print(f"Sent: {sent['id']}")
```

## Search syntax

Gmail soporta query syntax:

```python
# Buscar emails no leídos
gmail.users().messages().list(
    userId="me",
    q="is:unread"
).execute()

# Buscar emails de un remitente
gmail.users().messages().list(
    userId="me",
    q="from:boss@company.com"
).execute()

# Buscar emails con attachment
gmail.users().messages().list(
    userId="me",
    q="has:attachment filename:pdf"
).execute()

# Combinaciones
gmail.users().messages().list(
    userId="me",
    q="is:unread from:boss@company.com newer_than:7d"
).execute()
```

## Aithera email_tool.py

`backend/app/tools/email_tool.py` (44KB) implementa:
- ✅ `list_inbox(max_results, query)`
- ✅ `get_message(message_id)`
- ✅ `send(to, subject, body, reply_to)`
- ✅ `mark_as_read(message_id)`
- ✅ `mark_as_spam(message_id)`
- ✅ `create_label(name)`
- ✅ `apply_label(message_id, label_id)`

## Push notifications (Pub/Sub)

Gmail soporta **push notifications** via Google Cloud Pub/Sub. **NO implementado en Aithera V0.7.3** (usa polling).

Para V0.85+:
1. Crear topic en Pub/Sub.
2. Watch request: `users.watch({labelIds: ['INBOX'], topicName: 'projects/...'})`.
3. Gmail publica eventos a Pub/Sub.
4. Aithera consume via subscription.

## Rate limits

- **250 quota units per user per second**.
- Sending: 100 units.
- Listing: 5 units.
- Watch: 100 units.

## Para Aithera

V0.7.3+: Gmail tool funcional.
V0.85+: push notifications (Pub/Sub).
V0.9+: webhooks para notificaciones instantáneas.

## Referencias cruzadas

- [JWIKI-152 google-oauth-flow.md](./google-oauth-flow.md)
- [JWIKI-166 auto-reply-patterns.md](./auto-reply-patterns.md)
- [JWIKI-167 meeting-detection.md](./meeting-detection.md)
- CLAUDE.md §8 (`email_tool.py`)

## Fuentes

1. https://developers.google.com/gmail/api/reference/rest
2. https://developers.google.com/gmail/api/guides/quota

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified