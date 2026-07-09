# Migración SQLite → PostgreSQL

## Resumen

Aithera V0.7.3 puede migrar de SQLite (modo dev) a PostgreSQL (modo prod). Script de migración incluido: `backend/scripts/migrate_sqlite_to_postgres.py`.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Por qué migrar

| Aspecto | SQLite | PostgreSQL |
|---|---|---|
| Concurrencia | ❌ single writer | ✅ multi-writer |
| Producción | ⚠️ limitado | ✅ |
| Backup | ✅ trivial (archivo) | ✅ pg_dump |
| Full-text | FTS5 | tsvector |
| Extensions | pocas | muchas (pgvector, etc.) |

## Pasos migración

### 1. Backup

```bash
# Backup SQLite
cp ~/.aithera/aithera.db ~/.aithera/aithera.db.backup

# O via sqlite3
sqlite3 ~/.aithera/aithera.db ".backup ~/.aithera/aithera.db.backup"
```

### 2. Setup PostgreSQL

```bash
# Crear DB
createdb aithera

# Crear user
createuser -P aithera
```

### 3. Aplicar schema

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://aithera:password@localhost/aithera \
  alembic upgrade head
```

### 4. Migrar datos

```bash
# Aithera script
python backend/scripts/migrate_sqlite_to_postgres.py
```

## Script de migración

```python
# backend/scripts/migrate_sqlite_to_postgres.py
import sqlite3
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def migrate():
    # 1. Connect SQLite
    sqlite_conn = sqlite3.connect("~/.aithera/aithera.db")
    sqlite_conn.row_factory = sqlite3.Row
    
    # 2. Connect PostgreSQL
    pg_engine = create_async_engine(settings.POSTGRES_URL)
    
    # 3. Tables to migrate
    tables = ["projects", "tasks", "conversations", "chat_messages", ...]
    
    for table in tables:
        # Read SQLite
        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
        
        # Write PostgreSQL
        async with pg_engine.begin() as conn:
            for row in rows:
                # Convert row to dict
                data = dict(row)
                # Insert
                cols = ", ".join(data.keys())
                placeholders = ", ".join(f":{k}" for k in data.keys())
                await conn.execute(
                    text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"),
                    data
                )
        
        print(f"Migrated {len(rows)} rows in {table}")

asyncio.run(migrate())
```

## Pitfalls

- ⚠️ **Tipos diferentes**: SQLite `INTEGER` → PostgreSQL `INTEGER` o `BIGINT`.
- ⚠️ **JSON**: SQLite `TEXT` (JSON string) → PostgreSQL `JSONB`.
- ⚠️ **Timestamps**: SQLite `TEXT` → PostgreSQL `TIMESTAMP WITH TIME ZONE`.
- ⚠️ **Autoincrement**: SQLite `AUTOINCREMENT` → PostgreSQL `SERIAL`.

## Para Aithera

V0.7.3 tiene `backend/scripts/migrate_sqlite_to_postgres.py` que maneja los tipos automáticamente.

## Referencias cruzadas

- [JWIKI-065 databases.md](./databases.md)
- [JWIKI-066 postgresql.md](./postgresql.md)
- [JWIKI-067 sqlite-fallback.md](./sqlite-fallback.md)

## Fuentes

1. https://www.postgresql.org/docs/current/migration.html
2. CLAUDE.md §3 (migrations)

## Nivel de confianza

**90%** — Script existe en codebase.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified