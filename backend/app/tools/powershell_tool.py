# backend/app/tools/powershell_tool.py
#
# V0.5 (Fase 2): ejecucion SEGURA de scripts PowerShell. NUNCA permite
# strings de PowerShell arbitrarios: solo deja ejecutar archivos .ps1
# que ya existan en %USERPROFILE%/AitheraScripts/.
#
# Esto evita el escenario clasico donde un LLM genera
# `Remove-Item -Recurse C:\*` o `Invoke-WebRequest ... | iex` y se ejecuta.
#
# Acciones:
#   run_script   (ejecuta un .ps1 predefinido por nombre, requiere confirmacion)
#   list_scripts (lista los scripts disponibles, NO requiere confirmacion)

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseTool


# Carpeta donde el usuario debe poner los scripts que Aithera puede ejecutar.
# Existe dentro de HOME y es la unica zona desde la que se permite ejecutar
# scripts PowerShell. Si no existe, la tool funciona pero list_scripts
# devolvera [].
SCRIPTS_DIR = Path.home() / "AitheraScripts"


def _safe_script_name(name: str) -> str:
    """Normaliza el nombre del script para evitar path traversal.
    Devuelve solo el nombre base sin directorios, sin '..', sin caracteres
    raros. Si el nombre es inseguro, devuelve string vacio (y el caller
    rechazara la operacion)."""
    if not name:
        return ""
    # Nos quedamos solo con el nombre de archivo.
    base = os.path.basename(name)
    if base != name:
        # El usuario intento pasar una ruta con directorios -> sospechoso.
        return ""
    if not base.lower().endswith(".ps1"):
        return ""
    if ".." in base or any(ch in base for ch in " /\\"):
        return ""
    return base


class PowerShellTool(BaseTool):
    tool_id = "powershell"
    name = "PowerShell Tool"
    description = (
        "Ejecuta scripts .ps1 predefinidos por el usuario desde "
        "%USERPROFILE%/AitheraScripts/. NUNCA permite ejecutar strings "
        "PowerShell arbitrarios. SIEMPRE pide confirmacion."
    )
    requires_confirmation = True  # SIEMPRE

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if action == "run_script":
                return await self._run_script(params)
            elif action == "list_scripts":
                return await self._list_scripts()
            else:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: run_script, list_scripts",
                }
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "run_script",
                "description": (
                    f"Ejecuta un script .ps1 desde {SCRIPTS_DIR}. Solo nombre, "
                    "no path. Siempre pide confirmacion."
                ),
                "requires_confirmation": True,
                "params": {
                    "script_name": "string (ej. 'deploy.ps1')",
                    "args": "lista opcional de strings pasados al script",
                    "timeout": "int segundos (max 120)",
                },
            },
            {
                "id": "list_scripts",
                "description": f"Lista los .ps1 disponibles en {SCRIPTS_DIR}.",
                "requires_confirmation": False,
                "params": {},
            },
        ]

    async def _list_scripts(self) -> Dict[str, Any]:
        if not SCRIPTS_DIR.exists():
            return {
                "success": True,
                "result": {"scripts_dir": str(SCRIPTS_DIR), "scripts": [], "count": 0},
                "error": None,
            }

        def _do_list():
            return sorted([p.name for p in SCRIPTS_DIR.glob("*.ps1") if p.is_file()])

        scripts = await asyncio.to_thread(_do_list)
        return {
            "success": True,
            "result": {"scripts_dir": str(SCRIPTS_DIR), "scripts": scripts, "count": len(scripts)},
            "error": None,
        }

    async def _run_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        script_name = params.get("script_name", "")
        safe = _safe_script_name(script_name)
        if not safe:
            return {
                "success": False,
                "result": None,
                "error": (
                    "script_name invalido. Debe ser un nombre simple "
                    f"terminado en .ps1 (sin rutas, sin '..'). Recibido: {script_name!r}"
                ),
            }

        script_path = (SCRIPTS_DIR / safe).resolve()
        # Verificamos que SIGUE estando dentro de SCRIPTS_DIR (anti symlink trickery).
        try:
            script_path.relative_to(SCRIPTS_DIR.resolve())
        except ValueError:
            return {
                "success": False,
                "result": None,
                "error": f"script fuera de {SCRIPTS_DIR}: {script_path}",
            }

        if not script_path.exists():
            return {
                "success": False,
                "result": None,
                "error": f"script no existe: {script_path}",
            }

        script_args = params.get("args", [])
        if not isinstance(script_args, list):
            return {
                "success": False,
                "result": None,
                "error": "args debe ser una lista de strings",
            }
        # Sanear cada argumento: no puede contener caracteres de control.
        for arg in script_args:
            if not isinstance(arg, str):
                return {
                    "success": False,
                    "result": None,
                    "error": "cada arg debe ser un string",
                }
            if any(ord(ch) < 0x20 for ch in arg):
                return {
                    "success": False,
                    "result": None,
                    "error": f"arg contiene caracteres de control: {arg!r}",
                }

        timeout = params.get("timeout", 60)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            return {"success": False, "result": None, "error": "timeout invalido"}
        timeout = max(1, min(timeout, 120))

        # Comando: powershell -NoProfile -ExecutionPolicy Bypass -File <script> <args...>
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(script_path),
            *script_args,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "success": False,
                "result": None,
                "error": f"timeout: script no termino en {timeout}s y fue abortado",
            }

        stdout_text = (stdout or b"").decode("utf-8", errors="replace")
        stderr_text = (stderr or b"").decode("utf-8", errors="replace")
        MAX_OUT = 8000
        if len(stdout_text) > MAX_OUT:
            stdout_text = stdout_text[:MAX_OUT] + f"\n... [truncado, {len(stdout_text)} chars]"
        if len(stderr_text) > MAX_OUT:
            stderr_text = stderr_text[:MAX_OUT] + f"\n... [truncado, {len(stderr_text)} chars]"

        return {
            "success": proc.returncode == 0,
            "result": {
                "script": safe,
                "args": script_args,
                "returncode": proc.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
            },
            "error": None if proc.returncode == 0 else f"exit code {proc.returncode}",
        }