# RAG Patterns — Naive, Hybrid, Reranking, HyDE

## Resumen

**RAG** (Retrieval-Augmented Generation) es el patrón que permite a un LLM responder con contexto externo. 4 patrones principales.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## 1. Naive RAG

El más simple:

```python
def naive_rag(query: str, llm, vector_store, top_k: int = 5) -> str:
    docs = vector_store.search(query, top_k=top_k)
    context = "\n\n".join([d.text for d in docs])
    response = llm.chat(
        system=f"Use este contexto para responder:\n{context}",
        user=query
    )
    return response
```

**Pros**: simple, rápido.
**Cons**: solo semantic search (no keywords), sin reranking.

## 2. Hybrid Search (BM25 + semantic)

Combina keyword search (BM25) con semantic:

```python
from rank_bm25 import BM25Okapi

def hybrid_rag(query: str, llm, vector_store, bm25_index, top_k: int = 5):
    # Semantic
    semantic = vector_store.search(query, top_k=top_k*2)
    
    # BM25
    bm25_scores = bm25_index.get_scores(query.split())
    bm25_top = sorted(zip(bm25_scores, docs), key=lambda x: -x[0])[:top_k*2]
    
    # RRF (Reciprocal Rank Fusion)
    fused = rrf_fuse(semantic, bm25_top)
    return fused[:top_k]
```

**Pros**: mejor recall (keywords + semantics).
**Cons**: más complejo, 2 indexes.

## 3. Reranking

Después de retrieval inicial, rerankear con modelo más potente:

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")

def reranked_rag(query: str, llm, vector_store, top_k: int = 5, rerank_top: int = 20):
    # Initial retrieval (más candidatos)
    candidates = vector_store.search(query, top_k=rerank_top)
    
    # Rerank
    scores = reranker.predict([(query, c.text) for c in candidates])
    reranked = sorted(zip(scores, candidates), key=lambda x: -x[0])[:top_k]
    
    # Generate
    context = "\n\n".join([c.text for _, c in reranked])
    return llm.chat(...)
```

**Pros**: mejor precision (top-K con cross-encoder).
**Cons**: latencia + coste (reranker model).

## 4. HyDE (Hypothetical Document Embeddings)

LLM genera **respuesta hipotética** primero, luego busca con eso:

```python
def hyde_rag(query: str, llm, vector_store):
    # Generate hypothetical answer
    hypothetical = llm.chat(
        system="Responde a la pregunta de forma detallada y técnica.",
        user=query
    )
    # Use hypothetical as search query
    docs = vector_store.search(hypothetical, top_k=5)
    # Real answer with context
    context = "\n\n".join([d.text for d in docs])
    return llm.chat(...)
```

**Pros**: mejor recall (query es más rico).
**Cons**: 1 LLM call extra, latencia.

## Comparativa

| Pattern | Recall | Precision | Coste | Latencia |
|---|---|---|---|---|
| Naive | ⭐⭐ | ⭐⭐ | bajo | bajo |
| Hybrid | ⭐⭐⭐⭐ | ⭐⭐⭐ | medio | medio |
| Reranking | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | medio-alto | medio-alto |
| HyDE | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | alto | alto |

## Para Aithera V0.85

V0.85 MOS (Memory Operating System) podría añadir:
- **Hybrid search** (semantic + keyword).
- **Reranking** con cross-encoder.
- **Briefing automático** con resumen jerárquico.

Plan Maestro 2026 `07_MOS_V085_DISENO.md` y `08_MOS_ARQUITECTURA_COMPLETA.md`.

## RAG eval

Cómo medir calidad:
- **Hit rate @ k**: % de queries donde el doc relevante está en top-k.
- **MRR** (Mean Reciprocal Rank).
- **Human eval**: gold standard.

## Referencias cruzadas

- [JWIKI-120 chromadb.md](./chromadb.md)
- [JWIKI-119 vector-stores.md](./vector-stores.md)

## Fuentes

1. https://docs.ragas.io/
2. https://huggingface.co/BAAI/bge-reranker-v2-m3
3. https://arxiv.org/abs/2212.10496 (HyDE)

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified