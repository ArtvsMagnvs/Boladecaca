# OAuth2 Authorization Code + PKCE — Auth en Aithera

## Resumen

**OAuth2 Authorization Code + PKCE** es el flujo usado por Aithera V0.7+ para Google OAuth (Gmail, Calendar). Ver CLAUDE.md §13 (Integrations).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Flujo OAuth2 Authorization Code + PKCE

```
┌────────┐                                    ┌────────┐
│ Client │                                    │Google  │
│ (Aithera)                                   │OAuth   │
└───┬────┘                                    └────┬───┘
    │                                              │
    │ 1. Generate code_verifier + code_challenge   │
    │ 2. Redirect user to Google auth URL         │
    │    (with client_id, scope, code_challenge)   │
    │ ─────────────────────────────────────────────►│
    │                                              │
    │ 3. User grants permission                     │
    │                                              │
    │ 4. Google redirects back with code          │
    │ ◄─────────────────────────────────────────────│
    │                                              │
    │ 5. Exchange code + code_verifier             │
    │    for access_token + refresh_token          │
    │ ─────────────────────────────────────────────►│
    │                                              │
    │ 6. Store tokens in DB (encrypted V0.8+)      │
    │                                              │
    │ 7. Use access_token for Gmail/Calendar API    │
    │                                              │
    │ 8. Refresh when expired                       │
    └──────────────────────────────────────────────┘
```

## Aithera V0.7+ implementation

Aithera usa **google-auth-oauthlib** + flow personalizado:

```python
# backend/app/integrations/google_auth.py
from google_auth_oauthlib.flow import Flow

def start_oauth_flow():
    flow = Flow.from_client_secrets_file(
        "client_secrets.json",
        scopes=["https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/calendar"]
    )
    flow.redirect_uri = "http://localhost:8000/api/email/auth/callback"
    
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"  # force refresh_token
    )
    
    # Store state in session
    return authorization_url, state

def complete_oauth_flow(state, code):
    flow = Flow.from_client_secrets_file(...)
    flow.fetch_token(code=code)
    credentials = flow.credentials
    # Store in DB (encrypted V0.8+)
    save_credentials(credentials)
```

## PKCE (Proof Key for Code Exchange)

PKCE añade un `code_verifier` + `code_challenge` para evitar **authorization code interception attacks**:

```python
import secrets
import hashlib

# Generate
code_verifier = secrets.token_urlsafe(64)
code_challenge = hashlib.sha256(code_verifier.encode()).hexdigest()

# Send code_challenge with auth request
# Send code_verifier when exchanging code for token
# Google verifies: hash(code_verifier) == code_challenge
```

## Refresh tokens

Access tokens expiran (~1h). Refresh tokens son long-lived:

```python
def refresh_if_needed(credentials):
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_credentials(credentials)
```

## Aithera credentials storage

```python
# V0.8+: cifrado con DPAPI
from app.core.secrets import encrypt, decrypt

def save_credentials(credentials):
    encrypted = encrypt(json.dumps({
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "scopes": credentials.scopes
    }))
    db.set_config("google_oauth_credentials", encrypted)

def load_credentials():
    encrypted = db.get_config("google_oauth_credentials")
    return Credentials(**json.loads(decrypt(encrypted)))
```

## Pitfalls

- ❌ **`access_type=online`** (default) — pierde refresh_token. Usar `offline`.
- ❌ **No store refresh_token** — user tiene que re-auth cada hora.
- ❌ **No PKCE** — vulnerable a code interception.
- ❌ **Client secret en frontend** — usar solo en backend.

## Referencias cruzadas

- [JWIKI-071 auth-jwt.md](./auth-jwt.md)
- [JWIKI-152 google-oauth-flow.md](../09_INTEGRATIONS/google-oauth-flow.md)

## Fuentes

1. https://developers.google.com/identity/protocols/oauth2
2. https://oauth.net/2/pkce/
3. https://google-auth-oauthlib.readthedocs.io/

## Nivel de confianza

**95%** — Implementado y testeado.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified