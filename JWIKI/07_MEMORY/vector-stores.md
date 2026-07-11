# Vector stores — Comparativa

## Resumen

Vector stores (bases de datos de embeddings) comparados. Aithera V0.7.3 usa **ChromaDB**. Comparativa con Pinecone, Qdrant, Weaviate, Milvus, pgvector.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Comparativa

| Vector store | Stars | Self-host | License | Aithera |
|---|---|---|---|---|
| **ChromaDB** | 12k | ✅ simple | Apache-2.0 | ✅ V0.6+ |
| Pinecone | n/a (closed) | ❌ (managed) | Propietaria | ❌ |
| Qdrant | 18k | ✅ Rust | Apache-2.0 | ❌ |
| Weaviate | 9k | ✅ Go | Apache-2.0 (BSD-3) | ❌ |
| Milvus | 30k | ✅ Go/C++ | Apache-2.0 | ❌ |
| pgvector | n/a (ext) | ✅ PostgreSQL | PostgreSQL | ⏳ V0.85+ |

## ChromaDB — el elegido

**Por qué**:
- ✅ **Simple**: pip install, sin servidor.
- ✅ **Embedded mode**: perfecto para single-user.
- ✅ **Embeddings built-in**: sentence-transformers default.
- ✅ **Documentado**.

## Pinecone — alternativa managed

Pinecone es **SaaS only** (no self-host). Excelente performance y escala, pero:
- ❌ Costo mensual alto.
- ❌ Datos fuera de tu control.

**Para Aithera**: no aplica (single-user local).

## Qdrant — alternativa Rust

Qdrant es **Rust-native**, muy rápido, soporta filtros complejos. Buena opción para producción.

```python
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)
client.upsert(
    collection_name="docs",
    points=[{"id": 1, "vector": [0.1, 0.2, ...], "payload": {"text": "..."}}]
)
```

## pgvector — alternativa en PostgreSQL

Aithera V0.4+ ya usa PostgreSQL. pgvector extension añade vector search:

```sql
CREATE EXTENSION vector;
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER,
    embedding vector(384)
);
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

**Ventaja**: zero extra infra (usa la DB existente).

## Weaviate — GraphQL-first

Weaviate tiene **GraphQL API** + módulos de ML. Más complejo.

## Milvus — alta escala

Milvus es para **millones de vectores**. Overkill para Aithera.

## Para Aithera V0.85

Considerar migración a **pgvector**:
- ✅ Zero infra extra.
- ✅ Mismo backup (pg_dump).
- ✅ Performance suficiente para 100K-1M vectors.

ChromaDB es OK para V0.6+ pero **pgvector escala mejor**.

## ChromaDB arquitectura

```
ChromaDB
├── Collections (analogous to tables)
│   ├── Documents (text)
│   ├── Embeddings (vectors)
│   └── Metadata (filterable)
├── Embedding function (sentence-transformers default)
└── PersistentClient (SQLite / DuckDB)
```

## Aithera V0.7.3 collections

```python
# backend/app/memory/memory_manager.py
collections = {
    "conversations": "Chat messages con embeddings",
    "user_context": "Preferencias y datos del usuario",
    "documents": "Documentos indexados (uploaded)"
}
```

## Referencias cruzadas

- [JWIKI-120 chromadb.md](./chromadb.md)
- [JWIKI-121 pinecone.md](./pinecone.md)
- [JWIKI-127 rag-patterns-naive.md](./rag-patterns-naive.md)

## Fuentes

1. https://www.trychroma.com/
2. https://qdrant.tech/
3. https://github.com/pgvector/pgvector
4. https://milvus.io/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified