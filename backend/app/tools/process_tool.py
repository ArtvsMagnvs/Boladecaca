# backend/app/tools/process_tool.py
#
# V1.0/1.1 (Tools): gestion de procesos del sistema via psutil. Mismo
# criterio de seguridad que ShellTool/PowerShellTool: nada arbitrario.
#
# Acciones:
#   list_processes  (lectura, NO requiere confirmacion)
#   cpu_status      (lectura, NO requiere confirmacion)
#   ram_status      (lectura, NO requiere confirmacion)
#   open_program    (whitelist de programas conocidos, REQUIERE confirmacion)
#   close_program   (por pid, con lista de procesos protegidos, REQUIERE confirmacion)
#
# Seguridad:
# - open_program SOLO acepta nombres de una whitelist fija (igual que
#   ShellTool con binarios) -- nunca una ruta arbitraria a un .exe.
# - close_program bloquea SIEMPRE los procesos core de Windows y el propio
#   proceso del backend de Aithera (evita que la IA se corte a si misma o
#   tumbe el sistema).

import asyncio
import os
from typing import Dict, Any, List

from .base import BaseTool

try:
    import psutil
except ImportError:  # pragma: no cover - degradacion si falta la dependencia
    psutil = None


# Whitelist de programas que se pueden abrir por nombre logico. Cada entrada
# es el comando real que lanza Windows (mismo patron que ALLOWED_COMMANDS de
# ShellTool). Ampliable, pero SIEMPRE explicito -- nunca un path libre.
ALLOWED_PROGRAMS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "task_manager": "taskmgr.exe",
    "control_panel": "control.exe",
}

# Procesos que NUNCA se pueden cerrar: nucleo de Windows + shell + el propio
# backend de Aithera. Comparacion case-insensitive por nombre de imagen.
PROTECTED_PROCESS_NAMES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
    "explorer.exe", "dwm.exe", "fontdrvhost.exe",
}


class ProcessTool(BaseTool):
    tool_id = "process"
    name = "Process Tool"
    description = (
        "Lista procesos y consulta CPU/RAM. Abre programas de una whitelist fija "
        "y cierra procesos por pid (protegiendo el nucleo de Windows y el propio "
        "backend). Abrir/cerrar SIEMPRE requiere confirmacion."
    )
    requires_confirmation = False  # depende de la accion

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if psutil is None:
            return {
                "success": False, "result": None,
                "error": "psutil no esta instalado en el backend (pip install psutil)",
            }
        try:
            handler = {
                "list_processes": self._list_processes,
                "cpu_status": self._cpu_status,
                "ram_status": self._ram_status,
                "open_program": self._open_program,
                "close_program": self._close_program,
            }.get(action)
            if not handler:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: list_processes, cpu_status, ram_status, open_program, close_program",
                }
            return await handler(params)
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "list_processes",
                "description": "Lista los procesos en ejecucion (pid, nombre, %cpu, memoria).",
                "requires_confirmation": False,
                "params": {"limit": "int opcional (default 50), ordenado por %cpu desc"},
            },
            {
                "id": "cpu_status",
                "description": "Uso de CPU actual (global y por nucleo).",
                "requires_confirmation": False,
                "params": {},
            },
            {
                "id": "ram_status",
                "description": "Uso de memoria RAM actual (total/usada/disponible).",
                "requires_confirmation": False,
                "params": {},
            },
            {
                "id": "open_program",
                "description": f"Abre un programa de la whitelist: {', '.join(sorted(ALLOWED_PROGRAMS))}.",
                "requires_confirmation": True,
                "params": {"name": f"string, uno de: {', '.join(sorted(ALLOWED_PROGRAMS))}"},
            },
            {
                "id": "close_program",
                "description": "Cierra un proceso por pid. Rechaza procesos protegidos del sistema.",
                "requires_confirmation": True,
                "params": {"pid": "int"},
            },
        ]

    # ------------------------------------------------------------------

    async def _list_processes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(params.get("limit", 50))
        limit = max(1, min(limit, 200))

        def _do():
            procs = []
            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    cpu = p.cpu_percent(interval=None)
                    mem = p.info.get("memory_info")
                    procs.append({
                        "pid": p.info["pid"],
                        "name": p.info["name"],
                        "cpu_percent": cpu,
                        "memory_mb": round(mem.rss / (1024 * 1024), 1) if mem else None,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x["cpu_percent"] or 0, reverse=True)
            return procs[:limit]

        procs = await asyncio.to_thread(_do)
        return {"success": True, "result": {"processes": procs, "count": len(procs)}, "error": None}

    async def _cpu_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        def _do():
            return {
                "percent_total": psutil.cpu_percent(interval=0.3),
                "percent_per_core": psutil.cpu_percent(interval=None, percpu=True),
                "core_count": psutil.cpu_count(logical=True),
            }
        status = await asyncio.to_thread(_do)
        return {"success": True, "result": status, "error": None}

    async def _ram_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        def _do():
            vm = psutil.virtual_memory()
            return {
                "total_mb": round(vm.total / (1024 * 1024)),
                "used_mb": round(vm.used / (1024 * 1024)),
                "available_mb": round(vm.available / (1024 * 1024)),
                "percent_used": vm.percent,
            }
        status = await asyncio.to_thread(_do)
        return {"success": True, "result": status, "error": None}

    async def _open_program(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = (params.get("name") or "").strip().lower()
        cmd = ALLOWED_PROGRAMS.get(name)
        if not cmd:
            allowed = ", ".join(sorted(ALLOWED_PROGRAMS))
            return {
                "success": False, "result": None,
                "error": f"programa '{name}' no esta en la whitelist. Permitidos: {allowed}",
            }
        try:
            proc = await asyncio.create_subprocess_exec(cmd)
            return {"success": True, "result": {"name": name, "command": cmd, "pid": proc.pid}, "error": None}
        except Exception as e:
            return {"success": False, "result": None, "error": f"no se pudo abrir '{cmd}': {e}"}

    async def _close_program(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pid = params.get("pid")
        if pid is None:
            return {"success": False, "result": None, "error": "falta parametro: pid"}
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            return {"success": False, "result": None, "error": "pid invalido"}

        if pid == os.getpid():
            return {"success": False, "result": None, "error": "no se puede cerrar el propio proceso del backend"}

        def _do():
            proc = psutil.Process(pid)
            proc_name = proc.name()
            if proc_name.lower() in PROTECTED_PROCESS_NAMES:
                raise PermissionError(f"'{proc_name}' es un proceso protegido del sistema")
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            return proc_name

        try:
            proc_name = await asyncio.to_thread(_do)
        except psutil.NoSuchProcess:
            return {"success": False, "result": None, "error": f"no existe el proceso pid={pid}"}
        except PermissionError as e:
            return {"success": False, "result": None, "error": str(e)}
        except psutil.AccessDenied:
            return {"success": False, "result": None, "error": f"permiso denegado para cerrar pid={pid}"}

        return {"success": True, "result": {"pid": pid, "name": proc_name, "closed": True}, "error": None}
