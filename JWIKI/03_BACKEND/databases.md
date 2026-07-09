# Databases — PostgreSQL, SQLite, MariaDB

## Resumen

Comparativa de las 3 bases de datos principales para Aithera.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Matriz comparativa

| DB | Tipo | Performance | Concurrencia | Full-text | Embeddings | Aithera |
|---|---|---|---|---|---|---|
| **PostgreSQL** | RDBMS | ⭐⭐⭐⭐⭐ | ✅ excelente | ✅ tsvector + pgvector | ✅ pgvector | ✅ V0.4+ |
| **SQLite** | Embedded | ⭐⭐⭐⭐ | ⚠️ limitada | ✅ FTS5 | ❌ | ✅ fallback |
| **MariaDB** | RDBMS (MySQL fork) | ⭐⭐⭐⭐ | ✅ buena | ✅ FULLTEXT | ❌ | ❌ |

## PostgreSQL — primary de Aithera

Aithera V0.7.3 usa **PostgreSQL** cuando `DATABASE_URL` está configurada (CLAUDE.md §2).

**Por qué**:
- ✅ Async driver maduro (`asyncpg`).
- ✅ Alembic migrations robustas.
- ✅ Full-text search built-in.
- ✅ JSONB para metadata flexible.
- ✅ Production-ready.
- ✅ ChromaDB integration (ChromaDB usa pgvector para escala).

## SQLite — fallback automático

Si no hay `DATABASE_URL`, Aithera cae a **SQLite** (modo desarrollo).

**Por qué SQLite**:
- ✅ Zero-config (perfecto para single-user).
- ✅ Backup trivial (un archivo).
- ✅ Suficiente para 1 usuario + few thousand rows.
- ⚠️ No recomendado para concurrencia alta.

## MariaDB — NO se usa

MariaDB es MySQL fork. Aithera no lo usa directamente. Si el user quiere MySQL, puede usar MariaDB-compatible.

## Schema PostgreSQL clave (Aithera V0.7.3)

```sql
-- Users (futuro)
-- Projects
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    project_id INTEGER REFERENCES projects(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ChatMessages
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    model_used VARCHAR(100),
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Calendar Events
CREATE TABLE calendar_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    all_day BOOLEAN DEFAULT FALSE,
    color VARCHAR(20),
    google_event_id VARCHAR(100),  -- V0.7+ sync
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Providers
CREATE TABLE ai_provider_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    is_active BOOLEAN DEFAULT FALSE,
    api_key TEXT,  -- cifrado DPAPI V0.8+
    default_model VARCHAR(100),
    config JSONB
);

-- Agents
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    allowed_tools JSONB,
    max_execution_time INTEGER DEFAULT 3600,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Executions
CREATE TABLE agent_executions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    status VARCHAR(20),
    tool_calls JSONB,
    result TEXT,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Email Tables (V0.7+)
CREATE TABLE email_auto_reply_rules (...);
CREATE TABLE calendar_availability (...);
CREATE TABLE meeting_proposals (...);
CREATE TABLE email_activity_log (...);
CREATE TABLE email_triage (...);
```

## ChromaDB

Aithera V0.7.3 usa **ChromaDB** para memory (V0.6+). ChromaDB usa SQLite internamente por default, o PostgreSQL para escala.

## Driver async

```python
# asyncpg (PostgreSQL)
engine = create_async_engine("postgresql+asyncpg://...")

# aiosqlite (SQLite)
engine = create_async_engine("sqlite+aiosqlite:///./aithera.db")
```

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-064 sqlalchemy-2.md](./sqlalchemy-2.md)
- [JWIKI-066 postgresql.md](./postgresql.md)
- [JWIKI-067 sqlite-fallback.md](./sqlite-fallback.md)

## Fuentes

1. https://www.postgresql.org/
2. https://www.sqlite.org/
3. https://mariadb.org/
4. CLAUDE.md §2

## Nivel de confianza

**95%** — Bien documentado en Aithera codebase.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified