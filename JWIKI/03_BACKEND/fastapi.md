# FastAPI — Framework backend de Aithera

## Resumen

**FastAPI** es el framework backend de Aithera V0.7.3. Modern Python, async nativo, OpenAPI auto-generado. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones

| Componente | Versión | Notas |
|---|---|---|
| FastAPI | ≥0.100 (recomendado latest) | |
| Pydantic | v2 | **from_attributes=True** |
| Uvicorn | latest | ASGI server |
| SQLAlchemy | 2.0 | ORM async |
| Alembic | 1.13 | Migrations |
| python-dotenv | latest | .env loading |
| httpx | latest | async HTTP client |

## Stack Aithera V0.7.3

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await init_ai_providers()
    await init_memory()
    await init_gateway()
    yield
    # Shutdown
    await cleanup()

app = FastAPI(lifespan=lifespan, title="Aithera", version="0.7.3")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(email_auth.router, prefix="/api/email/auth")
# ... 18 routers más
```

## Async nativo

Todos los handlers son `async def`:

```python
@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    response = await ai_manager.chat(request.messages)
    return ChatResponse(content=response.content)
```

## SSE streaming

```python
from fastapi.responses import StreamingResponse

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in ai_manager.stream_chat(request.messages):
            yield f"data: {chunk.json()}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## Pydantic v2 schemas

```python
from pydantic import BaseModel, ConfigDict

class ChatRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # SQLAlchemy compat
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int = 2048

class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
```

## Exception handler global

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled error in {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)}
    )
```

## Lifespan events

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup async
    await ai_manager.initialize()  # carga 8 providers
    await memory_manager.initialize()  # ChromaDB
    await gateway.initialize()  # V0.8+
    yield
    # Shutdown async
    await ai_manager.cleanup()
    await gateway.cleanup()
```

## Para Aithera

V0.7.3 usa FastAPI extensivamente. CLAUDE.md §2 confirma:
- FastAPI con `lifespan` (startup/shutdown async).
- 20 routers en `backend/app/api/endpoints/`.
- OpenAPI auto-generated en `/docs`.

## Pitfalls

- ❌ **No usar `orm_mode` (Pydantic v1)** — usar `from_attributes=True` (v2).
- ❌ **Blocking I/O en async handlers** — usar `httpx.AsyncClient` no `requests`.
- ❌ **No usar `lifespan` para setup bloqueante** — wrap en `asyncio.to_thread()` si necesario.

## Referencias cruzadas

- [JWIKI-057 README.md](./README.md) — comparativa frameworks
- [JWIKI-061 flask-vs-fastapi.md](./flask-vs-fastapi.md)
- [JWIKI-075 async-lifespan.md](./async-lifespan.md)
- [JWIKI-077 pydantic-v2.md](./pydantic-v2.md)

## Fuentes

1. https://fastapi.tiangolo.com/
2. CLAUDE.md §2 (Aithera V0.7.3 backend stack)
3. https://docs.pydantic.dev/latest/

## Nivel de confianza

**95%** — Stack bien documentado en CLAUDE.md.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified