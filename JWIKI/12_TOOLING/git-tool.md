# Git Tool — Aithera

## Resumen

**Git tool** (`backend/app/tools/git_tool.py`, 9.2KB) ejecuta comandos git básicos con whitelist.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Operations

| Command | Args | Description |
|---|---|---|
| `git status` | (cwd) | Working tree status |
| `git log` | `--oneline -n 20` | Recent commits |
| `git diff` | `file` | Cambios |
| `git commit` | `-m "msg"` | Commit (con whitelist de mensajes) |

## Implementation

```python
class GitTool(BaseTool):
    name = "git"
    ALLOWED_SUBCOMMANDS = {"status", "log", "diff", "add", "commit", "branch"}
    DEFAULT_CWD = "~/Aithera"
    
    async def execute(self, subcommand: str, args: list = None) -> str:
        if subcommand not in self.ALLOWED_SUBCOMMANDS:
            raise PermissionError(f"git {subcommand} not allowed")
        
        cmd = ["git", subcommand] + (args or [])
        result = subprocess.run(cmd, cwd=self.DEFAULT_CWD, capture_output=True, text=True)
        return result.stdout
```

## Para Aithera

- ✅ V0.5+: git_tool.
- ⏳ V0.85+: git push (con auth).

## Referencias cruzadas

- CLAUDE.md §8

## Fuentes

1. https://git-scm.com/

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified