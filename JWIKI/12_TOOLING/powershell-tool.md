# PowerShell Tool — Aithera

## Resumen

**PowerShell tool** (`backend/app/tools/powershell_tool.py`, 7.9KB) ejecuta scripts PS aprobados en Windows.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Whitelist de scripts

```python
ALLOWED_SCRIPTS = {
    "backup-aithera.ps1": "scripts/backup-aithera.ps1",
    "restart-backend.ps1": "scripts/restart-backend.ps1",
    "check-updates.ps1": "scripts/check-updates.ps1"
}
```

## Implementation

```python
class PowerShellTool(BaseTool):
    name = "powershell"
    ALLOWED_SCRIPTS = {...}
    
    async def execute(self, script_name: str, args: list = None) -> str:
        if script_name not in self.ALLOWED_SCRIPTS:
            raise PermissionError(f"Script {script_name} not in whitelist")
        
        script_path = self.ALLOWED_SCRIPTS[script_name]
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path] + (args or [])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return result.stdout
```

## Para Aithera

- ✅ V0.5+: PowerShell tool.
- ✅ V0.7.3: script whitelist.

## Referencias cruzadas

- CLAUDE.md §8

## Fuentes

1. https://learn.microsoft.com/en-us/powershell/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified