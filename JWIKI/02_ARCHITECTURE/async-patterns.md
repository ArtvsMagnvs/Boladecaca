# Async Patterns — asyncio, queues, tasks

## Resumen

Aithera V0.7.3 usa **asyncio** extensivamente en FastAPI. Patrones async clave: tasks, queues, locks, semaphores, gather. Crítico para SSE streaming, agent execution, y event-driven V0.9+.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Patrones async clave

### 1. Async function + await

```python
async def chat(messages: list[dict]) -> str:
    response = await openai_client.chat(messages)
    return response.content
```

### 2. asyncio.gather (paralelo)

```python
async def get_multi_context():
    # Ejecuta en paralelo
    memory, calendar, email = await asyncio.gather(
        memory_manager.search("Aithera"),
        calendar.list_upcoming(),
        email.list_recent()
    )
    return {"memory": memory, "calendar": calendar, "email": email}
```

### 3. asyncio.Queue (producer-consumer)

```python
queue = asyncio.Queue()

async def producer():
    for i in range(10):
        await queue.put(f"item-{i}")

async def consumer():
    while True:
        item = await queue.get()
        await process(item)
        queue.task_done()
```

### 4. asyncio.Task (background)

```python
async def main():
    # Lanzar background task
    task = asyncio.create_task(background_worker())
    # Hacer otra cosa
    await asyncio.sleep(1)
    # Cancelar al final
    task.cancel()
```

### 5. asyncio.Lock (mutual exclusion)

```python
db_lock = asyncio.Lock()

async def safe_db_write(data):
    async with db_lock:
        await db.write(data)
```

### 6. asyncio.Semaphore (rate limit)

```python
api_sem = asyncio.Semaphore(5)  # max 5 concurrent

async def call_api(req):
    async with api_sem:
        return await openai.chat(req)
```

### 7. asyncio.wait_for (timeout)

```python
try:
    result = await asyncio.wait_for(slow_call(), timeout=30.0)
except asyncio.TimeoutError:
    result = fallback_value
```

## Aithera V0.7.3 — uso de async

- **FastAPI**: todos los handlers son `async def`.
- **httpx**: async HTTP client (reemplaza `requests`).
- **openai-async**: SDK async para OpenAI.
- **anthropic-async**: SDK async para Anthropic.
- **email_tool**: Gmail API calls via httpx async.
- **streaming**: SSE via `StreamingResponse` (async generator).

## SSE streaming async

```python
from fastapi.responses import StreamingResponse

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in ai_provider.stream_chat(request.messages):
            yield f"data: {chunk.json()}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## Aithera V1.0 — Orchestrator async

```python
async def orchestrator_handle(envelope: MessageEnvelope):
    # Parse intent (LLM call)
    intent = await orchestrator.classify_intent(envelope.text)
    
    # Plan tasks (async fan-out)
    tasks = await orchestrator.plan(intent)
    
    # Execute tasks in parallel where possible
    if tasks.parallelizable:
        results = await asyncio.gather(*[t.execute() for t in tasks])
    else:
        results = []
        for t in tasks:
            r = await t.execute()
            results.append(r)
    
    # Build response
    return await orchestrator.build_response(results, envelope)
```

## Anti-patterns

- ❌ **Blocking I/O en async function**: usar `httpx.AsyncClient` no `requests`.
- ❌ **`time.sleep` en async**: usar `await asyncio.sleep`.
- ❌ **No usar gather**: tareas paralelas secuenciales = lentas.
- ❌ **Crear task sin guardar referencia**: el task puede ser garbage-collected.
- ❌ **Lock global**: mata el paralelismo.

## Testing async

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == "expected"
```

Aithera V0.8+ usa `pytest-asyncio` para tests.

## Referencias cruzadas

- [JWIKI-048 event-driven.md](./event-driven.md)
- [JWIKI-050 sse-streaming.md](./sse-streaming.md)
- [JWIKI-055 orchestrator-pattern.md](./orchestrator-pattern.md)
- [JWIKI-058 fastapi.md](../03_BACKEND/fastapi.md)

## Fuentes

1. https://docs.python.org/3/library/asyncio.html — Python asyncio
2. https://fastapi.tiangolo.com/async/ — FastAPI async
3. https://anyio.readthedocs.io/ — anyio (FastAPI usa)

## Nivel de confianza

**95%** — Patrones bien establecidos.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified