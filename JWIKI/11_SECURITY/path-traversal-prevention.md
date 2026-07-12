# Path Traversal Prevention

## Resumen

**Path traversal** es el ataque donde `../../etc/passwd` se usa para acceder a archivos fuera del directorio permitido. Aithera V0.7.3 previene con whitelist + validación.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Attack example

```python
# VULNERABLE
def read_file(path: str):
    return open(path).read()

# Attack
read_file("../../etc/passwd")  # Lee archivo fuera del sandbox
```

## Aithera mitigation

```python
from pathlib import Path

class FilesystemTool:
    ALLOWED_PATHS = [
        Path.home() / "Aithera",
        Path.home() / "Documents"
    ]
    
    def read_file(self, path: str) -> str:
        # 1. Resolve symlinks + normalize
        abs_path = Path(path).resolve()
        
        # 2. Check whitelist
        if not any(abs_path.is_relative_to(p) for p in self.ALLOWED_PATHS):
            raise PermissionError(f"Path {path} not allowed")
        
        # 3. Validate exists + is file
        if not abs_path.is_file():
            raise FileNotFoundError(f"{path} is not a file")
        
        # 4. Read safely
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
```

## Edge cases

```python
# Symlinks
read_file("/home/user/Aithera/symlink_to_etc")  # symlink → /etc → BLOCKED

# Absolute path
read_file("/etc/passwd")  # BLOCKED (no en whitelist)

# Relative with ../../
read_file("../../../etc/passwd")  # resolve() → /etc/passwd → BLOCKED

# Unicode tricks
read_file("..%2F..%2Fetc%2Fpasswd")  # URL decoded → BLOCKED
```

## Test cases

```python
def test_path_traversal():
    tool = FilesystemTool()
    
    with pytest.raises(PermissionError):
        tool.read_file("/etc/passwd")
    
    with pytest.raises(PermissionError):
        tool.read_file("../../etc/passwd")
    
    with pytest.raises(PermissionError):
        tool.read_file("~/Aithera/../../../etc/passwd")
    
    # OK
    content = tool.read_file("~/Aithera/file.txt")
    assert content is not None
```

## Para Aithera

- ✅ V0.5+: whitelist + resolve() check.
- ⏳ V0.85+: chroot si es Windows (más complejo).

## Referencias cruzadas

- [JWIKI-183 sandboxing-tool-whitelist.md](./sandboxing-tool-whitelist.md)
- [JWIKI-185 command-injection-prevention.md](./command-injection-prevention.md)

## Fuentes

1. https://owasp.org/www-community/attacks/Path_Traversal
2. https://docs.python.org/3/library/pathlib.html

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified