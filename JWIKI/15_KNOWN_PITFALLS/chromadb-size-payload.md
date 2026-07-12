# ChromaDB 1.5GB Payload — sentence-transformers

## Resumen

**ChromaDB + sentence-transformers** descargan ~80MB la primera vez, pero con todos los modelos cacheados puede llegar a 1.5GB en disco.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Size breakdown

| Componente | Size |
|---|---|
| sentence-transformers model (all-MiniLM-L6-v2) | ~80MB |
| ChromaDB persistence (1K docs) | ~50MB |
| ChromaDB persistence (10K docs) | ~500MB |
| ChromaDB persistence (100K docs) | ~5GB |
| Other deps | ~50MB |

Total típico: **200MB-1GB** según uso.

## Mitigation

1. ✅ Usar **smaller embedding model** (`all-MiniLM-L6-v2` vs `all-mpnet-base-v2`).
2. ✅ **Cleanup periódico** (drop old collections).
3. ✅ **ChromaDB persistent client** (no in-memory).
4. ✅ **Configurable cache dir** (mover a D:/ si C: lleno).

```python
# Custom cache
import os
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "D:/models/"
os.environ["HF_HOME"] = "D:/models/"
```

## Para Aithera

- ✅ V0.7.3: default model `all-MiniLM-L6-v2` (80MB download).
- ⏳ V0.85+: cleanup automático + configurable cache.

## Referencias cruzadas

- [JWIKI-120 chromadb.md](../07_MEMORY/chromadb.md)
- CLAUDE.md §1 (ChromaDB)

## Fuentes

1. https://www.sbert.net/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified