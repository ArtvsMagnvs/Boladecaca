# SOP — Añadir modelo SQLAlchemy

## Cuándo
Necesitas persistir una nueva entidad.

## Pasos

1. **Añadir modelo** en `backend/app/db/database.py`:
```python
class NewEntity(Base):
    __tablename__ = "new_entities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

2. **Schema Pydantic** en `schemas.py`:
```python
class NewEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
```

3. **Generar migration**:
```bash
cd backend
alembic revision --autogenerate -m "add new_entities table"
```

4. **Revisar migration generada** en `alembic/versions/`.

5. **Aplicar**:
```bash
alembic upgrade head
```

## Verificación

- [ ] Tabla creada en DB.
- [ ] API endpoints funcionan.

## Rollback

```bash
alembic downgrade -1
```

## Referencias cruzadas

- [JWIKI-236 alembic-divergence.md](../15_KNOWN_PITFALLS/alembic-divergence.md)

---

*Estado: 🟢 verified*