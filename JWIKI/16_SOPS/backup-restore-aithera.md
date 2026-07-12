# SOP — Backup restore Aithera

## Cuándo
Antes de cambios importantes, o como cron diario.

## Pasos

### Backup

```bash
# SQLite (desarrollo)
cp ~/.aithera/aithera.db ~/.aithera/backups/aithera_$(date +%Y%m%d).db

# PostgreSQL (producción)
docker exec aithera-postgres pg_dump -U aithera aithera > \
  ~/.aithera/backups/aithera_$(date +%Y%m%d).sql
```

### Restore

```bash
# SQLite
cp ~/.aithera/backups/aithera_20260709.db ~/.aithera/aithera.db

# PostgreSQL
cat ~/.aithera/backups/aithera_20260709.sql | \
  docker exec -i aithera-postgres psql -U aithera -d aithera
```

### Automatización (cron)

```cron
0 3 * * * /usr/local/bin/backup-aithera.sh
```

## Retención

- Daily: 7 días.
- Weekly: 4 semanas.
- Monthly: 12 meses.

## Referencias cruzadas

- [JWIKI-216 backup-restore-db.md](../13_DEPLOYMENT/backup-restore-db.md)

---

*Estado: 🟢 verified*