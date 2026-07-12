# SOP — Crear tool ToolManager

## Cuándo
Necesitas un tool nuevo (e.g., `twitter.post`).

## Pasos

1. **Crear tool class** en `backend/app/tools/`:
```python
from app.tools.base import BaseTool
from pydantic import BaseModel

class TwitterPostArgs(BaseModel):
    text: str

class TwitterTool(BaseTool):
    name = "twitter.post"
    description = "Post a tweet"
    args_schema = TwitterPostArgs
    
    async def execute(self, args: TwitterPostArgs) -> dict:
        # Implementación
        ...
```

2. **Registrar en `tool_manager.py`** (lifespan):
```python
tool_manager.register(TwitterTool())
```

3. **Añadir al whitelist del Agent** (si aplica):
```python
agent.allowed_tools.append("twitter.post")
```

## Verificación

- [ ] Tool aparece en `GET /api/tools/`.
- [ ] Agent puede ejecutar el tool.
- [ ] Logs audit quedan en `agent_executions`.

## Rollback

- Remove registration.
- (No necesita DB rollback).

## Referencias cruzadas

- [JWIKI-193 tool-manager-pattern.md](../12_TOOLING/tool-manager-pattern.md)

---

*Estado: 🟢 verified*