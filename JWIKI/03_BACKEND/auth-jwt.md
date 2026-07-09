# JWT vs Session — Auth en Aithera

## Resumen

**JWT** (JSON Web Tokens) vs **Session cookies** para auth. Aithera V0.7.3 usa API keys (Bearer tokens), NO JWT. Para V0.85+ podría considerar JWT para multi-device.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Comparativa

| Aspecto | JWT | Session |
|---|---|---|
| Storage | Client (localStorage / cookie) | Server (DB / memory) |
| Stateless | ✅ | ❌ |
| Revocable | ❌ (until exp) | ✅ inmediato |
| Cross-domain | ✅ | ⚠️ CORS |
| Mobile-friendly | ✅ | ⚠️ |
| Performance | ✅ (no DB lookup) | ❌ (DB lookup) |

## Aithera V0.7.3 — API key Bearer

Aithera usa API keys en `Authorization: Bearer <key>`:

```python
# backend/app/api/deps.py
async def verify_api_key(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401)
    api_key = authorization[7:]
    if api_key != settings.AITHERA_API_KEY:
        raise HTTPException(403)
    return api_key
```

## Cuando usar JWT

- ✅ Multi-device sync.
- ✅ Microservicios stateless.
- ✅ Mobile clients.
- ✅ Third-party API access.

## Cuando usar Session

- ✅ Web apps traditional.
- ✅ Revocación inmediata importante.
- ✅ Single-server (no scale out).

## Para Aithera

Aithera es **single-user, single-device**:
- API key es suficiente.
- No necesita JWT.

V0.85+ (multi-device, V1.0+) podría considerar JWT.

## JWT estructura

```
header.payload.signature
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature
```

Header: algoritmo (`{"alg": "HS256"}`).
Payload: claims (`{"sub": "user_id", "exp": 1234567890}`).
Signature: HMAC del header + payload.

## Para Aithera V1.0+

```python
# jose library
from jose import jwt

def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
```

## Pitfalls

- ❌ **JWT en localStorage** vulnerable a XSS.
- ❌ **JWT sin expiración** = comprometido para siempre.
- ❌ **JWT con info sensible** en payload (es legible, solo base64).
- ❌ **Secret hardcodeado**.

## Referencias cruzadas

- [JWIKI-070 auth-oauth2.md](./auth-oauth2.md)
- [JWIKI-247 rotate-api-keys.md](../16_SOPS/rotate-api-keys.md)

## Fuentes

1. https://jwt.io/
2. https://datatracker.ietf.org/doc/html/rfc7519

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified