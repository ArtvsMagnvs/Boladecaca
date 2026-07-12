# Pydantic v1 vs v2 — Sintaxis

## Resumen

**Pydantic v2** cambió sintaxis significativamente. Aithera V0.7.3 usa v2 (CLAUDE.md §2). Migración crítica.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Cambios clave

| v1 | v2 |
|---|---|
| `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| `@validator("field")` | `@field_validator("field")` |
| `.dict()` | `.model_dump()` |
| `.parse_obj()` | `.model_validate()` |
| `@validator(..., always=True)` | `@field_validator(..., mode="before")` |
| `BaseSettings` (v1) | `pydantic_settings.BaseSettings` (separado) |

## Ejemplo migración

```python
# v1
from pydantic import BaseModel, validator

class User(BaseModel):
    name: str
    email: str
    
    class Config:
        orm_mode = True
    
    @validator("email")
    def validate_email(cls, v):
        return v.lower()
    
    def dict_for_json(self):
        return self.dict()


# v2
from pydantic import BaseModel, ConfigDict, field_validator

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    email: str
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        return v.lower()
    
    def dict_for_json(self):
        return self.model_dump()
```

## Pitfalls

- ❌ **No mezclar** v1 y v2 sintaxis.
- ❌ **`BaseSettings`** ahora es paquete separado (`pydantic_settings`).
- ❌ **`regex`** parameter deprecated, usar `pattern`.

## Para Aithera

- ✅ V0.7.3: Pydantic v2 (CLAUDE.md §2).

## Referencias cruzadas

- [JWIKI-077 pydantic-v2.md](../03_BACKEND/pydantic-v2.md)
- CLAUDE.md §2

## Fuentes

1. https://docs.pydantic.dev/latest/migration/

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified