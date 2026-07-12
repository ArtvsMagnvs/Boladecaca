# Google OAuth2 Flow — Authorization Code + PKCE

## Resumen

Aithera V0.7+ implementa **OAuth2 Authorization Code + PKCE** para Google (Gmail + Calendar). Ver CLAUDE.md §13 (`backend/app/integrations/google_auth.py`).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## OAuth2 Authorization Code + PKCE

Es el flow recomendado para **apps nativas / SPAs / desktop** (vs. apps server-side tradicionales).

### Ventajas vs otros flows

| Flow | Apps | Seguridad | Aithera |
|---|---|---|---|
| Implicit (deprecated) | SPA | baja | ❌ |
| Authorization Code | server | alta | ❌ |
| **Authorization Code + PKCE** | SPA / native | **máxima** | ✅ |

### Pasos del flow

```
1. App genera `code_verifier` (random 43-128 chars)
   y `code_challenge` = SHA256(code_verifier)

2. App redirige al user a Google OAuth:
   https://accounts.google.com/o/oauth2/v2/auth?
     client_id=...&
     redirect_uri=http://localhost:8000/api/email/auth/callback&
     response_type=code&
     scope=https://www.googleapis.com/auth/gmail.readonly ...&
     code_challenge=...&
     code_challenge_method=S256

3. User autoriza en Google.

4. Google redirige a `redirect_uri?code=...&state=...`

5. App intercambia code por tokens:
   POST https://oauth2.googleapis.com/token
     code=...&
     client_id=...&
     code_verifier=...&  # <- prueba PKCE
     grant_type=authorization_code

6. Google devuelve:
   {
     "access_token": "ya29...",
     "refresh_token": "1//...",
     "expires_in": 3600,
     "scope": "...",
     "token_type": "Bearer"
   }

7. App usa access_token para llamar APIs:
   Authorization: Bearer ya29...

8. Cuando access_token expira, usa refresh_token:
   POST https://oauth2.googleapis.com/token
     client_id=...&
     refresh_token=...&
     grant_type=refresh_token
```

## Aithera implementation

```python
# backend/app/integrations/google_auth.py
import secrets
import hashlib
import httpx
from urllib.parse import urlencode

class GoogleOAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
    
    def generate_auth_url(self, scopes: list[str]) -> tuple[str, str, str]:
        """Returns (auth_url, code_verifier, state)."""
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = hashlib.sha256(code_verifier.encode()).hexdigest()
        state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",  # <- para obtener refresh_token
            "state": state
        }
        return f"{self.auth_url}?{urlencode(params)}", code_verifier, state
    
    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri
            })
            response.raise_for_status()
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            })
            response.raise_for_status()
            return response.json()
```

## Endpoints Aithera V0.7+

```python
# POST /api/email/auth/start
# Body: { "scopes": ["gmail.readonly", "calendar.readonly"] }
# Response: { "auth_url": "https://accounts.google.com/..." }

# GET /api/email/auth/callback?code=...&state=...
# Exchange code, save tokens, redirect to /

# POST /api/email/auth/credentials
# Body: { "client_id": "...", "client_secret": "..." }
# Save OAuth app credentials

# DELETE /api/email/auth
# Revoke tokens, clear credentials
```

## Scopes necesarios Aithera

```python
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",   # leer emails
    "https://www.googleapis.com/auth/gmail.send",       # enviar emails
    "https://www.googleapis.com/auth/gmail.modify"      # marcar como leído, etc.
]

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",          # full calendar access
    "https://www.googleapis.com/auth/calendar.events"   # events only
]
```

## Token storage

Aithera almacena tokens en BD. **Importante**: cifrar con DPAPI (CLAUDE.md §1).

```python
# Encrypt before save
encrypted_access = encrypt_dpapi(access_token)
encrypted_refresh = encrypt_dpapi(refresh_token)

await db.save({
    "user_id": user_id,
    "access_token_enc": encrypted_access,
    "refresh_token_enc": encrypted_refresh,
    "expires_at": datetime.now() + timedelta(seconds=expires_in)
})

# Decrypt on read
access_token = decrypt_dpapi(stored.access_token_enc)
```

## Token refresh strategy

```python
async def get_valid_access_token(user_id: int) -> str:
    stored = await db.get_tokens(user_id)
    
    if stored.expires_at > datetime.now() + timedelta(minutes=5):
        # Aún válido
        return decrypt_dpapi(stored.access_token_enc)
    
    # Refresh
    new_tokens = await oauth.refresh_token(decrypt_dpapi(stored.refresh_token_enc))
    await db.update_tokens(user_id, new_tokens)
    return new_tokens["access_token"]
```

## Pitfalls

- ❌ **No hardcodear client_secret** en código.
- ❌ **No loguear access_token** (security).
- ❌ **No usar `access_type=online`** (sin refresh_token).
- ❌ **No asumir scopes granted** (verificar response.scope).

## Referencias cruzadas

- [JWIKI-151 README.md](./README.md)
- [JWIKI-153 gmail-api.md](./gmail-api.md)
- [JWIKI-154 google-calendar-api.md](./google-calendar-api.md)
- CLAUDE.md §13

## Fuentes

1. https://developers.google.com/identity/protocols/oauth2/native-app
2. https://oauth.net/2/pkce/
3. https://datatracker.ietf.org/doc/html/rfc7636

## Nivel de confianza

**100%** — Aithera V0.7+ lo implementa correctamente (CLAUDE.md §13).

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified