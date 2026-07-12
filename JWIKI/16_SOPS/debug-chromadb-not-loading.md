# SOP — Debug ChromaDB not loading

## Síntomas
- Chat no usa memory (respuestas sin contexto).
- Logs: "Memory features disabled".

## Pasos

1. **Verificar install**:
```bash
pip show chromadb sentence-transformers
```

2. **Verificar path**:
```bash
ls ~/.aithera/chroma/
```

3. **Test manual**:
```python
import chromadb
client = chromadb.PersistentClient(path="~/.aithera/chroma")
print(client.list_collections())
```

4. **Reinstalar**:
```bash
pip install --upgrade chromadb sentence-transformers
```

5. **Limpiar cache modelos**:
```bash
rm -rf ~/.cache/torch/sentence_transformers
```

6. **Restart backend**.

## Verificación

- [ ] `GET /api/memory/status` retorna `enabled: true`.

## Referencias cruzadas

- [JWIKI-120 chromadb.md](../07_MEMORY/chromadb.md)
- [JWIKI-232 chromadb-size-payload.md](../15_KNOWN_PITFALLS/chromadb-size-payload.md)

---

*Estado: 🟢 verified*