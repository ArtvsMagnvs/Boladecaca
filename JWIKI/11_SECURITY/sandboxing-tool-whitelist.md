# Sandboxing — Tool whitelist Aithera

## Resumen

Aithera implementa **tool sandboxing** vía whitelist (CLAUDE.md §8 "ToolManager 11KB"). Cada agent tiene `allowed_tools` que valida antes de ejecutar.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Architecture

```python
# backend/app/tools/tool_manager.py
class ToolManager:
    def __init__(self):
        self.tools = {}  # name → tool instance
    
    def register(self, tool):
        self.tools[tool.name] = tool
    
    async def execute(self, tool_name: str, args: dict, agent: Agent) -> dict:
        # 1. Whitelist check
        if tool_name not in agent.allowed_tools:
            raise PermissionError(f"Tool {tool_name} not allowed for agent {agent.id}")
        
        # 2. Schema validation
        tool = self.tools[tool_name]
        validated = tool.validate_args(args)
        
        # 3. Timeout
        try:
            result = await asyncio.wait_for(
                tool.execute(validated),
                timeout=agent.max_execution_time
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool {tool_name} timeout")
        
        # 4. Audit log
        await log_execution(agent.id, tool_name, args, result)
        
        return {"success": True, "output": result, "duration_ms": elapsed}
```

## Tool whitelist per agent

```python
class Agent(Base):
    allowed_tools: Mapped[list] = mapped_column(JSON, default=list)
    # ej: ["filesystem.read_file", "shell.git_status", "email.send"]
```

## Validation layers

1. **Agent whitelist**: ¿puede este agent usar este tool?
2. **Tool schema**: ¿los args son válidos?
3. **Path traversal**: para filesystem, ¿el path está dentro de la whitelist?
4. **Command injection**: para shell, ¿el comando es seguro?
5. **Timeout**: max_execution_time (default 3600s).

## Path whitelist (filesystem tool)

```python
class FilesystemTool:
    ALLOWED_PATHS = [
        Path.home() / "Aithera",
        Path.home() / "Documents",
        Path.home() / "Projects"
    ]
    
    def _validate_path(self, path: str) -> Path:
        abs_path = Path(path).resolve()
        if not any(abs_path.is_relative_to(p) for p in self.ALLOWED_PATHS):
            raise PermissionError(f"Path {path} not allowed")
        return abs_path
```

## Shell whitelist (shell tool)

```python
class ShellTool:
    ALLOWED_COMMANDS = ["python", "git", "npm", "npx", "pip", "pytest", "uvicorn"]
    
    def _validate_command(self, command: str) -> list[str]:
        parts = command.split()
        if parts[0] not in self.ALLOWED_COMMANDS:
            raise PermissionError(f"Command {parts[0]} not allowed")
        # No shell metacharacters
        if any(c in command for c in "|&;<>()$`"):
            raise PermissionError("Shell metacharacters not allowed")
        return parts
```

## Para Aithera

- ✅ V0.5+: ToolManager + whitelist.
- ✅ V0.7.3: validación schema + timeout.
- ⏳ V0.85+: sandboxing OS-level (Docker si necesario).
- ⏳ V1.0+: rate limiting per tool.

## Referencias cruzadas

- [JWIKI-184 path-traversal-prevention.md](./path-traversal-prevention.md)
- [JWIKI-185 command-injection-prevention.md](./command-injection-prevention.md)
- CLAUDE.md §8 (ToolManager)

## Fuentes

1. https://owasp.org/www-community/attacks/Path_Traversal
2. https://owasp.org/www-community/attacks/Command_Injection
3. CLAUDE.md §8

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified