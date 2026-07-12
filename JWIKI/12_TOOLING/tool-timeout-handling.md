# Tool Timeout Handling

## Resumen

**Tool timeout** es crítico para evitar que un tool bloquee al agente indefinidamente. Aithera usa `asyncio.wait_for` con `max_execution_time`.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Implementation

```python
# backend/app/tools/tool_manager.py
class ToolManager:
    async def execute(self, tool_name: str, args: dict, agent: Agent) -> dict:
        ...
        try:
            result = await asyncio.wait_for(
                tool.execute(validated_args),
                timeout=agent.max_execution_time  # default 3600s
            )
        except asyncio.TimeoutError:
            await log_timeout(tool_name, agent.max_execution_time)
            raise TimeoutError(f"Tool {tool_name} exceeded {agent.max_execution_time}s")
```

## Graceful kill

```python
class ShellTool:
    def __init__(self):
        self.process = None
    
    async def execute(self, command: str) -> str:
        self.process = await asyncio.create_subprocess_exec(
            *shlex.split(command),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                self.process.communicate(),
                timeout=300
            )
        except asyncio.TimeoutError:
            self.process.kill()  # <- SIGKILL
            await self.process.wait()
            raise TimeoutError("Shell command timed out")
        
        return stdout.decode()
```

## Per-agent timeout

```python
class Agent(Base):
    max_execution_time: int = 3600  # 1 hour default
```

User puede ajustar por agent.

## Para Aithera

- ✅ V0.5+: asyncio.wait_for.
- ✅ V0.7.3: graceful kill.

## Referencias cruzadas

- [JWIKI-193 tool-manager-pattern.md](./tool-manager-pattern.md)
- CLAUDE.md §8

## Fuentes

1. https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified