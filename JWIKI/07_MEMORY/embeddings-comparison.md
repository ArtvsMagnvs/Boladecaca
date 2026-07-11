# Embeddings — sentence-transformers, OpenAI, Cohere

## Resumen

**Embeddings** son la representación vectorial de texto que permite similarity search. Aithera V0.6+ usa sentence-transformers (local). Comparativa con OpenAI, Cohere, Voyage.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Comparativa

| Modelo | Dimensiones | Costo | Calidad (MTEB) | Aithera |
|---|---|---|---|---|
| **all-MiniLM-L6-v2** (sentence-transformers) | 384 | gratis | ⭐⭐⭐ | ✅ default |
| all-mpnet-base-v2 (sentence-transformers) | 768 | gratis | ⭐⭐⭐⭐ | ⏳ upgrade |
| text-embedding-3-small (OpenAI) | 1536 | $0.02/1M | ⭐⭐⭐⭐ | ⏳ V0.85+ |
| text-embedding-3-large (OpenAI) | 3072 | $0.13/1M | ⭐⭐⭐⭐⭐ | ⏳ V0.85+ |
| embed-english-v3.0 (Cohere) | 1024 | $0.10/1M | ⭐⭐⭐⭐⭐ | ⏳ V0.85+ |
| voyage-3 (Voyage AI) | 1024 | $0.06/1M | ⭐⭐⭐⭐⭐ | ❌ |

## sentence-transformers (default Aithera)

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")  # default
embeddings = model.encode([
    "Aithera is an AI assistant",
    "Aithera uses ChromaDB for memory"
])
# shape: (2, 384)
```

**Ventajas**:
- ✅ Gratis, local.
- ✅ Privacidad (no sale del PC).
- ✅ Rápido en CPU.
- ❌ Calidad menor que OpenAI large.
- ❌ Descarga inicial ~80MB.

## OpenAI embeddings

```python
from openai import OpenAI

client = OpenAI()
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=["Aithera is an AI assistant"]
)
embedding = response.data[0].embedding  # 1536-dim
```

**Ventajas**:
- ✅ Top quality.
- ✅ Sin descarga.
- ❌ Costo (~$0.02/1M tokens para small).

## Cohere embed-english-v3.0

```python
import cohere
co = cohere.Client("...")
response = co.embed(
    texts=["Aithera is an AI assistant"],
    model="embed-english-v3.0",
    input_type="search_document"
)
embedding = response.embeddings[0]  # 1024-dim
```

**Ventajas**:
- ✅ Top quality.
- ✅ Multilingual opcional.
- ❌ Costo.

## Para Aithera V0.85+

Considerar upgrade a:
- **all-mpnet-base-v2** (gratis, mejor que MiniLM).
- **text-embedding-3-small** (OpenAI, $0.02/1M, top quality).

## Embedding dimensions trade-off

| Dim | Pros | Cons |
|---|---|---|
| 384 (MiniLM) | rápido, ligero | menos preciso |
| 768 (mpnet) | balance | medio |
| 1536 (OpenAI small) | top | más storage |
| 3072 (OpenAI large) | top | pesado |

## Cuantización

Para reducir storage, ChromaDB soporta cuantización (reduce dim 4-32x con pérdida mínima).

## Para Aithera

V0.6+: `all-MiniLM-L6-v2` (gratis, local, 384-dim).
V0.85+: considerar upgrade.

## Referencias cruzadas

- [JWIKI-120 chromadb.md](./chromadb.md)
- [JWIKI-125 embeddings-sentence-transformers.md](./embeddings-sentence-transformers.md)
- [JWIKI-127 rag-patterns-naive.md](./rag-patterns-naive.md)

## Fuentes

1. https://www.sbert.net/
2. https://platform.openai.com/docs/guides/embeddings
3. https://docs.cohere.com/docs/embeddings
4. https://huggingface.co/spaces/mteb/leaderboard

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified