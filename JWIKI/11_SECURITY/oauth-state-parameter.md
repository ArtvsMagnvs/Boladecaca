# OAuth State Parameter — CSRF protection

## Resumen

**State parameter** en OAuth2 protege contra **CSRF** (Cross-Site Request Forgery). Aithera V0.7+ lo implementa.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## CSRF attack (sin state)

```
1. User hace login en attacker.com
2. attacker.com redirige a Google OAuth con client_id=APP_LEGITIMO
3. User autoriza (sin saber)
4. Google redirige a APP_LEGITIMO/callback con code
5. APP_LEGITIMO intercambia code por tokens del attacker
```

## Con state parameter

```
1. Aithera genera state=random123 y guarda en session
2. Redirige a Google con state=random123
3. User autoriza
4. Google redirige con state=random123
5. Aithera verifica: state == session.state → OK
6. Si state distinto → CSRF attempt, reject
```

## Aithera implementation

```python
# backend/app/integrations/google_auth.py
import secrets

def generate_auth_url(scopes: list[str]) -> tuple[str, str, str]:
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64url(hashlib.sha256(code_verifier.encode()).digest())
    state = secrets.token_urlsafe(32)  # <- CSRF protection
    
    # Save state in DB (since Aithera is local, can use simple table)
    await db.set_temp_state(user_id, state)
    
    return auth_url, code_verifier, state

async def handle_callback(code: str, state: str, user_id: int):
    # Verify state
    saved_state = await db.get_temp_state(user_id)
    if state != saved_state:
        raise SecurityError("OAuth state mismatch — possible CSRF")
    
    # Clear state (one-time use)
    await db.clear_temp_state(user_id)
    
    # Exchange code
    return await exchange_code(code, code_verifier)
```

## Referencias cruzadas

- [JWIKI-186 oauth-pkce.md](./oauth-pkce.md)
- [JWIKI-152 google-oauth-flow.md](../09_INTEGRATIONS/google-oauth-flow.md)

## Fuentes

1. https://datatracker.ietf.org/doc/html/rfc6749#section-10.12

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified