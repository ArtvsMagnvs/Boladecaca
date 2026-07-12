# Tooling — Overview

## Resumen

Aithera V0.5+ tiene **8 tools** registrados en ToolManager (`backend/app/tools/`). Ver CLAUDE.md §8. Cada tool tiene schema validation + whitelist.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Tools Aithera V0.7.3

| Tool | Archivo | Capacidades |
|---|---|---|
| **filesystem** | filesystem_tool.py | list_dir, read_file, write_file |
| **shell** | shell_tool.py | python, git, npm, uvicorn whitelist |
| **git** | git_tool.py | status, log, diff, commit |
| **powershell** | powershell_tool.py | scripts PS aprobados |
| **email** | email_tool.py (44KB) | Gmail REST + auto-reply + meeting |
| **calendar** | calendar_tool.py (29KB) | Google Calendar + availability |
| **voice** | voice/ | TTS/STT |
| **memory** | memory/ | ChromaDB search |

## Architecture

```python
# backend/app/tools/base.py
class BaseTool:
    name: str
    description: str
    schema: dict  # JSON schema for args
    
    def validate_args(self, args: dict) -> dict:
        # Validate args against schema
        ...
    
    async def execute(self, args: dict) -> dict:
        # Tool-specific logic
        ...
```

```python
# backend/app/tools/tool_manager.py
class ToolManager:
    def __init__(self):
        self.tools = {}
    
    def register(self, tool: BaseTool):
        self.tools[tool.name] = tool
    
    async def execute(self, tool_name: str, args: dict, agent: Agent, timeout: int = None) -> dict:
        # 1. Whitelist (agent.allowed_tools)
        # 2. Schema validation
        # 3. Execute with timeout
        # 4. Audit log
        ...
```

## Tool calling flow

```
LLM response: {tool_call: {name: "email.send", args: {...}}}
  ↓
AgentManager.execute()
  ↓
ToolManager.execute("email.send", args)
  ↓
EmailTool.execute(args)
  ↓
Result → message back to LLM
```

## Para Aithera

- ✅ V0.5+: 8 tools básicos.
- ✅ V0.7.3: email + calendar completos.
- ⏳ V0.85+: MCP client (tools externos).
- ⏳ V1.0+: skill-based tool registry.

## Referencias cruzadas

- [JWIKI-192 execution-engine-pattern.md](./execution-engine-pattern.md)
- [JWIKI-193 tool-manager-pattern.md](./tool-manager-pattern.md)
- CLAUDE.md §8 (ToolManager)

## Fuentes

1. CLAUDE.md §8

## Nivel de confianza

**100%** — implementado en CLAUDE.md §8.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified