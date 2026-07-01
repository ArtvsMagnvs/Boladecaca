# FASE 4 — V0.7: Email Assistant + Calendar Inteligente
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.7.0
**Prerrequisito**: Aithera V0.6.0 completada (Memory System funcionando)
**Sesiones**: 3

---

## CONTEXTO

El backend ya tiene `email_assistant.py` como esqueleto y la guía `GUIA-OAUTH-GOOGLE.md`. Esta fase lo convierte en funcional. El Email Assistant y el Calendar evolucionan — no se reemplazan.

---

## SESIÓN 1: OAuth Google + EmailTool

**Tiempo estimado**: 2-3 horas
**Empieza con**: Aithera V0.6.0 funcionando

### Paso 1 — Instalar dependencias

```bash
cd backend
pip install google-api-python-client==2.160.0 google-auth-oauthlib==1.2.1 google-auth-httplib2==0.2.0 --break-system-packages
```

Añadir a `backend/requirements.txt`:
```
google-api-python-client==2.160.0
google-auth-oauthlib==1.2.1
google-auth-httplib2==0.2.0
```

### Paso 2 — Crear `backend/app/integrations/google_auth.py`

```python
"""
Gestión centralizada de OAuth 2.0 para Google APIs.
Token guardado en: %APPDATA%/Aithera/google_token.json
"""
import os, json
from pathlib import Path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

TOKEN_PATH = Path(os.environ.get('APPDATA', '.')) / 'Aithera' / 'google_token.json'

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

def get_credentials() -> Optional[Credentials]:
    """Obtiene credenciales válidas. Refresca automáticamente si expiraron."""
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GOOGLE_SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return creds
    return None

def is_connected() -> bool:
    creds = get_credentials()
    return creds is not None and creds.valid

def start_oauth_flow(client_id: str, client_secret: str) -> Credentials:
    """
    Inicia el flujo OAuth. Abre el browser del sistema.
    Captura el código en http://localhost:8080.
    """
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8080"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, GOOGLE_SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=True)
    TOKEN_PATH.write_text(creds.to_json())
    return creds

def disconnect():
    """Borra el token guardado."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
```

### Paso 3 — EmailTool

Crear `backend/app/tools/email_tool.py` implementando `BaseTool` con estas acciones:

**`list_inbox`**: lista últimos N emails (`max_results: int = 20, label: str = "INBOX"`). Devuelve: `[{ id, subject, from, date, snippet, has_attachment }]`

**`get_email`**: contenido completo de un email (`email_id: str`). Devuelve: `{ id, subject, from, to, date, body_text, body_html }`

**`search_emails`**: búsqueda con sintaxis de Gmail (`query: str`). Ej: `"from:jefe@empresa.com subject:reunión"`.

**`create_draft`**: crea borrador sin enviar (`to, subject, body`). `requires_confirmation = False`.

**`send_email`**: envía email (`to, subject, body`). `requires_confirmation = True` — SIEMPRE.

**`classify_email`**: clasifica un email con IA (`email_id: str`):
```python
# Llama a ai_manager.chat() con este prompt:
prompt = f"""Clasifica este email en una categoría: urgent, follow_up, informational, spam.
Responde SOLO con JSON: {{"category": "...", "reason": "..."}}

De: {email['from']}
Asunto: {email['subject']}
Cuerpo: {email['body_text'][:500]}"""
```

### Paso 4 — Actualizar `backend/app/api/endpoints/email_assistant.py`

Reemplazar el esqueleto existente con implementación real:

```
GET /api/email/status         → { "connected": bool, "email": str | null }
GET /api/email/auth/url       → inicia OAuth, abre browser, devuelve { "auth_url": str }
GET /api/email/inbox          → lista de emails
GET /api/email/{id}           → email completo
GET /api/email/search?q=...   → búsqueda
POST /api/email/draft         → crear borrador
POST /api/email/send          → enviar (requiere campo "confirmed": true en el body)
GET /api/email/summary        → resumen IA de los últimos 20 emails
```

El endpoint `/summary`: lee 20 emails, clasifica cada uno, genera resumen con `ai_manager.chat()`.

### ✅ Checkpoint Sesión 1 — verificar antes de parar

- [ ] `pip install google-api-python-client ...` completado
- [ ] `GET /api/email/status` devuelve `{ "connected": false }` (sin OAuth aún)
- [ ] `GET /api/email/auth/url` abre el browser de Google correctamente
- [ ] Después de autorizar, `GET /api/email/status` devuelve `{ "connected": true, "email": "...@gmail.com" }`
- [ ] `GET /api/email/inbox` devuelve la bandeja de entrada real
- [ ] `classify_email` clasifica correctamente un email de prueba

### 🛑 Para aquí

Commit: `feat: EmailTool + OAuth Google`. La Sesión 2 implementa CalendarTool.

---

## SESIÓN 2: CalendarTool + UI de Email

**Tiempo estimado**: 2-3 horas
**Empieza con**: OAuth funcionando, EmailTool operativo

### Paso 1 — CalendarTool

Crear `backend/app/tools/calendar_tool.py` implementando `BaseTool`:

**`list_events`**: eventos próximos (`days_ahead: int = 7, max_results: int = 20`). Devuelve: `[{ id, title, start, end, all_day, location, description }]`

**`get_event`**: evento específico (`event_id: str`).

**`create_event`**: crea evento en Google Calendar (`title, start_datetime, end_datetime, description, attendees`). `requires_confirmation = True`.

**`find_free_slots`**: encuentra huecos libres (`date: str, duration_minutes: int = 60, preferred_hours: list = [9..18]`). Consulta la agenda y devuelve slots disponibles.

