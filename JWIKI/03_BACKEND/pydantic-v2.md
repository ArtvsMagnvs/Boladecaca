# Pydantic v2 — Schemas en Aithera

## Resumen

**Pydantic v2** es la librería de validación usada en Aithera V0.7.3. **from_attributes=True** es crítico para SQLAlchemy compat. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Pydantic v2 (CLAUDE.md §2). **NO usar `orm_mode` (v1)**.

## Schema básico

```python
from pydantic import BaseModel, ConfigDict, Field

class ChatRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # SQLAlchemy compat
    
    messages: list[Message]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=128000)
    stream: bool = False

class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str = Field(min_length=1, max_length=200000)

class ChatResponse(BaseModel):
    content: str
    model_used: str
    tokens_used: int | None = None
```

## Pydantic v1 vs v2

| Feature | v1 | v2 |
|---|---|---|
| ORM mode | `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| Validators | `@validator("field")` | `@field_validator("field")` |
| Performance | Base | ⭐⭐⭐⭐⭐ (Rust core) |
| Discriminated unions | ✅ | ✅ (mejor) |

## Pydantic v2 en Aithera V0.7.3

**Patrón obligatorio**:
```python
class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    created_at: datetime
    tasks: list["TaskResponse"] = []
```

**Nunca**:
```python
class ProjectResponse(BaseModel):  # ❌ NO orm_mode
    class Config:
        orm_mode = True  # ❌ v1 syntax
```

## Validators custom

```python
from pydantic import field_validator

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    
    @field_validator("to")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()
    
    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v):
        if len(v) > 200:
            raise ValueError("Subject too long")
        return v
```

## Nested models

```python
class ConversationWithMessages(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str | None
    created_at: datetime
    messages: list[Message] = []
```

## Discriminated unions

```python
from typing import Literal
from pydantic import BaseModel, Field

class UserEvent(BaseModel):
    type: Literal["user_message"]
    message: str

class SystemEvent(BaseModel):
    type: Literal["system"]
    code: int

Event = UserEvent | SystemEvent
```

## Para Aithera

- ✅ Usar `model_config = ConfigDict(from_attributes=True)` SIEMPRE.
- ✅ Validators para inputs de API.
- ✅ Pydantic genera OpenAPI schema automáticamente.

## Pitfalls

- ❌ **`orm_mode = True`** (v1) — usar `from_attributes = True` (v2).
- ❌ **`@validator`** (v1) — usar `@field_validator` (v2).
- ❌ **`dict()`** (v1) — usar `model_dump()` (v2).
- ❌ **`.parse_obj()`** (v1) — usar `model_validate()` (v2).

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-072 api-design-rest.md](./api-design-rest.md)

## Fuentes

1. https://docs.pydantic.dev/latest/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified