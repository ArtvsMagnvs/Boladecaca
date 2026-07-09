# Async Lifespan — FastAPI startup/shutdown

## Resumen

**Lifespan** en FastAPI es el patrón async para startup/shutdown de la app. Aithera V0.7.3 lo usa extensivamente. Ver [JWIKI-058 fastapi.md](./fastapi.md).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Lifespan pattern

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP ===
    print("Starting Aithera...")
    await init_database()
    await init_ai_providers()
    await init_memory_manager()
    await init_gateway()  # V0.8+
    await init_telegram_adapter()  # V0.8+
    print("Aithera started")
    
    yield  # <- app runs here
    
    # === SHUTDOWN ===
    print("Stopping Aithera...")
    await cleanup_ai_providers()
    await cleanup_gateway()
    print("Aithera stopped")

app = FastAPI(lifespan=lifespan, title="Aithera", version="0.7.3")
```

## Aithera V0.7.3 lifespan

```python
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    
    # 1. Database
    await init_db()
    
    # 2. AI Manager (8 providers)
    ai_manager = get_ai_manager()
    await ai_manager.load_providers()
    
    # 3. Memory (ChromaDB)
    memory_manager = get_memory_manager()
    await memory_manager.initialize()
    
    # 4. Tools registry
    tool_manager = get_tool_manager()
    await tool_manager.load_tools()
    
    # 5. Agents
    agent_manager = get_agent_manager()
    await agent_manager.load_agents()
    
    # 6. Gateway (V0.8+)
    if settings.GATEWAY_ENABLED:
        await gateway.start()
    
    yield
    
    # Shutdown
    if settings.GATEWAY_ENABLED:
        await gateway.stop()
    await ai_manager.cleanup()
```

## Old vs new pattern

**Old** (deprecated en FastAPI 0.93+):
```python
@app.on_event("startup")
async def startup():
    ...

@app.on_event("shutdown")
async def shutdown():
    ...
```

**New** (lifespan):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown
```

## Best practices

- ✅ **Ordenar dependencies**: DB → AI → Memory → Tools → Agents → Gateway.
- ✅ **Cleanup en orden inverso**: Gateway → Agents → Tools → Memory → AI → DB.
- ✅ **Manejar excepciones en startup**: si falla, app no arranca.
- ✅ **Idempotente**: re-llamar startup no debe fallar.
- ❌ **Bloquear startup con tareas largas** (usar background tasks).

## Aithera V0.85+ additions

V0.85 podría añadir al lifespan:
- `await skill_manager.load_skills()` (drop-in de `aithera-skills/`).
- `await automation_engine.start()` (V0.9).
- `await orchestrator.initialize()` (V1.0).

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-076 exception-handling.md](./exception-handling.md)

## Fuentes

1. https://fastapi.tiangolo.com/advanced/events/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified