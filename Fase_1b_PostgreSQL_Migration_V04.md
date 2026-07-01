# FASE 1b — V0.4: Migración SQLite → PostgreSQL
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.4.0
**Prerrequisito**: Aithera V0.3.0 completada y funcionando
**Sesiones**: 2

---

## PRINCIPIO FUNDAMENTAL

Los modelos SQLAlchemy, los schemas Pydantic, los endpoints y el frontend no se tocan. Solo cambia el engine de base de datos.

---

## SESIÓN 1: Instalar PostgreSQL y preparar la migración

**Tiempo estimado**: 1-2 horas
**Empieza con**: Aithera V0.3.0 funcionando con SQLite

### Paso 1 — Instalar PostgreSQL 16

Descargar PostgreSQL 16 desde https://www.postgresql.org/download/windows/ e instalar con opciones por defecto. Anotar la contraseña del usuario `postgres`.

**Alternativa con Docker**:
```bash
docker run --name aithera-postgres \
  -e POSTGRES_DB=aithera \
  -e POSTGRES_USER=aithera_user \
  -e POSTGRES_PASSWORD=aithera_local_2026 \
  -p 5432:5432 \
  -d postgres:16-alpine
```

### Paso 2 — Crear base de datos y usuario

Conectar a PostgreSQL como superusuario y ejecutar:
```sql
CREATE DATABASE aithera;
CREATE USER aithera_user WITH PASSWORD 'aithera_local_2026';
GRANT ALL PRIVILEGES ON DATABASE aithera TO aithera_user;
```

### Paso 3 — Instalar dependencias Python

```bash
cd backend
pip install psycopg2-binary==2.9.9 alembic==1.13.1 --break-system-packages
```

Añadir a `backend/requirements.txt`:
```
psycopg2-binary==2.9.9
alembic==1.13.1
```

### Paso 4 — Actualizar `backend/.env`

```env
DATABASE_URL=postgresql://aithera_user:aithera_local_2026@localhost:5432/aithera
MINIMAX_API_KEY=sk-cp--sUhQnGSRs1E87N0fYHhcSBLf2HBNbCc8okAp_QabniiF4H9PqIL2oqJkvAcQR9iudLkGueIu7XutfL7347tEpiLPevl31YO6w4nJgpC3R11JatwQwKL9OU
MINIMAX_MODEL=MiniMax-M2.7-highspeed
```

