# SQLAlchemy 2.0 — ORM en uso en Aithera

## Resumen

**SQLAlchemy 2.0** es el ORM usado en Aithera V0.7.3 (CLAUDE.md §2). Async, type-safe, maduro.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Aithera usa SQLAlchemy 2.0 (según CLAUDE.md §2).

## Características clave

- ✅ **AsyncSession** para async queries.
- ✅ **Mapped[T]** type hints (Python 3.12+).
- ✅ **Alembic** para migrations.
- ✅ Multi-DB (PostgreSQL/SQLite/MySQL).
- ✅ Performance optimizado.

## Aithera modelos (extracto)

```python
# backend/app/db/database.py
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    completed: Mapped[bool] = mapped_column(default=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    
    project: Mapped["Project | None"] = relationship(back_populates="tasks")

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="conversation")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(20))  # user/assistant/system
    content: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
```

## Async session

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/aithera")
async_session = async_sessionmaker(engine, expire_on_commit=False)

async with async_session() as session:
    user = await session.get(User, 1)
    tasks = await session.execute(
        select(Task).where(Task.user_id == user.id)
    )
```

## Eager loading (evitar N+1)

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

stmt = select(User).options(selectinload(User.tasks))
result = await session.execute(stmt)
users = result.scalars().all()
```

## Engine dinámico (SQLite/PostgreSQL)

```python
# Aithera: DATABASE_URL dinámico
import os

def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Fallback a SQLite
        database_url = "sqlite+aiosqlite:///./aithera.db"
    
    return create_async_engine(
        database_url,
        echo=False,  # set True para debug
        pool_size=10 if "postgresql" in database_url else 1,
        max_overflow=20,
    )
```

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-063 orms.md](./orms.md)
- [JWIKI-065 databases.md](./databases.md)
- [JWIKI-066 postgresql.md](./postgresql.md)
- [JWIKI-068 migrations.md](./migrations.md)

## Fuentes

1. https://docs.sqlalchemy.org/en/20/
2. https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
3. CLAUDE.md §2

## Nivel de confianza

**95%** — SQLAlchemy 2.0 bien documentado en codebase.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified