# ChromaDB — Vector store en uso en Aithera

## Resumen

**ChromaDB** es el vector store de Aithera V0.6+. Embedded, simple, ideal para single-user. Ver CLAUDE.md §1 ("ChromaDB").

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

ChromaDB 0.4+ (CLAUDE.md §1).

## Por qué ChromaDB

- ✅ **Embedded**: corre en proceso, sin servidor.
- ✅ **SQLite/DuckDB** persistence: archivo `.chroma/`.
- ✅ **Sentence-transformers** default embeddings (~80MB descarga).
- ✅ **Pythonic API**: simple.
- ✅ **Filterable metadata**.

## Setup

```bash
pip install chromadb
# Auto-descarga sentence-transformers (~80MB)
```

## Aithera V0.6+ collections

```python
# backend/app/memory/memory_manager.py
import chromadb
from chromadb.config import Settings

class MemoryManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="~/.aithera/chroma",
            settings=Settings(anonymized_telemetry=False)
        )
        self.conversations = self.client.get_or_create_collection("conversations")
        self.user_context = self.client.get_or_create_collection("user_context")
        self.documents = self.client.get_or_create_collection("documents")
    
    async def search(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        results = self.conversations.query(
            query_texts=[query],
            n_results=top_k
        )
        return [MemoryItem.from_chroma(r) for r in results["documents"][0]]
    
    async def add(self, text: str, metadata: dict, collection: str = "conversations"):
        getattr(self, collection).add(
            documents=[text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )
```

## Embeddings default

- **Modelo**: all-MiniLM-L6-v2 (sentence-transformers).
- **Dimensiones**: 384.
- **Tamaño**: ~80MB descarga inicial.
- **Velocidad**: ~1000 sentences/seg en CPU.

## Aithera Memory API

```python
# POST /api/memory/search
{
    "query": "Aithera project info",
    "top_k": 5
}

# Response
{
    "results": [
        {"text": "...", "metadata": {...}, "distance": 0.12},
        ...
    ]
}
```

## Persistencia

ChromaDB persiste en `~/.aithera/chroma/` (SQLite + binarios).

## Graceful degradation (CLAUDE.md §1)

Aithera degrada gracefully si ChromaDB falla:
```python
try:
    self.client = chromadb.PersistentClient(...)
except Exception:
    logger.warning("ChromaDB not available, memory features disabled")
    self.client = None
```

## Para Aithera V0.85

Considerar migración a **pgvector**:
- Aithera ya tiene PostgreSQL.
- pgvector unified DB.
- Mejor scaling.

Mantener ChromaDB para backward compat.

## Referencias cruzadas

- [JWIKI-119 vector-stores.md](./vector-stores.md)
- [JWIKI-127 rag-patterns-naive.md](./rag-patterns-naive.md)

## Fuentes

1. https://www.trychroma.com/
2. CLAUDE.md §1
3. https://github.com/chroma-core/chroma

## Nivel de confianza

**95%** — ChromaDB estable, bien documentado.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified