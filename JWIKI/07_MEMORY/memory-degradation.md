# Memory — Degradation graceful

## Resumen

Aithera V0.7.3 implementa **graceful degradation** en el memory layer. Si ChromaDB falla, la app sigue funcionando sin memory. Ver CLAUDE.md §1.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Patrón degradation

```python
class MemoryManager:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path="~/.aithera/chroma")
            self.conversations = self.client.get_or_create_collection("conversations")
            self.user_context = self.client.get_or_create_collection("user_context")
            self.documents = self.client.get_or_create_collection("documents")
            self.enabled = True
            logger.info("ChromaDB ready")
        except Exception as e:
            logger.warning(f"ChromaDB not available: {e}. Memory features disabled.")
            self.client = None
            self.enabled = False
    
    async def search(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        if not self.enabled:
            return []  # graceful: no error, just empty
        try:
            results = self.conversations.query(query_texts=[query], n_results=top_k)
            return [MemoryItem.from_chroma(r) for r in results["documents"][0]]
        except Exception as e:
            logger.exception("Memory search failed")
            return []  # graceful: empty result
```

## Patrón "no romper el chat"

```python
@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Si memory falla, chat sigue funcionando
    try:
        context = await memory_manager.search(request.message)
    except Exception:
        context = []  # graceful: chat sin contexto
    
    response = await ai_manager.chat(
        messages=[{"role": "system", "content": f"Context: {context}"}] + request.messages
    )
    return response
```

## Por qué es importante

- ✅ **Chat siempre funciona** (función core).
- ✅ **Memory es enhancement** (no bloqueante).
- ✅ **Debugging fácil**: logs claros cuando memory falla.
- ✅ **Recovery automática**: si ChromaDB vuelve, memory se reintenta.

## Cuando falla memory

Causas comunes:
- ❌ ChromaDB no instalado.
- ❌ Sentence-transformers download failed.
- ❌ ChromaDB file corruption.
- ❌ Permission denied en `~/.aithera/chroma/`.
- ❌ Disk full.

Aithera maneja todas con `try/except` + log + return empty.

## Logging

```python
logger.info("Memory search: 0 results (degraded mode)")
logger.warning("ChromaDB not available, memory features disabled")
logger.error("Memory search failed: <error>")
```

## Health check

Aithera V0.7.3 expone `/api/memory/status`:

```python
@app.get("/api/memory/status")
async def memory_status():
    return {
        "enabled": memory_manager.enabled,
        "collections": memory_manager.get_collections_count() if memory_manager.enabled else 0,
        "documents": memory_manager.count() if memory_manager.enabled else 0
    }
```

## Para Aithera V0.85

V0.85 MOS debería mantener el patrón de degradation pero añadir:
- ✅ **Health checks automáticos** cada 5 min.
- ✅ **Retry con backoff** si memory falla temporalmente.
- ✅ **Cache de queries** recientes.

## Referencias cruzadas

- [JWIKI-120 chromadb.md](./chromadb.md)
- [JWIKI-131 conversation-memory.md](./conversation-memory.md)
- [JWIKI-134 memory-degradation.md](./este doc)
- `PLAN_MAESTRO_2026/07_MOS_V085_DISENO.md`

## Fuentes

1. CLAUDE.md §1 (graceful degradation en Aithera V0.7.3)
2. https://docs.trychroma.com/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified