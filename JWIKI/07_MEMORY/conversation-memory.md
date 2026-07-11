# Conversation Memory — Short-term y long-term

## Resumen

Conversation memory: lo que el LLM "recuerda" entre turnos. Aithera V0.7.3 combina DB persistente (SQLAlchemy) + ChromaDB semantic search.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Tipos de memory

| Tipo | Scope | Storage | Aithera |
|---|---|---|---|
| **Short-term** | Conversación actual | Messages array | ✅ |
| **Long-term** | Cross-conversación | ChromaDB | ✅ |
| **Episodic** | Eventos del user | ChromaDB | ⏳ V0.85+ |
| **Semantic** | Hechos sobre el user | ChromaDB | ⏳ V0.85+ |
| **Procedural** | Skills del user | (a definir) | ⏳ V1.0+ |

## Aithera V0.7.3 implementation

```python
# backend/app/memory/memory_manager.py
class MemoryManager:
    async def add_message(self, conversation_id: int, message: ChatMessage):
        # 1. Persist to DB
        await self.db.add(message)
        
        # 2. Index in ChromaDB (semantic search)
        await self.conversations.add(
            documents=[message.content],
            metadatas=[{
                "conversation_id": conversation_id,
                "role": message.role,
                "timestamp": message.created_at.isoformat()
            }],
            ids=[str(message.id)]
        )
    
    async def get_context(self, conversation_id: int, query: str) -> list[MemoryItem]:
        # Semantic search
        results = await self.conversations.query(
            query_texts=[query],
            n_results=5,
            where={"conversation_id": conversation_id}  # filter
        )
        return results
```

## Memory injection en chat

```python
@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 1. Get relevant context from memory
    context = await memory_manager.get_context(
        conversation_id=request.conversation_id,
        query=request.message
    )
    
    # 2. Inject into messages
    messages = [
        {"role": "system", "content": f"Relevant context: {context}"},
        *request.messages
    ]
    
    # 3. Generate
    response = await ai_manager.chat(messages)
    return response
```

## Window size

Aithera NO implementa windowing (enviar TODO el historial). Para conversaciones largas (>100 mensajes), considerar summarization.

## Para Aithera V0.85

V0.85 MOS (Memory Operating System) debería:
- ✅ **Window + summary** para long conversations.
- ✅ **Episodic memory**: "el user preguntó X hace 3 días".
- ✅ **Semantic memory**: "el user prefiere Y".
- ✅ **Auto-ingest** desde Gmail/Calendar (P3 de Plan Maestro 2026).

## References

- [JWIKI-120 chromadb.md](./chromadb.md)
- [JWIKI-127 rag-patterns.md](./rag-patterns.md)
- `PLAN_MAESTRO_2026/07_MOS_V085_DISENO.md`

## Fuentes

1. https://www.trychroma.com/
2. Plan Maestro 2026 §07

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified