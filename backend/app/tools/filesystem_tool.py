# backend/app/tools/filesystem_tool.py
#
# V0.4 (Fase 2 AgentManager + ToolSystem) + V0.5 (Fase 2):
# Herramienta de acceso al sistema de archivos LOCAL con whitelist de paths.
#
# Seguridad:
# - Solo opera dentro de %USERPROFILE% (raiz del usuario).
# - Bloquea SIEMPRE paths absolutos a C:\\Windows, C:\\Program Files, etc.
# - Bloquea '..' para impedir path traversal.
# - Limita lectura a 1MB por archivo (protege contra lectura de logs/bds).
#
# Acciones:
#   read_file     (lectura, NO requiere confirmacion)
#   file_exists   (lectura, NO requiere confirmacion)
#   list_dir      (lectura, NO requiere confirmacion)
#   write_file    (escritura, REQUIERE confirmacion)
#   create_dir    (escritura, REQUIERE confirmacion)
#   delete_file   (DESTRUCTIVA, REQUIERE confirmacion)

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseTool


# Paths sensibles en Windows que NUNCA deben tocarse, ni siquiera en lectura.
WINDOWS_BLOCKED_PREFIXES = (
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\Boot",
    "C:\\Recovery",
    "C:\\System Volume Information",
)

# Limite de tamano para operaciones de lectura (protege contra archivos
# enormes tipo base de datos o logs gigantes).
MAX_READ_BYTES = 1024 * 1024  # 1 MB


def _resolve_user_path(path_str: str) -> Path:
    """Convierte un path a Path absoluto, expandiendo ~ y variables de entorno.

    Si el path es relativo, se interpreta como relativo al home del usuario.
    """
    if not path_str:
        raise ValueError("path vacio")
    p = Path(os.path.expandvars(os.path.expanduser(path_str)))
    if not p.is_absolute():
        p = Path.home() / p
    return p.resolve()


def _is_path_allowed(path: Path) -> bool:
    """Verifica que el path este dentro de HOME y no caiga en zonas prohibidas."""
    try:
        path_resolved = path.resolve()
    except Exception:
        return False

    # Bloqueo #1: el path debe estar dentro del home del usuario.
    try:
        path_resolved.relative_to(Path.home().resolve())
    except ValueError:
        return False

    # Bloqueo #2: rutas absolutas a zonas sensibles del sistema.
    path_str = str(path_resolved)
    for blocked in WINDOWS_BLOCKED_PREFIXES:
        if path_str.startswith(blocked):
            return False

    # Bloqueo #3: cualquier componente del path es '..' (ya no deberia
    # llegar aqui tras resolve(), pero por si acaso).
    for part in path.parts:
        if part == "..":
            return False

    return True


class FilesystemTool(BaseTool):
    tool_id = "filesystem"
    name = "Filesystem Tool"
    description = (
        "Lee, escribe y lista archivos y directorios dentro del home del usuario. "
        "Las acciones destructivas (escribir/borrar) requieren confirmacion."
    )
    requires_confirmation = False  # depende de la accion

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            handler = {
                "read_file": self._read_file,
                "file_exists": self._file_exists,
                "list_dir": self._list_dir,
                "write_file": self._write_file,
                "create_dir": self._create_dir,
                "delete_file": self._delete_file,
            }.get(action)

            if not handler:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: read_file, file_exists, list_dir, write_file, create_dir, delete_file",
                }

            return await handler(params)
        except ValueError as e:
            return {"success": False, "result": None, "error": f"path invalido: {e}"}
        except PermissionError as e:
            return {"success": False, "result": None, "error": f"permiso denegado: {e}"}
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "read_file",
                "description": "Lee el contenido de un archivo de texto (max 1MB).",
                "requires_confirmation": False,
                "params": {"path": "string (path absoluto o relativo a HOME)"},
            },
            {
                "id": "file_exists",
                "description": "Comprueba si un archivo o directorio existe.",
                "requires_confirmation": False,
                "params": {"path": "string"},
            },
            {
                "id": "list_dir",
                "description": "Lista los archivos y subdirectorios de un directorio.",
                "requires_confirmation": False,
                "params": {"path": "string"},
            },
            {
                "id": "write_file",
                "description": "Escribe texto en un archivo (lo crea si no existe).",
                "requires_confirmation": True,
                "params": {"path": "string", "content": "string"},
            },
            {
                "id": "create_dir",
                "description": "Crea un directorio (con padres si no existen).",
                "requires_confirmation": True,
                "params": {"path": "string"},
            },
            {
                "id": "delete_file",
                "description": "Borra un archivo. PELIGRO: irreversible.",
                "requires_confirmation": True,
                "params": {"path": "string"},
            },
        ]

    # --- Implementaciones por accion (async aunque sean sync, para
    #     mantener una interfaz homogenea que el manager pueda timeoutear) ---

    async def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path_str = params.get("path")
        if not path_str:
            return {"success": False, "result": None, "error": "falta parametro: path"}
        path = _resolve_user_path(path_str)
        if not _is_path_allowed(path):
            return {"success": False, "result": None, "error": f"path fuera de zonas permitidas: {path}"}

        def _do_read():
            if not path.exists():
                raise FileNotFoundError(f"no existe: {path}")
            if path.is_dir():
                raise IsADirectoryError(f"es un directorio, usa list_dir: {path}")
            size = path.stat().st_size
            if size > MAX_READ_BYTES:
                raise ValueError(f"archivo demasiado grande ({size} bytes, max {MAX_READ_BYTES})")
            return path.read_text(encoding="utf-8")

        content = await asyncio.to_thread(_do_read)
        return {
            "success": True,
            "result": {"path": str(path), "size": path.stat().st_size, "content": content},
            "error": None,
        }

    async def _file_exists(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path_str = params.get("path")
        if not path_str:
            return {"success": False, "result": None, "error": "falta parametro: path"}
        path = _resolve_user_path(path_str)
        # file_exists es SOLO lectura: no exigimos _is_path_allowed tan
        # estricto (puede ser util saber si existe algo fuera), pero NO
        # devolvemos su contenido ni metadatos sensibles.
        return {
            "success": True,
            "result": {"path": str(path), "exists": path.exists(), "is_file": path.is_file() if path.exists() else None},
            "error": None,
        }

    async def _list_dir(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path_str = params.get("path")
        if not path_str:
            return {"success": False, "result": None, "error": "falta parametro: path"}
        path = _resolve_user_path(path_str)
        if not _is_path_allowed(path):
            return {"success": False, "result": None, "error": f"path fuera de zonas permitidas: {path}"}

        def _do_list():
            if not path.exists():
                raise FileNotFoundError(f"no existe: {path}")
            if not path.is_dir():
                raise NotADirectoryError(f"no es un directorio: {path}")
            entries = []
            for entry in path.iterdir():
                try:
                    entries.append({
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "size": entry.stat().st_size if entry.is_file() else None,
                    })
                except (PermissionError, OSError):
                    entries.append({"name": entry.name, "is_dir": None, "size": None, "accessible": False})
            return entries

        entries = await asyncio.to_thread(_do_list)
        return {
            "success": True,
            "result": {"path": str(path), "entries": entries, "count": len(entries)},
            "error": None,
        }

    async def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path_str = params.get("path")
        content = params.get("content", "")
        if not path_str:
            return {"success": False, "result": None, "error": "falta parametro: path"}
        path = _resolve_user_path(path_str)
        if not _is_path_allowed(path):
            return {"success": False, "result": None, "error": f"path fuera de zonas permitidas: {path}"}

        def _do_write():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return path.stat().st_size

        size = await asyncio.to_thread(_do_write)
        return {"success": True, "result": {"path": str(path), "size": size}, "error": None}

    async def _create_dir(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path_str = params.get("path")
        if not path_str:
            return {"success": False, "result": None, "error": "falta parametro: path"}
        path = _resolve_user_path(path_str)
        if not _is_path_allowed(path):
            return {"success": False, "result": None, "error": f"path fuera de zonas permitidas: {path}"}

        def _do_create():
            path.mkdir(parents=True, exist_ok=True)
            return True

        await asyncio.to_thread(_do_create)
        return {"success": True, "result": {"path": str(path), "created": True}, "error": None}

    async def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path_str = params.get("path")
        if not path_str:
            return {"success": False, "result": None, "error": "falta parametro: path"}
        path = _resolve_user_path(path_str)
        if not _is_path_allowed(path):
            return {"success": False, "result": None, "error": f"path fuera de zonas permitidas: {path}"}

        def _do_delete():
            if not path.exists():
                raise FileNotFoundError(f"no existe: {path}")
            if path.is_dir():
                raise IsADirectoryError(
                    f"es un directorio; borra recursivamente a mano si quieres. Path: {path}"
                )
            path.unlink()
            return True

        await asyncio.to_thread(_do_delete)
        return {"success": True, "result": {"path": str(path), "deleted": True}, "error": None}