**`sync_to_aithera`**: sincroniza eventos de Google Calendar a la BD local de Aithera (`days_ahead: int = 30`). Inserta o actualiza en la tabla `calendar_events`.

### Paso 2 — Nuevos endpoints de calendario

Añadir en `backend/app/api/endpoints/calendar.py` sin quitar los existentes:

```
GET /api/calendar/google/events              → eventos de Google Calendar
POST /api/calendar/google/create             → crear evento (requiere confirmación)
GET /api/calendar/availability?date=...&duration=60  → slots libres
POST /api/calendar/sync                      → sincronizar Google → BD local
```

### Paso 3 — UI de Email

Actualizar `frontend/src/pages/Email.tsx` (actualmente esqueleto):

**Si no conectado a Google**:
- Botón "Conectar Google" → llama `GET /api/email/auth/url` → abre el flujo
- Instrucciones breves para crear credenciales en Google Cloud Console

**Si conectado**:
- Panel superior: botón "Resumen del día" → llama `/summary`, muestra en modal
- Lista de emails con categoría de color: rojo (urgent), amarillo (follow_up), gris (informational), negro (spam)
- Clic en email → modal con contenido completo
- Modal email tiene: botón "Crear borrador de respuesta" (llama a `create_draft`)
- Botón "Enviar" solo en el modal de borrador, con confirmación explícita ("¿Confirmas el envío?")
- Botón "Sincronizar" → `POST /api/calendar/sync` para sincronizar calendario

### ✅ Checkpoint Sesión 2 — verificar antes de parar

- [ ] `GET /api/calendar/google/events` devuelve eventos reales de Google Calendar
- [ ] `GET /api/calendar/availability?date=2026-07-01&duration=60` devuelve slots libres
- [ ] `POST /api/calendar/sync` sincroniza eventos a la BD local
- [ ] La UI de Email muestra la bandeja de entrada con categorías de color
- [ ] Clic en un email abre el modal con el contenido
- [ ] "Crear borrador" crea un draft en Gmail (verificar en Gmail web)
- [ ] El botón "Enviar" muestra confirmación antes de enviar

### 🛑 Para aquí

Commit: `feat: CalendarTool + UI de Email funcional`. La Sesión 3 añade disponibilidad y Settings de Google.

---

## SESIÓN 3: Disponibilidad + Settings Google

**Tiempo estimado**: 1-2 horas
**Empieza con**: Email y Calendar funcionando

### Paso 1 — Sistema de disponibilidad

Nuevo endpoint `POST /api/calendar/availability/config`:

```json
{
  "meeting": {
    "days": ["monday", "tuesday", "wednesday", "thursday"],
    "hours": [10, 11, 15, 16, 17],
    "max_per_day": 3
  },
  "deep_work": {
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "hours": [9, 10, 11],
    "min_duration_minutes": 90
  }
}
```

Se guarda en la tabla `config` con key `calendar_availability`. El endpoint `find_free_slots` consulta esta config para filtrar los slots disponibles según el tipo de actividad.

### Paso 2 — Sección Google en Settings

Actualizar `frontend/src/pages/Settings.tsx`:

Añadir sección "Google":
- Estado: "✓ Conectado como user@gmail.com" o "Sin conectar"
- Campos: `client_id` y `client_secret` (se guardan en tabla `config`)
- Botón "Conectar Google" → llama al flujo OAuth
- Botón "Desconectar" → borra `google_token.json`
- Link a `GUIA-OAUTH-GOOGLE.md` para instrucciones de configuración

### Paso 3 — Registrar herramientas en ToolManager

En `backend/app/execution/__init__.py`, registrar EmailTool y CalendarTool:

```python
from app.tools.email_tool import EmailTool
from app.tools.calendar_tool import CalendarTool

register_tool(EmailTool())
register_tool(CalendarTool())
```

Ahora los agentes pueden usar `email` y `calendar` en su `allowed_tools`.

### Bump de versión

- `backend/app/main.py`: `version="0.7.0"`
- `backend/app/core/config.py`: `VERSION = "0.7.0"`
- `frontend/package.json`: `"version": "0.7.0"`

### ✅ Checkpoint Sesión 3 — verificar antes de parar

- [ ] `GET /api/calendar/availability?date=...&duration=60&type=meeting` respeta la config de disponibilidad
- [ ] Settings muestra el estado de conexión de Google
- [ ] El botón "Desconectar" borra el token y la UI vuelve al estado "Sin conectar"
- [ ] `GET /api/tools/` devuelve 6 herramientas (las 4 originales + EmailTool + CalendarTool)
- [ ] Un agente con `allowed_tools: ["email"]` puede listar emails desde la UI de Agentes
- [ ] El token OAuth se refresca automáticamente (verificar arrancando el backend después de que expire)
- [ ] `GET /` devuelve `"version": "0.7.0"`

### 🛑 Para aquí

Aithera V0.7.0 completada. Commit: `feat: V0.7.0 — Email Assistant + Calendar inteligente con Google OAuth`.

**Siguiente fase**: `Fase_5_Clients_Telegram_Web_V08.md`

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Sesión 1**: `backend/app/integrations/__init__.py`, `backend/app/integrations/google_auth.py`, `backend/app/tools/email_tool.py`, `backend/app/api/endpoints/email_assistant.py` (implementación real), `backend/requirements.txt`

**Sesión 2**: `backend/app/tools/calendar_tool.py`, `backend/app/api/endpoints/calendar.py` (nuevos endpoints), `frontend/src/pages/Email.tsx` (implementación real)

**Sesión 3**: `backend/app/execution/__init__.py` (registrar EmailTool y CalendarTool), `frontend/src/pages/Settings.tsx` (sección Google), versiones en main.py, config.py, package.json
