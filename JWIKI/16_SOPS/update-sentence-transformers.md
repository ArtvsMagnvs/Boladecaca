# SOP — Actualizar sentence-transformers model

## Cuándo
Quieres mejorar calidad de embeddings (e.g., `all-mpnet-base-v2` en vez de `all-MiniLM-L6-v2`).

## Pasos

1. **Backup BD** (ChromaDB):
```bash
cp -r ~/.aithera/chroma ~/.aithera/chroma.backup
```

2. **Update modelo en `memory_manager.py`**:
```python
self.model = SentenceTransformer("all-mpnet-base-v2")  # 768-dim
```

3. **Re-embed existing data** (opcional, costoso):
```python
for old_embedding, old_doc, old_meta in old_data:
    new_embedding = new_model.encode(old_doc)
    new_collection.add(...)
```

4. **Restart backend**.

## ⚠️ Importante

- Cambio de modelo = cambio de dimensiones.
- Vector search no es compatible cross-model.
- User verá resultados diferentes (puede mejorar o empeorar).

## Verificación

- [ ] Memory search retorna resultados.

## Referencias cruzadas

- [JWIKI-125 embeddings-sentence-transformers.md](../07_MEMORY/embeddings-sentence-transformers.md)

---

*Estado: 🟢 verified*