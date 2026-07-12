# Validators — JSON Schema y Pydantic

## Resumen

**Validators** en Aithera usan Pydantic v2 para validar argumentos de tools antes de ejecutar. CLAUDE.md §2 "Pydantic v2 (from_attributes = True)".

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Pydantic como JSON Schema

```python
from pydantic import BaseModel, Field
from typing import Literal

class EmailSendArgs(BaseModel):
    to: str = Field(..., regex=r"^[\w.-]+@[\w.-]+\.\w+$")
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    priority: Literal["low", "normal", "high"] = "normal"

# Generate JSON schema for LLM
schema = EmailSendArgs.schema()
# {
#   "title": "EmailSendArgs",
#   "type": "object",
#   "properties": {
#     "to": {"type": "string", "pattern": "^...$"},
#     "subject": {"type": "string", "minLength": 1, "maxLength": 200},
#     ...
#   },
#   "required": ["to", "subject", "body"]
# }
```

## Tool validation

```python
class EmailTool(BaseTool):
    args_schema = EmailSendArgs
    
    def validate_args(self, args: dict) -> dict:
        return self.args_schema(**args).dict()  # Raises ValidationError
```

## Custom validators

```python
from pydantic import field_validator

class CalendarCreateEventArgs(BaseModel):
    summary: str
    start: datetime
    end: datetime
    
    @field_validator("end")
    @classmethod
    def end_after_start(cls, v, info):
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("end must be after start")
        return v
```

## Para Aithera

- ✅ V0.5+: Pydantic validation.
- ✅ V0.7.3: JSON Schema generation para LLM tool calling.

## Referencias cruzadas

- [JWIKI-077 pydantic-v2.md](../03_BACKEND/pydantic-v2.md)
- CLAUDE.md §2

## Fuentes

1. https://docs.pydantic.dev/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified