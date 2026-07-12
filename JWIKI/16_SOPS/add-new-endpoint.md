# SOP — Añadir endpoint FastAPI

## Cuándo
Necesitas un nuevo endpoint API.

## Pasos

1. **Identificar router existente** o crear nuevo:
```bash
ls backend/app/api/endpoints/
```

2. **Añadir endpoint**:
```python
# backend/app/api/endpoints/new_resource.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/new-resource", tags=["new-resource"])

@router.get("/")
async def list_items():
    return {"items": []}

@router.post("/")
async def create_item(item: ItemCreate):
    return await db.add(item)
```

3. **Schemas Pydantic** en `backend/app/db/schemas.py`:
```python
class ItemCreate(BaseModel):
    name: str
```

4. **Registrar en main.py**:
```python
from app.api.endpoints.new_resource import router as new_resource_router
app.include_router(new_resource_router)
```

5. **Test**:
```bash
curl http://localhost:8000/api/new-resource/
curl -X POST http://localhost:8000/api/new-resource/ -d '{"name":"test"}'
```

## Verificación

- [ ] Endpoint aparece en OpenAPI (`/docs`).
- [ ] Tests pasan.

## Referencias cruzadas

- [JWIKI-072 api-design-rest.md](../03_BACKEND/api-design-rest.md)

---

*Estado: 🟢 verified*