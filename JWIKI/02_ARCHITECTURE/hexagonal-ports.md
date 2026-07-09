# Hexagonal Architecture — Ports & Adapters

## Resumen

**Hexagonal Architecture** (Ports & Adapters) de Alistair Cockburn es un patrón que aísla la lógica de negocio (core) de las dependencias externas (DB, UI, API). Aithera V0.7.3 sigue parcialmente este patrón.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Conceptos

- **Core / Domain**: lógica de negocio pura.
- **Ports**: interfaces que el core expone (e.g., `IMemoryStore`).
- **Adapters**: implementaciones de ports (e.g., `ChromaDBMemoryStore`).

```
┌─────────────────────────────────────────┐
│  UI (Electron / Telegram / Web)          │ ← Adapter
├─────────────────────────────────────────┤
│  API (FastAPI)                           │ ← Adapter
├─────────────────────────────────────────┤
│  Core (Agents / Memory / Tools / Email)  │
│  ↕ Ports (interfaces)                    │
│  ChromaDB, PostgreSQL, Gmail, Calendar  │ ← Adapters
└─────────────────────────────────────────┘
```

## Ventajas

- ✅ **Testeable**: mock adapters fácilmente.
- ✅ **Cambiar DB o AI provider**: solo cambias adapter.
- ✅ **Core reutilizable**: en otro cliente (CLI, mobile).
- ✅ **Aislamiento**: cambios externos no rompen core.

## Desventajas

- ❌ **Más capas**: boilerplate extra.
- ❌ **Overkill para proyectos pequeños**.
- ❌ **Curva aprendizaje**.

## Aithera V0.7.3 — hexagonal parcial

Aithera tiene hexagonal en algunos lugares:
- **`ToolManager`**: tools son adapters detrás de una interfaz común.
- **`AIManager`**: providers son adapters detrás de `BaseProvider`.
- **`MemoryManager`**: ChromaDB es adapter detrás de `IMemoryStore` (parcial).

Pero NO es hexagonal puro:
- FastAPI importa directamente de SQLAlchemy (no hay port explícito).
- Frontend llama directamente a endpoints.

## Para V1.0+ Orchestrator

V1.0 Orchestrator debería ser hexagonal puro:
- Core: lógica de orquestación.
- Ports: `ITaskExecutor`, `IMemoryAccess`, `IToolInvocation`.
- Adapters: implementaciones específicas.

## Ejemplo de port (Python)

```python
# port.py
from abc import ABC, abstractmethod

class IMemoryStore(ABC):
    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        ...
    
    @abstractmethod
    async def add(self, item: MemoryItem) -> None:
        ...

# adapter_chromadb.py
class ChromaDBMemoryStore(IMemoryStore):
    def __init__(self, collection):
        self.collection = collection
    
    async def search(self, query, top_k=5):
        results = self.collection.query(query_texts=[query], n_results=top_k)
        return [MemoryItem.from_chroma(r) for r in results["documents"][0]]
    
    async def add(self, item):
        self.collection.add(documents=[item.content], ids=[item.id])

# adapter_inmemory.py (test)
class InMemoryStore(IMemoryStore):
    def __init__(self):
        self.items = []
    
    async def search(self, query, top_k=5):
        return [i for i in self.items if query.lower() in i.content.lower()][:top_k]
    
    async def add(self, item):
        self.items.append(item)
```

## Trade-off hexagonal vs simple

Para Aithera V0.7.3 (personal project), hexagonal puro sería overkill. **Hexagonal parcial** (como tiene) es el sweet spot:
- Core interfaces para lo crítico (Tools, AI providers, Memory).
- Direct integration para lo no-crítico (DB session, HTTP handlers).

## Para V1.0 Orchestrator

V1.0 introduce el Orchestrator. Aquí sí vale la pena hexagonal puro porque:
- Multi-provider AI (cambiar de OpenAI a Anthropic sin tocar core).
- Multi-Memory store (ChromaDB → Pinecone).
- Multi-Tool executor (in-process vs Docker sandbox).

## Referencias cruzadas

- [JWIKI-052 plugin-architecture.md](./plugin-architecture.md)
- [JWIKI-054 clean-architecture.md](./clean-architecture.md)
- [JWIKI-055 orchestrator-pattern.md](./orchestrator-pattern.md)

## Fuentes

1. https://alistair.cockburn.us/hexagonal-architecture/ — Alistair Cockburn
2. https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html — Uncle Bob

## Nivel de confianza

**85%** — Pattern bien establecido.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified