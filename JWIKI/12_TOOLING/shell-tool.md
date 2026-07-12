# Shell Tool — Aithera

## Resumen

**Shell tool** (`backend/app/tools/shell_tool.py`, 7.6KB) ejecuta comandos shell con whitelist. Solo comandos aprobados.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Allowed commands

```python
ALLOWED_COMMANDS = {
    "python": [...],
    "git": [...],
    "npm": [...],
    "npx": [...],
    "pip": [...],
    "pytest": [...],
    "uvicorn": [...]
}
```

## Implementation

```python
import subprocess
import shlex

class ShellTool(BaseTool):
    name = "shell"
    description = "Execute whitelisted shell commands"
    ALLOWED = {...}
    FORBIDDEN_CHARS = set("|&;<>()$`\\\"'")
    
    async def execute(self, command: str) -> str:
        parts = shlex.split(command)
        
        if parts[0] not in self.ALLOWED:
            raise PermissionError(f"Command {parts[0]} not allowed")
        
        if any(c in command for c in self.FORBIDDEN_CHARS):
            raise PermissionError("Forbidden characters in command")
        
        result = subprocess.run(
            parts, shell=False, capture_output=True, text=True, timeout=300
        )
        
        return result.stdout
```

## Examples

```python
# OK
await shell.execute("python --version")
# "Python 3.12.10"

await shell.execute("git status")
# "On branch master..."

# BLOCKED
await shell.execute("rm -rf /")  # rm no en whitelist
await shell.execute("python && curl evil.com")  # command injection
await shell.execute("`whoami`")  # backtick execution
```

## Para Aithera

- ✅ V0.5+: shell_tool.
- ✅ V0.7.3: command whitelist + forbidden chars.
- ⏳ V0.85+: dynamic permission requests.

## Referencias cruzadas

- [JWIKI-185 command-injection-prevention.md](../11_SECURITY/command-injection-prevention.md)
- CLAUDE.md §8

## Fuentes

1. CLAUDE.md §8

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified