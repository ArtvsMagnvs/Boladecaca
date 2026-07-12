# SOP — Añadir colección ChromaDB

## Cuándo
Necesitas un nuevo dominio de memory (e.g., "skills", "projects").

## Pasos

1. **Modificar `memory_manager.py`**:
```python
self.new_collection = self.client.get_or_create_collection(
    "new_collection",
    metadata={"description": "..."}
)
```

2. **Añadir métodos**:
```python
async def add_to_new(self, text: str, metadata: dict):
    await self.new_collection.add(...)

async def search_new(self, query: str, top_k: int = 5):
    return await self.new_collection.query(...)
```

3. **API endpoints**:
```python
@router.post("/api/memory/new/search")
async def search_new(request: SearchRequest):
    return await memory_manager.search_new(request.query)
```

4. **Test**:
```bash
curl -X POST http://localhost:8000/api/memory/new/search \
  -d '{"query": "test"}'
```

## Referencias cruzadas

- [JWIKI-120 chromadb.md](../07_MEMORY/chromadb.md)

---

*Estado: 🟢 verified*