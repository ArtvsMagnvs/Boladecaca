# Clean Architecture — Versión de Uncle Bob

## Resumen

**Clean Architecture** (Uncle Bob, 2012) es la versión "mainstream" de Hexagonal. Mismo concepto, capas más explícitas. Aithera V0.7.3 sigue parcialmente.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Las 4 capas

```
┌─────────────────────────────────┐
│  Frameworks & Drivers (DB, UI)  │ ← Outer
├─────────────────────────────────┤
│  Interface Adapters (Gateways)  │
├─────────────────────────────────┤
│  Application Business Rules    │
├─────────────────────────────────┤
│  Enterprise Business Rules     │ ← Inner (Core)
└─────────────────────────────────┘
```

**Dependency rule**: dependencias apuntan hacia adentro (outer → inner). Core no conoce outer.

## Aithera V0.7.3 — clean architecture parcial

| Capa | Aithera V0.7.3 |
|---|---|
| Frameworks | FastAPI, Electron, React |
| Interface Adapters | `ai/providers/`, `tools/`, `gateway/adapters/` |
| Application | `api/endpoints/` (routers), `services/email_service.py` |
| Enterprise | `agents/agent_manager.py`, `memory/memory_manager.py` |

**Bueno**: routers son interface adapters claros, services/ es application layer.

**Malo**: routes importan directamente SQLAlchemy models (mezcla application con frameworks).

## Hexagonal vs Clean Architecture

| Aspecto | Hexagonal | Clean |
|---|---|---|
| **Autor** | Cockburn (2005) | Uncle Bob (2012) |
| **Capas** | 2 (core + adapters) | 4 (frameworks, adapters, app, core) |
| **Concepto** | Ports & Adapters | Dependency rule + boundaries |
| **Práctica** | Mismo en esencia | Más explícito en capas |

## Para Aithera V1.0

V1.0 Orchestrator debería respetar Clean Architecture estricta:
- **Core (Enterprise)**: lógica de orquestación pura.
- **Application**: use cases (HandleRequest, RunTask).
- **Interface Adapters**: gateways a AI providers, tools, memory.
- **Frameworks**: FastAPI, asyncio.

## Ejemplo de capas

```python
# core/use_cases/handle_request.py
class HandleRequest:
    def __init__(self, memory: MemoryPort, tools: ToolPort, ai: AIPort):
        self.memory = memory
        self.tools = tools
        self.ai = ai
    
    async def execute(self, request: Request) -> Response:
        # Pure business logic
        context = await self.memory.search(request.query)
        plan = await self.ai.plan(request.query, context)
        result = await self.tools.execute(plan)
        return Response.from_result(result)

# interface_adapters/ai/openai_provider.py
class OpenAIProvider(AIPort):
    async def plan(self, query, context):
        return await self.openai_client.chat([...])
```

## Trade-offs

- ✅ **Independiente de frameworks**.
- ✅ **Testeable puro**.
- ❌ **Más boilerplate**.
- ❌ **Overkill para V0.7.3 personal**.

## Referencias cruzadas

- [JWIKI-053 hexagonal-ports.md](./hexagonal-ports.md)
- [JWIKI-055 orchestrator-pattern.md](./orchestrator-pattern.md)

## Fuentes

1. https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
2. https://alistair.cockburn.us/hexagonal-architecture/

## Nivel de confianza

**90%** — Pattern bien establecido.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified