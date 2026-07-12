# Alembic Schema Divergence

## Resumen

**Alembic** requiere migrations cuando cambias el modelo ORM. Si modificas sin migration, el schema diverge del modelo.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Workflow

```bash
# 1. Modificar modelo
class Project(Base):
    new_field: str = "default"  # <- añadido

# 2. Generar migration
cd backend
alembic revision --autogenerate -m "add new_field to projects"

# 3. Revisar migration generada
# backend/alembic/versions/xxxx_add_new_field_to_projects.py
def upgrade():
    op.add_column("projects", sa.Column("new_field", sa.String, default="default"))

# 4. Aplicar
alembic upgrade head
```

## Pitfalls

- ❌ **Modificar modelo sin migration**: schema DB diverge.
- ❌ **Olvidar autogenerate**: perder cambios.
- ❌ **Migrations no revisadas**: a veces generan SQL incorrecto.

## Detección

```bash
alembic check  # Detecta divergencia
# Output: "FAILED: 1 issue detected"  → migration needed
```

## Para Aithera

- ✅ V0.4+: Alembic 1.13+ (CLAUDE.md §2).
- ✅ V0.8: migration `d4e5f6a7b8c9_v08_encrypt_api_keys`.

## Referencias cruzadas

- [JWIKI-069 alembic.md](../03_BACKEND/alembic.md)
- CLAUDE.md §2

## Fuentes

1. https://alembic.sqlalchemy.org/

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified