# Document Indexing — Chunking strategies y metadata

## Resumen

Document indexing: cómo partir documentos grandes en chunks para embedding. Crítico para RAG de calidad.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Estrategias de chunking

| Estrategia | Descripción | Pros | Cons |
|---|---|---|---|
| **Fixed-size** | chunks de N tokens fijos | simple | corta sentences |
| **Sentence** | 1 chunk = N sentences | preserva semántica | variable size |
| **Paragraph** | 1 chunk = 1 paragraph | semántica natural | muy variable |
| **Semantic** | split por cambio semántico | mejor calidad | lento, requiere embeddings |
| **Sliding window** | overlap entre chunks | no pierde contexto | duplica storage |
| **Recursive** | split jerárquico (paragraphs → sentences) | balance | complejo |

## Aithera V0.7.3

Aithera usa **sentence-based** chunking simple:

```python
def chunk_text(text: str, max_chunk_size: int = 500) -> list[str]:
    sentences = text.split(". ")
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_chunk_size:
            if current:
                chunks.append(current)
            current = sentence
        else:
            current += ". " + sentence
    return chunks
```

## Mejores prácticas

- ✅ **Chunk size**: 200-500 tokens (sweet spot).
- ✅ **Overlap**: 10-20% para no perder contexto entre chunks.
- ✅ **Metadata**: source, page, section, timestamp.
- ✅ **Normalize whitespace**.

## Para Aithera V0.85

V0.85 debería mejorar chunking:
- ✅ **Recursive chunking** (LangChain-style).
- ✅ **Overlap 50 tokens** entre chunks.
- ✅ **Metadata rico**: source_doc, page, section, chunk_index.
- ✅ **Semantic chunking** opcional (vía Ollama).

```python
# LangChain-style recursive
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""]
)
chunks = splitter.split_text(document_text)

for i, chunk in enumerate(chunks):
    memory.documents.add(
        documents=[chunk],
        metadatas=[{
            "source": "doc.pdf",
            "page": i // 4,
            "chunk_index": i
        }],
        ids=[f"doc-chunk-{i}"]
    )
```

## Embedding model limits

- **sentence-transformers**: max 512 tokens.
- **OpenAI text-embedding-3-small**: max 8191 tokens.
- Truncar antes de embed si es necesario.

## Eval chunking

Cómo medir:
- **Retrieval accuracy** @k: % queries donde top-k contiene el chunk relevante.
- **Chunk coherence**: ¿el chunk tiene sentido standalone?

## References

- [JWIKI-120 chromadb.md](./chromadb.md)
- [JWIKI-127 rag-patterns.md](./rag-patterns.md)

## Fuentes

1. https://www.trychroma.com/
2. https://docs.langchain.com/docs/modules/data_connection/document_transformers/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified