# Alembic — Migration tool en uso en Aithera

## Resumen

**Alembic** es la herramienta de migrations para SQLAlchemy. Aithera V0.7.3 la usa extensivamente (12+ migraciones).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Alembic 1.13+ (CLAUDE.md §2).

## Setup

```python
# alembic/env.py (Aithera setup)
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db.database import Base  # Aithera's Base
from app.core.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

## Comandos Aithera

```bash
# Aplicar migrations (startup script)
cd backend && alembic upgrade head

# Crear nueva migration
alembic revision --autogenerate -m "V0.85: add skill_activations table"

# Rollback
alembic downgrade -1

# Ver estado actual
alembic current
```

## Workflow típico

1. Modificar modelo en `app/db/database.py`.
2. `alembic revision --autogenerate -m "descripcion"`.
3. Revisar el archivo generado en `alembic/versions/`.
4. `alembic upgrade head` para aplicar.
5. Commit el archivo de migration.

## Pitfalls

- ❌ **Modificar migration ya aplicada**: NUNCA.
- ❌ **No probar downgrade**: puede haber datos perdidos.
- ❌ **Migration que no es idempotente**: problemas en retry.

## Migraciones Aithera (resumen)

Ver [JWIKI-068 migrations.md](./migrations.md) sección "Aithera migrations".

## Para V0.85+

Crear nuevas migrations para:
- `skill_activations` (V0.85 Skills).
- `automation_rules` (V0.9 Automation).
- `orchestrator_tasks` (V1.0 Orchestrator).

## Referencias cruzadas

- [JWIKI-068 migrations.md](./migrations.md)
- [JWIKI-064 sqlalchemy-2.md](./sqlalchemy-2.md)
- [JWIKI-066 postgresql.md](./postgresql.md)

## Fuentes

1. https://alembic.sqlalchemy.org/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified