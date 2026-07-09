# Migrations — Alembic

## Resumen

**Alembic** es la herramienta de migrations para SQLAlchemy. Aithera V0.7.3 usa Alembic 1.13+ (CLAUDE.md §2).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```bash
# Inicializar (una vez)
cd backend
alembic init alembic

# Configurar alembic.ini + alembic/env.py
# (Aithera ya lo tiene hecho)
```

## Comandos básicos

```bash
# Ver migración actual
alembic current

# Ver historial
alembic history

# Crear nueva migración (autogenerate)
alembic revision --autogenerate -m "add new column"

# Aplicar migraciones
alembic upgrade head

# Rollback
alembic downgrade -1

# Ir a versión específica
alembic upgrade <revision_id>
```

## Aithera migrations (V0.7.3)

Alembic migrations de Aithera (8+ migraciones aplicadas):

```
1. `4ab2071f433f_initial_schema_snapshot_from_sqlite_migration.py` — V0.4
2. `24b8353ad754_add_agent_fields_and_execution_table.py` — V0.5
3. `25c926be5811_force_cascade_delete_on_agent_execut...py` — V0.5 fix
4. `f94e0572d70d_v07_email_calendar_auto_reply_and_.py` — V0.7
5. `33074ebc50b0_v07_add_google_event_id_to_calendar_.py` — V0.7
6. `0840fe70d5ce_v07_meeting_proposals.py` — V0.7
7. `48b15869c4e3_v07_extra_redesign_auto_reply_rules.py` — V0.7
8. `bff7a3fd8d7d_v07_extra_email_activity_log_and_.py` — V0.7
9. `a1f2e3d4c5b6_v073_email_triage.py` — V0.7.3
10. `b2c3d4e5f6a7_v073_rule_autonomy.py` — V0.7.3
11. `c3d4e5f6a7b8_v073b_rule_ai_prompt.py` — V0.7.3
12. `d4e5f6a7b8c9_v08_encrypt_api_keys.py` — V0.8 (DPAPI)
```

## Migración autogenerate

```bash
alembic revision --autogenerate -m "add user_preferences table"
```

Alembic compara el schema actual de SQLAlchemy con el schema en la DB y genera la migration.

## Migración manual

```python
# alembic/versions/xxxx_add_user_preferences.py
def upgrade():
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.JSON, nullable=True),
    )

def downgrade():
    op.drop_table("user_preferences")
```

## Para V0.4+ SQLite → PostgreSQL migration

```bash
# 1. Dump SQLite
sqlite3 aithera.db .dump > sqlite_dump.sql

# 2. Use Aithera's migrate script
python backend/scripts/migrate_sqlite_to_postgres.py
```

## Pitfalls

- ❌ **Modificar migration ya aplicada** — NUNCA. Crear nueva migration.
- ❌ **No usar `--autogenerate` ciegamente** — revisar el diff antes de aplicar.
- ❌ **Olvidar `downgrade()`** — sin rollback possible.

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-064 sqlalchemy-2.md](./sqlalchemy-2.md)
- [JWIKI-069 alembic.md](./alembic.md)

## Fuentes

1. https://alembic.sqlalchemy.org/
2. CLAUDE.md §2

## Nivel de confianza

**95%** — Alembic bien establecido.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified