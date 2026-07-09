# PostgreSQL — Database primary de Aithera

## Resumen

**PostgreSQL** es la database primary de Aithera cuando `DATABASE_URL` está configurada (V0.4+). Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versiones

| Componente | Versión |
|---|---|
| PostgreSQL | ≥14 (recomendado ≥16) |
| asyncpg | latest (driver async) |
| psycopg2-binary | 2.9.10 (Alembic sync) |
| ChromaDB | optional integration con pgvector |

## Por qué PostgreSQL para Aithera

- ✅ **Async maduro**: `asyncpg` es el driver más rápido.
- ✅ **JSONB**: para metadata flexible (config AI providers, agent allowed_tools).
- ✅ **Full-text search**: para búsqueda de emails.
- ✅ **Production-ready**: battle-tested.
- ✅ **Extensions**: pgvector (ChromaDB), pg_trgm (similarity), etc.

## Setup

```bash
# Crear DB
createdb aithera

# Variable de entorno
DATABASE_URL=postgresql+asyncpg://user:password@localhost/aithera

# Aplicar migrations
alembic upgrade head
```

## Aithera schema (resumen)

Ver [JWIKI-065 databases.md](./databases.md) sección "Schema PostgreSQL clave" para el detalle completo.

## Backup y restore

```bash
# Backup
pg_dump aithera > aithera_backup.sql

# Restore
psql aithera < aithera_backup.sql
```

## Performance tips

- ✅ **Indexes**: en foreign keys (`conversation_id`, `agent_id`, etc.) y campos de búsqueda frecuente (`email`, `created_at`).
- ✅ **EXPLAIN ANALYZE**: para queries lentas.
- ✅ **Connection pooling**: SQLAlchemy `pool_size=10, max_overflow=20`.
- ✅ **JSONB indexes**: GIN indexes para búsqueda en JSONB.

## Para Aithera V0.85+

Considerar:
- **pgvector extension**: para embeddings nativos en Postgres (alternativa a ChromaDB).
- **partitioning**: si `chat_messages` crece mucho, particionar por `created_at`.
- **replication**: si Aithera se vuelve multi-usuario.

## Pitfalls

- ❌ **`text` queries sin parametrizar**: SQL injection risk.
- ❌ **N+1 queries**: usar `selectinload`.
- ❌ **JSONB sin index**: queries lentas.

## Referencias cruzadas

- [JWIKI-065 databases.md](./databases.md)
- [JWIKI-067 sqlite-fallback.md](./sqlite-fallback.md)
- [JWIKI-068 migrations.md](./migrations.md)

## Fuentes

1. https://www.postgresql.org/docs/
2. https://magicstack.github.io/asyncpg/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified