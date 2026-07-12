# SOP — Migrar SQLite → PostgreSQL

## Cuándo
Producción / multi-user setup.

## Pasos

1. **Setup PostgreSQL**:
```bash
docker run -d --name aithera-postgres \
  -e POSTGRES_USER=aithera \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=aithera \
  -p 5432:5432 postgres:16
```

2. **Update `.env`**:
```
DATABASE_URL=postgresql+asyncpg://aithera:secret@localhost/aithera
```

3. **Aplicar migrations**:
```bash
cd backend
alembic upgrade head
```

4. **Migrar datos**:
```bash
python scripts/migrate_sqlite_to_postgres.py
```

5. **Verificar**:
```bash
# Contar filas en ambas DBs
sqlite3 ~/.aithera/aithera.db "SELECT COUNT(*) FROM projects"
psql -U aithera -d aithera -c "SELECT COUNT(*) FROM projects"
```

## Verificación

- [ ] Conteos idénticos.
- [ ] Foreign keys funcionan.
- [ ] App arranca con PostgreSQL.

## Referencias cruzadas

- [JWIKI-078 sqlite-postgres-migration.md](../03_BACKEND/sqlite-postgres-migration.md)

---

*Estado: 🟢 verified*