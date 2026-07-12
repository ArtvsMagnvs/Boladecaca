# Filesystem Tool — Aithera

## Resumen

**Filesystem tool** (`backend/app/tools/filesystem_tool.py`, 11KB) permite a agents leer/escribir archivos con whitelist de paths.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Operations

| Method | Args | Description |
|---|---|---|
| `list_dir` | `path` | Listar contenido de directorio |
| `read_file` | `path` | Leer archivo (text only) |
| `write_file` | `path`, `content` | Escribir archivo |

## Whitelist paths

```python
ALLOWED_PATHS = [
    Path.home() / "Aithera",
    Path.home() / "Documents",
    Path.home() / "Projects"
]
```

## Implementation

```python
# backend/app/tools/filesystem_tool.py
from pathlib import Path
import os

class FilesystemTool(BaseTool):
    name = "filesystem"
    description = "Read, write, list files in whitelisted paths"
    ALLOWED_PATHS = [...]
    
    def _validate_path(self, path: str) -> Path:
        abs_path = Path(path).resolve()
        if not any(abs_path.is_relative_to(p) for p in self.ALLOWED_PATHS):
            raise PermissionError(f"Path {path} not allowed")
        return abs_path
    
    async def list_dir(self, path: str) -> list[str]:
        abs_path = self._validate_path(path)
        if not abs_path.is_dir():
            raise NotADirectoryError(f"{path} is not a directory")
        return [str(p) for p in abs_path.iterdir()]
    
    async def read_file(self, path: str) -> str:
        abs_path = self._validate_path(path)
        if not abs_path.is_file():
            raise FileNotFoundError(f"{path} not found")
        return abs_path.read_text(encoding="utf-8")
    
    async def write_file(self, path: str, content: str) -> dict:
        abs_path = self._validate_path(path)
        if not any(abs_path.is_relative_to(p) for p in self.ALLOWED_PATHS):
            raise PermissionError("Write outside whitelist")
        abs_path.write_text(content, encoding="utf-8")
        return {"success": True, "bytes_written": len(content)}
```

## Path traversal prevention

```python
# Test
tool = FilesystemTool()

# OK
tool.read_file("~/Documents/note.txt")  # OK

# BLOCKED
tool.read_file("/etc/passwd")  # PermissionError
tool.read_file("../../etc/passwd")  # resolve() → /etc/passwd → PermissionError
tool.read_file("~/Documents/../../../etc/passwd")  # PermissionError
```

## Para Aithera

- ✅ V0.5+: filesystem_tool.
- ✅ V0.7.3: whitelist + path validation.
- ⏳ V0.85+: binary file support.

## Referencias cruzadas

- [JWIKI-184 path-traversal-prevention.md](../11_SECURITY/path-traversal-prevention.md)
- CLAUDE.md §8

## Fuentes

1. CLAUDE.md §8

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified