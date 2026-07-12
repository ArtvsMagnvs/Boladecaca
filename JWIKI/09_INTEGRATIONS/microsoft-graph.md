# Microsoft Graph API — Outlook + Calendar

## Resumen

**Microsoft Graph API** es el equivalente Microsoft de Google Workspace APIs. Outlook Mail + Calendar + Teams + OneDrive. **NO integrado en Aithera V0.7.3** (solo Google).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Endpoints principales

| Endpoint | Función |
|---|---|
| `GET /v1.0/me/messages` | Listar emails Outlook |
| `POST /v1.0/me/sendMail` | Enviar email |
| `GET /v1.0/me/events` | Listar eventos Calendar |
| `POST /v1.0/me/events` | Crear evento |
| `GET /v1.0/me/drive/root/children` | Listar archivos OneDrive |
| `GET /v1.0/me/joinedTeams` | Listar Teams |

## Hello World (Outlook Mail)

```python
import msal
import httpx

# MSAL setup
app = msal.ConfidentialClientApplication(
    client_id="...",
    client_secret="...",
    authority="https://login.microsoftonline.com/common"
)

# Get token
flow = app.initiate_device_flow(scopes=["Mail.Read", "Mail.Send"])
result = app.acquire_token_by_device_flow(flow)
access_token = result["access_token"]

# API call
headers = {"Authorization": f"Bearer {access_token}"}
messages = httpx.get(
    "https://graph.microsoft.com/v1.0/me/messages?$top=10",
    headers=headers
).json()

for msg in messages["value"]:
    print(msg["subject"], msg["from"]["emailAddress"]["address"])
```

## Enviar email Outlook

```python
import base64
from email.mime.text import MIMEText

def create_outlook_message(to: str, subject: str, body: str) -> dict:
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    return {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}]
        },
        "saveToSentItems": "true"
    }

httpx.post(
    "https://graph.microsoft.com/v1.0/me/sendMail",
    headers=headers,
    json=create_outlook_message("to@example.com", "Subject", "Body")
)
```

## Calendar (Outlook)

```python
event = {
    "subject": "Reunión",
    "start": {"dateTime": "2026-07-15T10:00:00", "timeZone": "Europe/Madrid"},
    "end": {"dateTime": "2026-07-15T11:00:00", "timeZone": "Europe/Madrid"},
    "attendees": [
        {"emailAddress": {"address": "cliente@example.com"}, "type": "required"}
    ]
}

created = httpx.post(
    "https://graph.microsoft.com/v1.0/me/events",
    headers=headers,
    json=event
).json()
```

## OAuth2 + PKCE (Microsoft)

Microsoft también soporta OAuth2 + PKCE. Setup en Azure AD:

1. App registration en https://portal.azure.com.
2. Redirect URI: `http://localhost:8000/api/microsoft/auth/callback`.
3. API permissions: Mail.Read, Mail.Send, Calendars.ReadWrite.

## Webhooks (change notifications)

Microsoft Graph soporta **webhooks** via subscriptions:

```python
subscription = {
    "changeType": "created,updated",
    "notificationUrl": "https://aithera.com/api/microsoft/webhook",
    "resource": "/me/messages",
    "expirationDateTime": "2026-07-15T11:00:00Z",
    "clientState": "secret-verify-token"
}

httpx.post(
    "https://graph.microsoft.com/v1.0/subscriptions",
    headers=headers,
    json=subscription
)
```

## Para Aithera

- ❌ V0.7.3: NO integrado (solo Google).
- ⏳ V1.5+: Microsoft Graph support (Outlook + Teams + OneDrive).

## Pros y cons vs Google

| Aspecto | Microsoft Graph | Google |
|---|---|---|
| Mail API | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Calendar | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Teams | ⭐⭐⭐⭐⭐ (incluido) | ❌ |
| OneDrive | ⭐⭐⭐⭐⭐ (incluido) | ⭐⭐⭐⭐ |
| Auth setup | Azure AD (más complejo) | Cloud Console (más simple) |

## Referencias cruzadas

- [JWIKI-152 google-oauth-flow.md](./google-oauth-flow.md)
- [JWIKI-153 gmail-api.md](./gmail-api.md)

## Fuentes

1. https://learn.microsoft.com/en-us/graph/
2. https://learn.microsoft.com/en-us/graph/sdks/national-clouds

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified