# Performance — Caching

## Resumen

**Caching** reduce latencia + load en DBs/APIs. Aithera V0.85+ debería añadir caching.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Caching layers

| Layer | Tool | Use |
|---|---|---|
| Browser | HTTP cache, localStorage | static assets |
| CDN | Cloudflare | static + media |
| API | Redis, in-memory | responses |
| DB | PostgreSQL cache, materialized views | queries |
| LLM | Anthropic prompt cache, OpenAI cache | system prompts |

## Redis cache (V0.85+)

```python
import redis

cache = redis.Redis(host="localhost", port=6379)

async def get_cached_ai_response(prompt: str) -> str | None:
    key = f"ai:{hash(prompt)}"
    return cache.get(key)

async def set_cached_ai_response(prompt: str, response: str, ttl: int = 3600):
    key = f"ai:{hash(prompt)}"
    cache.setex(key, ttl, response)
```

## HTTP cache headers

```python
from fastapi import Response

@app.get("/api/agents/{id}")
async def get_agent(id: int, response: Response):
    response.headers["Cache-Control"] = "max-age=60, must-revalidate"
    return await db.get_agent(id)
```

## LLM prompt caching (Anthropic)

```python
response = anthropic.messages.create(
    model="claude-opus-4-8",
    system=[
        {"type": "text", "text": "You are Aithera.", "cache_control": {"type": "ephemeral"}}
    ],
    messages=[{"role": "user", "content": user_input}]
)
# System prompt cached, 90% discount.
```

## Para Aithera

- ❌ V0.7.3: NO caching explícito.
- ⏳ V0.85+: Redis + HTTP cache + LLM prompt cache.

## Fuentes

1. https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified