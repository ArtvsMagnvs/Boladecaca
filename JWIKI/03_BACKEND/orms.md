# ORMs — SQLAlchemy 2.0, Prisma, Drizzle

## Resumen

Comparativa de ORMs: **SQLAlchemy 2.0** (Python, usado en Aithera), **Prisma** (Node/TS), **Drizzle** (TS moderno), **Django ORM**, **SQLModel**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

| ORM | Lenguaje | Async | Type-safety | Madurez | Aithera |
|---|---|---|---|---|---|
| **SQLAlchemy 2.0** | Python | ✅ async | ✅ Mapped types | ⭐⭐⭐⭐⭐ | ✅ |
| Prisma | Node/TS | ✅ | ✅⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ |
| Drizzle | TS | ✅ | ✅⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |
| Django ORM | Python | ✅ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |
| SQLModel | Python | ✅ | ✅⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |
| Tortoise | Python | ✅ | ⭐⭐⭐ | ⭐⭐⭐ | ❌ |

## SQLAlchemy 2.0 — el elegido para Aithera

**Por qué SQLAlchemy**:
- ✅ Async nativo (`AsyncSession`).
- ✅ Type hints con `Mapped[T]`.
- ✅ Migration tool maduro (Alembic).
- ✅ 18 años de madurez.
- ✅ Performance top-tier.
- ✅ Compatible con múltiples DBs (PostgreSQL, SQLite, MySQL).

## SQLAlchemy 2.0 — ejemplo

```python
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String, unique=True)
    
    tasks: Mapped[list["Task"]] = relationship(back_populates="user")

class Task(Base):
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    user: Mapped["User"] = relationship(back_populates="tasks")
```

## SQLAlchemy vs SQLModel

**SQLModel** es un wrapper sobre SQLAlchemy + Pydantic creado por el mismo autor de FastAPI. Más conciso pero menos maduro.

```python
# SQLModel
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(unique=True)
```

**Aithera eligió SQLAlchemy puro** (más control, más maduro).

## Alembic migrations

```bash
# Crear nueva migration
alembic revision --autogenerate -m "add new column"

# Aplicar
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Prisma (Node/TS) — alternativa moderna

```typescript
// schema.prisma
model User {
  id    Int    @id @default(autoincrement())
  name  String
  email String @unique
  tasks Task[]
}

model Task {
  id     Int  @id @default(autoincrement())
  title  String
  user   User @relation(fields: [userId], references: [id])
  userId Int
}
```

Prisma es **más conciso** que SQLAlchemy pero Aithera no usa Node/TS en backend.

## Drizzle (TS moderno) — type-safe máximo

```typescript
import { pgTable, serial, text, varchar } from "drizzle-orm/pg-core";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 100 }).notNull(),
  email: text("email").notNull().unique(),
});
```

Drizzle es **más type-safe** que Prisma pero menos maduro.

## Para Aithera V0.85+

Considerar **SQLModel** si se quiere más concisión. Pero SQLAlchemy 2.0 ya es lo suficientemente bueno.

## Pitfalls SQLAlchemy

- ❌ **`orm_mode`** (Pydantic v1) — usar `from_attributes=True` (v2).
- ❌ **Lazy loading en async** — usar `selectinload()` o `joinedload()` explícito.
- ❌ **N+1 queries** — eager loading.

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-064 sqlalchemy-2.md](./sqlalchemy-2.md)
- [JWIKI-068 migrations.md](./migrations.md)

## Fuentes

1. https://docs.sqlalchemy.org/en/20/
2. https://alembic.sqlalchemy.org/
3. https://www.prisma.io/
4. https://orm.drizzle.team/

## Nivel de confianza

**95%** — SQLAlchemy bien establecido.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified