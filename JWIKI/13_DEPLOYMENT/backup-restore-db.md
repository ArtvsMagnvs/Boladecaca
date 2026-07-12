# Backup / Restore PostgreSQL

## Resumen

**pg_dump** y **pg_restore** son las herramientas oficiales para backup/restore de PostgreSQL. Crítico para Aithera V0.85+ SaaS.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Backup

```bash
# Logical backup (SQL)
pg_dump -U aithera -h localhost aithera > backup_$(date +%Y%m%d).sql

# Custom format (compressed, parallel restore)
pg_dump -U aithera -h localhost -Fc aithera > backup.dump

# Compressed plain SQL
pg_dump -U aithera -h localhost aithera | gzip > backup.sql.gz
```

## Restore

```bash
# SQL format
psql -U aithera -h localhost aithera < backup.sql

# Custom format
pg_restore -U aithera -h localhost -d aithera backup.dump
```

## Automated backup

```bash
#!/bin/bash
# backup-aithera.sh (cron daily)
BACKUP_DIR=/backups/aithera
DATE=$(date +%Y%m%d_%H%M)
mkdir -p $BACKUP_DIR

pg_dump -U aithera -h localhost -Fc aithera > $BACKUP_DIR/aithera_$DATE.dump

# Retain 30 days
find $BACKUP_DIR -name "*.dump" -mtime +30 -delete
```

## Cron setup

```cron
# Daily at 3am
0 3 * * * /usr/local/bin/backup-aithera.sh
```

## Para Aithera

- ⏳ V0.85+: automated daily backup.
- ⏳ V0.85+: S3 / cloud backup.

## Referencias cruzadas

- [JWIKI-210 docker-postgres.md](./docker-postgres.md)

## Fuentes

1. https://www.postgresql.org/docs/current/backup.html

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified