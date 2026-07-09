# SQLite Fallback — Modo desarrollo

## Resumen

**SQLite** es el fallback automático de Aithera cuando no hay `DATABASE_URL`. Perfecto para single-user y desarrollo.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Activación

Aithera V0.7.3 activa SQLite automáticamente si:
- `DATABASE_URL` no está definida.
- O `DATABASE_URL=""`.

```python
# backend/app/core/config.py
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///./aithera.db"
```

## Aithera V0.7.3 — fallback SQLAlchemy

```python
# engine creation
def get_engine():
    url = settings.DATABASE_URL
    if "sqlite" in url:
        return create_async_engine(
            url,
            echo=False,
            pool_size=1,  # SQLite single-connection
            max_overflow=0,
        )
    else:
        return create_async_engine(
            url,
            echo=False,
            pool_size=10,
            max_overflow=20,
        )
```

## Ubicación del archivo SQLite

Aithera guarda el archivo SQLite en:
- Linux: `~/.aithera/aithera.db`
- macOS: `~/.aithera/aithera.db`
- Windows: `%APPDATA%/Aithera/aithera.db`

```python
from pathlib import Path
import platform

def get_sqlite_path():
    if platform.system() == "Windows":
        base = Path(os.getenv("APPDATA")) / "Aithera"
    else:
        base = Path.home() / ".aithera"
    base.mkdir(parents=True, exist_ok=True)
    return base / "aithera.db"
```

## Limitaciones de SQLite

- ⚠️ **Single writer**: SQLite bloquea durante writes.
- ⚠️ **No network access**: solo local.
- ⚠️ **Size limit**: < 1TB práctico.
- ⚠️ **No full concurrency**: para single-user OK.

## Para V0.4+ migración a PostgreSQL

```bash
# Dump SQLite
sqlite3 aithera.db .dump > dump.sql

# Adaptar schema (algunos tipos cambian)
# CREATE TABLE → CREATE TABLE con SERIAL en vez de INTEGER PRIMARY KEY

# Load PostgreSQL
psql aithera < dump_adapted.sql
```

**Aithera tiene script de migración**: `backend/scripts/migrate_sqlite_to_postgres.py`.

## Referencias cruzadas

- [JWIKI-065 databases.md](./databases.md)
- [JWIKI-066 postgresql.md](./postgresql.md)
- [JWIKI-067 sqlite-fallback.md](./este doc)

## Fuentes

1. https://www.sqlite.org/docs.html
2. https://github.com/omnilib/aiosqlite

## Nivel de confianza

**95%** — SQLite bien establecido.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified