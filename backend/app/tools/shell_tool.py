# backend/app/tools/shell_tool.py
#
# V0.4 (Fase 2 AgentManager + ToolSystem) + V0.5 (Fase 2):
# Shell con WHITELIST ESTRICTA de binarios permitidos.
#
# Seguridad:
# - Solo permite los binarios listados en ALLOWED_COMMANDS (python, pip,
#   git, npm, node, uvicorn, npx).
# - Cada binario tiene un max_timeout configurable (en segundos).
# - requires_confirmation SIEMPRE True: el usuario debe aceptar la
#   ejecucion antes de que se lance.
# - Nunca permite concatenacion (& | ;), redirecciones (>>, >, <), ni
#   comandos del sistema operativo (cmd, bash, sh, powershell, etc).
# - No permite rutas absolutas a ejecutables (solo el nombre del binario).

import os
import asyncio
import shlex
from typing import Dict, Any, List

from .base import BaseTool


# Whitelist explicita de binarios permitidos. Cada uno lleva su max_timeout
# en segundos. NO anadir binarios potentes (rm, curl, wget, etc.) sin un
# control muy estricto.
ALLOWED_COMMANDS = {
    "python": {"max_timeout": 60, "description": "Python interpreter"},
    "python3": {"max_timeout": 60, "description": "Python 3 (alias de python)"},
    "pip": {"max_timeout": 120, "description": "Pip package manager"},
    "git": {"max_timeout": 30, "description": "Git VCS"},
    "npm": {"max_timeout": 120, "description": "Node package manager"},
    "node": {"max_timeout": 60, "description": "Node.js runtime"},
    "npx": {"max_timeout": 120, "description": "Node package runner"},
    "uvicorn": {"max_timeout": 10, "description": "Uvicorn ASGI server"},
}


# Caracteres prohibidos: cualquier intento de encadenar comandos, redireccionar
# salida o expandir variables/bashisms es bloqueado.
FORBIDDEN_CHARS = set("&|;<>`$(){}[]\n\r\t")


class ShellTool(BaseTool):
    tool_id = "shell"
    name = "Shell Tool"
    description = (
        "Ejecuta comandos de una whitelist estricta (python, pip, git, npm, "
        "node, npx, uvicorn). Cualquier otro binario o intento de "
        "concatenacion de comandos es rechazado. SIEMPRE pide confirmacion."
    )
    requires_confirmation = True  # SIEMPRE - comando de sistema

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if action != "run":
                return {
                    "success": False,
                    "result": None,
                    "error": f"Accion desconocida: {action}. Solo se soporta 'run'.",
                }

            command_str = params.get("command", "")
            cwd = params.get("cwd", None)
            timeout_override = params.get("timeout", None)

            if not command_str or not isinstance(command_str, str):
                return {"success": False, "result": None, "error": "falta parametro: command"}

            # 1) Tokenizar con shlex para separar argumentos (sin ejecutar).
            try:
                tokens = shlex.split(command_str)
            except ValueError as e:
                return {"success": False, "result": None, "error": f"comando mal formado: {e}"}
            if not tokens:
                return {"success": False, "result": None, "error": "comando vacio"}

            # 2) Validar binario: debe estar en ALLOWED_COMMANDS.
            binary = tokens[0]
            normalized = binary.lower().replace(".exe", "")
            cmd_info = ALLOWED_COMMANDS.get(normalized)
            if not cmd_info:
                allowed = ", ".join(sorted(ALLOWED_COMMANDS.keys()))
                return {
                    "success": False,
                    "result": None,
                    "error": (
                        f"Binario '{binary}' no esta en la whitelist. "
                        f"Permitidos: {allowed}"
                    ),
                }

            # 3) Buscar caracteres prohibidos en cualquier argumento.
            for tok in tokens:
                if any(ch in FORBIDDEN_CHARS for ch in tok):
                    return {
                        "success": False,
                        "result": None,
                        "error": f"caracteres prohibidos en argumento: {tok!r}",
                    }

            # 4) Validar timeout.
            timeout = timeout_override or cmd_info["max_timeout"]
            try:
                timeout = float(timeout)
            except (TypeError, ValueError):
                return {"success": False, "result": None, "error": "timeout invalido"}
            if timeout <= 0 or timeout > cmd_info["max_timeout"] * 2:
                return {
                    "success": False,
                    "result": None,
                    "error": f"timeout fuera de rango (max permitido para {normalized}: {cmd_info['max_timeout'] * 2}s)",
                }

            # 5) Validar cwd (si se da): debe estar dentro de HOME.
            if cwd:
                cwd_path = os.path.abspath(os.path.expandvars(os.path.expanduser(cwd)))
                home = os.path.abspath(os.path.expanduser("~"))
                if not cwd_path.startswith(home):
                    return {"success": False, "result": None, "error": f"cwd fuera de HOME: {cwd_path}"}

            # 6) Ejecutar de verdad (sin shell=True para que no se interpreten
            #    metacaracteres).
            proc = await asyncio.create_subprocess_exec(
                *tokens,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd_path if cwd else None,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "success": False,
                    "result": None,
                    "error": f"timeout: comando no termino en {timeout}s y fue abortado",
                }

            stdout_text = (stdout or b"").decode("utf-8", errors="replace")
            stderr_text = (stderr or b"").decode("utf-8", errors="replace")
            MAX_OUT = 8000
            if len(stdout_text) > MAX_OUT:
                stdout_text = stdout_text[:MAX_OUT] + f"\n... [truncado, {len(stdout_text)} chars]"
            if len(stderr_text) > MAX_OUT:
                stderr_text = stderr_text[:MAX_OUT] + f"\n... [truncado, {len(stderr_text)} chars]"

            return {
                "success": (proc.returncode == 0),
                "result": {
                    "command": command_str,
                    "binary": normalized,
                    "returncode": proc.returncode,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                },
                "error": None if proc.returncode == 0 else f"exit code {proc.returncode}",
            }
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        actions = []
        for cmd, info in ALLOWED_COMMANDS.items():
            actions.append({
                "id": "run",
                "binary": cmd,
                "description": f"Ejecuta '{cmd}'. {info['description']} (max {info['max_timeout']}s).",
                "requires_confirmation": True,
                "params": {
                    "command": f"string con '{cmd} <args...>'",
                    "cwd": "string opcional (debe estar dentro de HOME)",
                    "timeout": f"int opcional en segundos (max {info['max_timeout'] * 2})",
                },
            })
        return actions