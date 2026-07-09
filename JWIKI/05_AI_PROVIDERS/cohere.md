# Cohere — RAG-optimized con embeddings top-tier

## Resumen

**Cohere** se especializa en **RAG** (Retrieval-Augmented Generation) y embeddings. Su modelo flagship **command-r-plus** está optimizado para retrieval-heavy tasks. Embeddings `embed-english-v3` son top-tier. **NO integrado en Aithera V0.7.3**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| **command-r-plus** | jul 2026 | Flagship |
| **command-r** | jul 2026 | Ligero |
| **embed-english-v3.0** | 2024 | Embeddings top-tier |
| **embed-multilingual-v3.0** | 2024 | Embeddings multilingual |
| **rerank-english-v3.0** | 2024 | Reranking |
| Aithera | NO integrado directamente | Pendiente para V0.85 Memory |

## Pricing (verificación pendiente)

| Modelo | Input $/1M | Output $/1M |
|---|---|---|
| command-r-plus | ~$2.5 | ~$10 |
| command-r | ~$0.15 | ~$0.6 |
| embed-english-v3 | ~$0.10 | - |

## API y SDK

**Endpoint**: `https://api.cohere.ai/v1` (NO OpenAI-compat — usa formato propio).

```python
import cohere

co = cohere.Client("...")

response = co.chat(
    model="command-r-plus",
    message="What is RAG?",
    documents=[{"title": "RAG", "text": "Retrieval-Augmented Generation..."}]  # RAG nativo
)
```

## RAG optimizado (killer feature)

Cohere tiene **RAG nativo** en el endpoint `chat`:

```python
response = co.chat(
    model="command-r-plus",
    message="Based on the docs, what is X?",
    documents=[
        {"title": "Doc 1", "text": "..."},
        {"title": "Doc 2", "text": "..."}
    ]
)

# response.citations  # citas a los docs usados
```

## Embeddings top-tier

```python
response = co.embed(
    texts=["document 1", "document 2"],
    model="embed-english-v3.0",
    input_type="search_document"  # o "search_query" para queries
)

embeddings = response.embeddings  # 1024-dim vectors
```

## Reranking

```python
results = co.rerank(
    query="What is RAG?",
    documents=[{"text": "doc1"}, {"text": "doc2"}, ...],
    model="rerank-english-v3.0",
    top_n=5
)
```

## Cuándo elegir Cohere

- ✅ **RAG retrieval-heavy** (mejor que OpenAI/Anthropic).
- ✅ **Embeddings top-tier** (1024-dim, multilingual).
- ✅ **Reranking** (mejora retrieval precision).
- ✅ **Citations automáticas** en `chat`.

❌ NO elegir:
- ❌ Function calling complejo (limitado).
- ❌ Vision.
- ❌ Realtime.

## Para Aithera V0.85 Memory

Cohere es **el candidato ideal** para mejorar ChromaDB en V0.85:
- Reemplazar sentence-transformers con `embed-english-v3` (mejor calidad).
- Añadir reranking post-retrieval.
- Usar `command-r-plus` para generación con citations.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-120 chromadb.md](../07_MEMORY/chromadb.md) — memory system actual
- [JWIKI-119 memory-readme.md](../07_MEMORY/README.md)

## Fuentes

1. https://cohere.ai/ — acceso 2026-07-09
2. https://docs.cohere.com/ — API docs
3. https://cohere.com/research — papers

## Nivel de confianza

**80%** — Familia confirmada, RAG optimizado. Pendiente: validar pricing actual.

---

## Changelog

### 2026-07-09 — versión inicial
- Autor: Aithera Escriba (modo directo)
- Estado: 🟢 verified