### Paso 5 — Actualizar `backend/app/core/config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.environ.get('APPDATA', '.'), 'Aithera', 'aithera.db')}"
)
VERSION = "0.4.0"
```

### Paso 6 — Actualizar el engine en `backend/app/db/database.py`

Cambiar SOLO la línea del engine (todo lo demás permanece igual):

```python
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    **({"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {})
)
```

### Paso 7 — Crear el script de migración de datos

Crear `backend/scripts/migrate_sqlite_to_postgres.py`:

```python
"""
Script de migración SQLite → PostgreSQL. Ejecutar UNA SOLA VEZ.

Uso:
    cd backend
    python scripts/migrate_sqlite_to_postgres.py
"""
import os, sys, sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()

SQLITE_PATH = Path(os.environ.get('APPDATA', '.')) / 'Aithera' / 'aithera.db'
POSTGRES_URL = os.getenv("DATABASE_URL", "")

TABLES_IN_ORDER = [
    'config', 'ai_provider_configs', 'projects', 'tasks',
    'calendar_events', 'agents', 'conversations', 'chat_messages',
]

def migrate():
    if not SQLITE_PATH.exists():
        print(f"❌ SQLite no encontrado en: {SQLITE_PATH}"); sys.exit(1)
    if not POSTGRES_URL.startswith("postgresql"):
        print("❌ DATABASE_URL no apunta a PostgreSQL"); sys.exit(1)

    print(f"📦 Fuente: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
    sqlite_conn.row_factory = sqlite3.Row

    pg_engine = create_engine(POSTGRES_URL)

    # Crear tablas en PostgreSQL
    from app.db.database import Base
    Base.metadata.create_all(bind=pg_engine)
    print("✅ Tablas creadas en PostgreSQL")

    pg_conn = pg_engine.connect()
    total = 0

    for table_name in TABLES_IN_ORDER:
        try:
            cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            if not rows:
                print(f"   {table_name}: vacía"); continue

            columns = [d[0] for d in cursor.description]
            placeholders = ", ".join([f":{c}" for c in columns])
            col_list = ", ".join(columns)
            sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

            count = 0
            for row in rows:
                pg_conn.execute(text(sql), dict(zip(columns, row)))
                count += 1
            pg_conn.commit()
            total += count
            print(f"   ✅ {table_name}: {count} registros")
        except Exception as e:
            print(f"   ⚠️  {table_name}: {e}")
            pg_conn.rollback()

    sqlite_conn.close(); pg_conn.close()
    print(f"\n🎉 {total} registros migrados. SQLite conservado como backup.")

if __name__ == "__main__":
    migrate()
```

### ✅ Checkpoint Sesión 1 — verificar antes de parar

- [ ] PostgreSQL está corriendo (verificar con `psql -U aithera_user -d aithera`)
- [ ] `pip install psycopg2-binary alembic` completado sin errores
- [ ] `backend/.env` tiene `DATABASE_URL` apuntando a PostgreSQL
- [ ] `config.py` lee `DATABASE_URL` desde el entorno
- [ ] `database.py` usa el engine dinámico
- [ ] El script de migración existe en `backend/scripts/migrate_sqlite_to_postgres.py`

### 🛑 Para aquí

NO arrancar el backend todavía. NO ejecutar el script todavía. Eso es la Sesión 2.
Commit: `chore: preparar migración a PostgreSQL — engine dinámico + script`.

---

## SESIÓN 2: Ejecutar la migración y activar Alembic

**Tiempo estimado**: 1 hora
**Empieza con**: PostgreSQL corriendo, script de migración listo

### Paso 1 — Ejecutar la migración de datos

```bash
cd backend
python scripts/migrate_sqlite_to_postgres.py
```

Verificar que la salida muestra registros migrados sin errores `❌`.

### Paso 2 — Arrancar el backend y verificar

```bash
python -m uvicorn app.main:app --reload --port 8000
```

La app debe arrancar sin errores. Si hay errores de conexión a PostgreSQL, revisar que el servicio PostgreSQL está corriendo y las credenciales en `.env` son correctas.

### Paso 3 — Inicializar Alembic

```bash
cd backend
alembic init alembic
```

Actualizar `backend/alembic/env.py`:

```python
import os
from dotenv import load_dotenv
from app.db.database import Base

load_dotenv()

# Usar DATABASE_URL del entorno
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", ""))
target_metadata = Base.metadata
```

### Paso 4 — Crear la migración inicial (snapshot del estado actual)

```bash
alembic revision --autogenerate -m "initial_schema_snapshot_from_sqlite_migration"
alembic upgrade head
```

Esto marca la base de datos PostgreSQL como sincronizada con el esquema actual. Las migraciones futuras usarán `alembic revision --autogenerate`.

### Paso 5 — Bump de versión

- `backend/app/main.py`: `version="0.4.0"`
- `backend/app/core/config.py`: `VERSION = "0.4.0"`
- `frontend/package.json`: `"version": "0.4.0"`

### Paso 6 — Actualizar `CLAUDE.md`

- Sección 4: actualizar a V0.4.0
- Sección 5: cambiar `SQLite` por `PostgreSQL`
- Sección 8: añadir `psycopg2-binary==2.9.9`, `alembic==1.13.1`
- Sección 13: actualizar pipeline de desarrollo con comando PostgreSQL
- Sección 17: eliminar restricción #3 (SQLite)
- Sección 18: actualizar riesgo de migraciones (ahora con Alembic)

### ✅ Checkpoint Sesión 2 — verificar antes de parar

- [ ] `GET /api/projects/` devuelve los mismos proyectos que había en SQLite
- [ ] `GET /api/tasks/` devuelve las mismas tareas
- [ ] `GET /api/ai/status` devuelve el proveedor activo (config migrada)
- [ ] El chat funciona correctamente
- [ ] `alembic current` muestra que la BD está al día
- [ ] `GET /` devuelve `"version": "0.4.0"`
- [ ] El archivo SQLite original sigue existiendo como backup en `%APPDATA%/Aithera/`
- [ ] El frontend no nota ningún cambio

### 🛑 Para aquí

Aithera V0.4.0 funcionando sobre PostgreSQL. Commit: `feat: V0.4.0 — migración a PostgreSQL + Alembic`.

**Siguiente fase**: `Fase_2_AgentManager_ExecutionEngine_V05.md`

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Sesión 1**: `backend/app/core/config.py`, `backend/app/db/database.py`, `backend/.env`, `backend/requirements.txt`, `backend/scripts/migrate_sqlite_to_postgres.py`

**Sesión 2**: `backend/alembic.ini`, `backend/alembic/` (directorio completo), `backend/app/main.py`, `frontend/package.json`, `CLAUDE.md`

**No modificados**: todos los modelos SQLAlchemy, todos los schemas Pydantic, todos los endpoints, todo el frontend
