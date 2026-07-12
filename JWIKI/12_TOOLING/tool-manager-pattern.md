# Tool Manager Pattern — Aithera

## Resumen

**ToolManager** es el registro centralizado de tools (`backend/app/tools/tool_manager.py`, 11KB). Permite ejecutar tools con whitelist + validación.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Implementation

```python
# backend/app/tools/tool_manager.py
from app.tools.base import BaseTool

class ToolManager:
    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a tool instance."""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> BaseTool:
        if name not in self.tools:
            raise KeyError(f"Tool {name} not registered")
        return self.tools[name]
    
    async def execute(self, tool_name: str, args: dict, agent: Agent) -> dict:
        """Execute tool with full validation pipeline."""
        # 1. Whitelist check
        if tool_name not in agent.allowed_tools:
            raise PermissionError(f"Tool {tool_name} not in agent whitelist")
        
        tool = self.get_tool(tool_name)
        
        # 2. Schema validation
        try:
            validated_args = tool.validate_args(args)
        except ValidationError as e:
            raise ValueError(f"Invalid args for {tool_name}: {e}")
        
        # 3. Execute with timeout
        try:
            result = await asyncio.wait_for(
                tool.execute(validated_args),
                timeout=agent.max_execution_time
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool {tool_name} exceeded {agent.max_execution_time}s")
        
        # 4. Audit
        return {
            "success": True,
            "output": result,
            "duration_ms": elapsed
        }
    
    def list_tools(self) -> list[dict]:
        """List all registered tools (for LLM tool selection)."""
        return [
            {"name": t.name, "description": t.description, "schema": t.schema}
            for t in self.tools.values()
        ]
```

## Bootstrap

```python
# backend/app/main.py lifespan
from app.tools.filesystem_tool import FilesystemTool
from app.tools.shell_tool import ShellTool
from app.tools.git_tool import GitTool
from app.tools.powershell_tool import PowerShellTool
from app.tools.email_tool import EmailTool
from app.tools.calendar_tool import CalendarTool

tool_manager = ToolManager()
tool_manager.register(FilesystemTool())
tool_manager.register(ShellTool())
tool_manager.register(GitTool())
tool_manager.register(PowerShellTool())
tool_manager.register(EmailTool())
tool_manager.register(CalendarTool())
```

## Tool schema (Pydantic)

```python
from pydantic import BaseModel, Field

class EmailSendArgs(BaseModel):
    to: str = Field(..., regex=r"^[\w.-]+@[\w.-]+\.\w+$")
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=100000)

class EmailTool(BaseTool):
    name = "email.send"
    description = "Send an email via Gmail"
    schema = EmailSendArgs.schema()
    
    def validate_args(self, args):
        return EmailSendArgs(**args).dict()
    
    async def execute(self, args):
        # Send via Gmail API
        ...
```

## Para Aithera

- ✅ V0.5+: ToolManager.
- ✅ V0.7.3: Pydantic validation.
- ⏳ V0.85+: MCP client (tools externos).
- ⏳ V1.0+: visual tool editor.

## Referencias cruzadas

- [JWIKI-192 execution-engine-pattern.md](./execution-engine-pattern.md)
- CLAUDE.md §8

## Fuentes

1. CLAUDE.md §8

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified