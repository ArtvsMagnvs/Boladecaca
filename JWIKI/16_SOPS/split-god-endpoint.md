# SOP — Partir god-endpoint

## Cuándo
Un router pasa de ~500 líneas o mezcla dominios.

## Pasos

1. **Identificar dominios** mezclados (ej. email + calendar).

2. **Crear nuevos archivos**:
```python
# backend/app/api/endpoints/new_resource.py
router = APIRouter(prefix="/api/new-resource")
@router.get("/...")
async def endpoint(): ...
```

3. **Mover endpoints** al router correspondiente.

4. **Crear service layer** si hay lógica compartida:
```python
# backend/app/services/new_service.py
class NewService:
    async def shared_logic(self): ...
```

5. **Update `main.py`**:
```python
app.include_router(new_resource_router)
```

6. **Update tests**.

7. **Verificar backward compatibility** (mismo path).

## Verificación

- [ ] No se rompió ningún endpoint.
- [ ] Tests pasan.

## Lección Aithera

- ✅ `email_assistant.py` (2038 líneas) → 7 routers (V0.7.2).

## Referencias cruzadas

- [JWIKI-241 god-endpoint-pattern.md](../15_KNOWN_PITFALLS/god-endpoint-pattern.md)

---

*Estado: 🟢 verified*