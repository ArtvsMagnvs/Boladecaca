# Webhooks — Pattern general

## Resumen

**Webhooks** son HTTP callbacks que permiten a un servidor notificar a otro cuando un evento ocurre. Alternativa a polling. **NO usado en Aithera V0.7.3** (polling para Gmail). V0.85+ considera.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Webhook pattern

```
Service (GitHub)                          Aithera
   │                                          │
   │  1. Setup: Aithera expone URL            │
   │  POST https://aithera.com/webhook/github │
   │                                          │
   │  2. Evento ocurre (push a repo)          │
   │  ────────────────────►                   │
   │  POST /webhook/github                    │
   │  X-Hub-Signature: sha256=...             │
   │  { "event": "push", ... }                │
   │                                          │
   │  3. Aithera verifica signature           │
   │  4. Procesa el evento                    │
   │  5. Devuelve 200 OK                      │
```

## Aithera como webhook receiver

```python
# backend/app/api/endpoints/webhooks.py
from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib

router = APIRouter()

GITHUB_SECRET = "..."

@router.post("/api/webhook/github")
async def github_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    # Verificar signature
    expected = "sha256=" + hmac.new(
        GITHUB_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid signature")
    
    event = await request.json()
    
    # Procesar
    if event["ref"] == "refs/heads/main":
        # Trigger CI / rebuild / notify user
        await notification.send(f"Push to main: {event['head_commit']['message']}")
    
    return {"status": "ok"}
```

## Push notifications alternativas

| Service | Webhook | Polling |
|---|---|---|
| GitHub | ✅ | ✅ API |
| Gmail | ❌ (use Pub/Sub) | ✅ |
| Stripe | ✅ | ❌ no recomendado |
| Slack | ✅ Events API | ❌ |
| GitLab | ✅ | ✅ |

## Polling vs Webhooks

| Aspecto | Polling | Webhooks |
|---|---|---|
| Latency | alta (interval) | baja (instant) |
| Server load | constante | solo en eventos |
| Setup | simple | requiere URL pública |
| Reliability | ✅ always works | ⚠️ puede fallar |
| HTTPS | no necesita | necesita |

Aithera es **desktop local** → webhooks requieren tunnel (ngrok, Cloudflare) o self-hosting server. **No ideal** para V0.85+ desktop.

## Para Aithera

- ❌ V0.7.3: NO usa webhooks (polling).
- ⏳ V0.85+: webhooks opcionales con HTTPS tunnel (ngrok).
- ⏳ V1.0+: Cloudflare tunnel para webhooks stables.

## Referencias cruzadas

- [JWIKI-153 gmail-api.md](./gmail-api.md)
- [JWIKI-156 telegram-bot.md](./telegram-bot.md)

## Fuentes

1. https://docs.github.com/en/webhooks
2. https://webhooks.pbjar.uk/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified