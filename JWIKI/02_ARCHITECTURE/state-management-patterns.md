# State Management — Cross-client

## Resumen

**State management** es cómo mantener estado coherente entre Electron (frontend), FastAPI (backend), y canales externos (Telegram). Aithera V0.7.3 usa Zustand + DB persistida. Para V1.0+, podría usar state machines.

## Resumen por componente

| Capa | State management | Storage |
|---|---|---|
| Frontend (Electron) | Zustand 4 | Memoria + localStorage |
| Backend (FastAPI) | SQLAlchemy session + state objects | PostgreSQL/SQLite |
| Memory (ChromaDB) | Embeddings | ChromaDB vector store |
| Multi-client (V0.8+) | Gateway + MessageEnvelope | DB |

## Frontend — Zustand

```typescript
import { create } from "zustand";

interface AppState {
    chatMessages: ChatMessage[];
    setChatMessages: (msgs: ChatMessage[]) => void;
    aiStatus: AIStatus | null;
    setAiStatus: (status: AIStatus) => void;
}

export const useAppStore = create<AppState>((set) => ({
    chatMessages: [],
    setChatMessages: (chatMessages) => set({ chatMessages }),
    aiStatus: null,
    setAiStatus: (aiStatus) => set({ aiStatus }),
}));
```

## Backend — SQLAlchemy state

```python
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String)  # "user" | "assistant" | "system"
    content = Column(Text)
    model_used = Column(String)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Multi-client state

Con Gateway V0.8+, state se complica:
- Telegram user envía mensaje.
- Electron user envía otro mensaje al mismo tiempo.
- Backend procesa ambos en paralelo.
- **Source of truth**: PostgreSQL.

```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    channel VARCHAR,  -- "electron" | "telegram" | ...
    external_id VARCHAR,  -- telegram chat_id
    created_at TIMESTAMP
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER,
    role VARCHAR,
    content TEXT,
    metadata JSONB,  -- canal, tool_calls, etc.
    created_at TIMESTAMP
);
```

## Para V1.0 Orchestrator

V1.0 Orchestrator necesita state management más sofisticado:
- **Conversation state**: cuál es el contexto actual.
- **Task state**: qué tasks están running, cuáles pending.
- **Skill state**: qué skills están cargadas, cuáles invocadas.

Solución: **state machines** (LangGraph-style):
```python
class OrchestratorState:
    conversation_id: str
    current_intent: Intent
    plan: Plan | None
    task_results: dict[str, Any]
    checkpoint: bytes  # for resume
```

## Cross-client consistency

- ✅ **Single source of truth**: PostgreSQL.
- ✅ **Optimistic updates**: frontend asume success, rollback si falla.
- ❌ **Conflict resolution**: dos users editando mismo doc → last-write-wins (simple) o CRDT (complejo).

## Para Aithera (single-user)

Single-user = no hay conflict resolution real. Solo el user Aithera usa Aithera, en 1-2 canales. **last-write-wins** es OK.

## Patrones relacionados

- **Event sourcing**: todos los cambios son eventos append-only.
- **CQRS**: separar read/write models.
- **State machines**: estado como grafo finito.

Aithera V0.7.3 es CRUD simple. V1.0 podría usar state machines para Orchestrator.

## Referencias cruzadas

- [JWIKI-049 async-patterns.md](./async-patterns.md)
- [JWIKI-055 orchestrator-pattern.md](./orchestrator-pattern.md)
- [JWIKI-084 state-zustand.md](../04_FRONTEND/state-zustand.md)
- [JWIKI-120 chromadb.md](../07_MEMORY/chromadb.md)

## Fuentes

1. Zustand docs
2. SQLAlchemy state patterns
3. LangGraph state machines

## Nivel de confianza

**85%** — Patterns bien establecidos.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified