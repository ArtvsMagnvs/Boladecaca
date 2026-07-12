# PostgreSQL en Docker

## Resumen

**PostgreSQL 16+** corre en Docker para Aithera SaaS / multi-user (V1.0+). Single-user desktop usa SQLite fallback.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Quick start

```bash
docker run -d \
    --name aithera-postgres \
    -e POSTGRES_USER=aithera \
    -e POSTGRES_PASSWORD=secret \
    -e POSTGRES_DB=aithera \
    -v postgres_data:/var/lib/postgresql/data \
    -p 5432:5432 \
    postgres:16
```

## Connection string

```
postgresql+asyncpg://aithera:secret@localhost:5432/aithera
```

## Backup

```bash
docker exec aithera-postgres pg_dump -U aithera aithera > backup.sql
```

## Restore

```bash
cat backup.sql | docker exec -i aithera-postgres psql -U aithera -d aithera
```

## Para Aithera

- ❌ V0.7.3: SQLite fallback only.
- ⏳ V1.0+: Docker Postgres para SaaS.

## Referencias cruzadas

- [JWIKI-209 docker-compose-backend.md](./docker-compose-backend.md)
- [JWIKI-066 postgresql.md](../03_BACKEND/postgresql.md)

## Fuentes

1. https://hub.docker.com/_/postgres

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified