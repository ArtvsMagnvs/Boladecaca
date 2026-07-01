# backend/app/tools/tool_manager.py
#
# V0.4 (Fase 2 AgentManager + ToolSystem) + V0.5 (Fase 2 ExecutionEngine):
# Registro centralizado de herramientas con whitelist por agente, log de
# auditoria y timeout duro.
#
# V0.4 establecio el contrato basico: registro + ejecucion simple.
# V0.5 lo blindo con:
#   - whitelist por agente (allowed_tools del modelo Agent).
#   - validacion comun de parametros (path traversal, zonas prohibidas).
#   - timeout duro con asyncio.wait_for.
#   - log en memoria (ultimas 100 ejecuciones, expuesto en /api/tools/execution-log).
#
# Principios:
# - La IA sugiere. El ToolManager valida. Aithera ejecuta.
# - NUNCA se delega la decision a la IA sin pasar por este manager.
# - Cada tool es responsable de su propia logica, pero el manager impone
#   las garantias comunes (whitelist, timeout, log).

import asyncio
import time
from collections import deque
from typing import Dict, Any, List, Optional, Deque

from .base import BaseTool


class ToolManager:
    """Registro singleton de herramientas + ejecucion con whitelist + log."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        # Deque de las ultimas 100 ejecuciones (FIFO). Se expone en /api/tools/execution-log.
        self._log: Deque[Dict[str, Any]] = deque(maxlen=100)

    # ------------------------------------------------------------------
    # Registro (V0.4 API)
    # ------------------------------------------------------------------

    def _register_default_tools(self):
        """Registra las herramientas incluidas por defecto (V0.4 + V0.5 + V0.7).

        V0.4 incluia 3: filesystem, shell, git.
        V0.5 anadio PowerShellTool para ejecutar scripts .ps1 predefinidos.
        V0.7 anadio EmailTool (Gmail) y CalendarTool (Google Calendar).
        """
        from .filesystem_tool import FilesystemTool
        from .shell_tool import ShellTool
        from .git_tool import GitTool
        from .powershell_tool import PowerShellTool
        from .email_tool import EmailTool
        from .calendar_tool import CalendarTool

        self.register(FilesystemTool())
        self.register(ShellTool())
        self.register(GitTool())
        self.register(PowerShellTool())
        self.register(EmailTool())
        self.register(CalendarTool())

    def register(self, tool: BaseTool) -> None:
        """Registra una herramienta. Permite anadir herramientas custom en el futuro."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"se esperaba BaseTool, recibio {type(tool).__name__}")
        if not tool.tool_id:
            raise ValueError("tool.tool_id no puede estar vacio")
        if tool.tool_id in self._tools:
            # Permitimos re-registro (util para tests); avisamos.
            print(f"[ToolManager] Reemplazando herramienta: {tool.tool_id}")
        self._tools[tool.tool_id] = tool

    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        return self._tools.get(tool_id)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Devuelve el catalogo de herramientas registradas con sus acciones.
        Esto es lo que consume el frontend en /api/tools/."""
        out = []
        for tool_id, tool in self._tools.items():
            out.append({
                "tool_id": tool_id,
                "name": tool.name,
                "description": tool.description,
                "requires_confirmation": tool.requires_confirmation,
                "actions": tool.list_actions(),
            })
        # Orden alfabetico para que la UI sea estable.
        out.sort(key=lambda t: t["tool_id"])
        return out

    # ------------------------------------------------------------------
    # Ejecucion (V0.4 API simple + V0.5 blindaje)
    # ------------------------------------------------------------------

    async def execute(
        self,
        tool_id: str,
        action: str,
        params: Dict[str, Any],
        allowed_tools: Optional[List[str]] = None,
        timeout: int = 30,
        agent_id: Optional[int] = None,
        execution_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Ejecuta una herramienta con todas las validaciones (V0.4 + V0.5).

        Args:
            tool_id: id de la herramienta (debe estar registrada)
            action: accion a ejecutar (debe estar en tool.list_actions())
            params: parametros validados
            allowed_tools: whitelist de tool_id que el agente puede usar. Si None,
                se permite cualquier herramienta registrada (util para tests).
            timeout: segundos maximos de espera
            agent_id / execution_id: para el log (trazabilidad)

        Returns:
            Dict uniforme {success, result, error}
        """
        t0 = time.monotonic()

        # 1) Validacion de existencia.
        tool = self._tools.get(tool_id)
        if not tool:
            return self._log_and_return({
                "success": False,
                "result": None,
                "error": f"herramienta no registrada: {tool_id}",
                "tool_id": tool_id,
                "action": action,
            }, t0, agent_id, execution_id, "rejected")

        # 2) Validacion de whitelist por agente.
        if allowed_tools is not None and tool_id not in allowed_tools:
            return self._log_and_return({
                "success": False,
                "result": None,
                "error": (
                    f"el agente no tiene permiso para usar '{tool_id}'. "
                    f"Permitidos: {allowed_tools}"
                ),
                "tool_id": tool_id,
                "action": action,
            }, t0, agent_id, execution_id, "rejected_whitelist")

        # 3) Validacion comun de parametros (defensa en profundidad).
        common_check = _common_param_check(params)
        if common_check is not None:
            return self._log_and_return({
                "success": False,
                "result": None,
                "error": common_check,
                "tool_id": tool_id,
                "action": action,
            }, t0, agent_id, execution_id, "rejected_params")

        # 4) Validacion especifica de la tool.
        try:
            if not tool.validate_params(action, params):
                return self._log_and_return({
                    "success": False,
                    "result": None,
                    "error": f"parametros invalidos para {tool_id}/{action}",
                    "tool_id": tool_id,
                    "action": action,
                }, t0, agent_id, execution_id, "rejected_params")
        except Exception as e:
            return self._log_and_return({
                "success": False,
                "result": None,
                "error": f"validate_params de {tool_id} lanzo {type(e).__name__}: {e}",
                "tool_id": tool_id,
                "action": action,
            }, t0, agent_id, execution_id, "error")

        # 5) Ejecucion con timeout duro (no se puede colgar el backend).
        try:
            result = await asyncio.wait_for(
                tool.execute(action, params),
                timeout=max(1, min(timeout, 300)),
            )
        except asyncio.TimeoutError:
            return self._log_and_return({
                "success": False,
                "result": None,
                "error": f"timeout del manager: {tool_id}/{action} supero {timeout}s",
                "tool_id": tool_id,
                "action": action,
            }, t0, agent_id, execution_id, "timeout")
        except Exception as e:
            return self._log_and_return({
                "success": False,
                "result": None,
                "error": f"excepcion en {tool_id}/{action}: {type(e).__name__}: {e}",
                "tool_id": tool_id,
                "action": action,
            }, t0, agent_id, execution_id, "error")

        # Aseguramos la forma del resultado aunque la tool sea descuidada.
        if not isinstance(result, dict):
            result = {"success": bool(result), "result": result, "error": None}
        if "success" not in result:
            result["success"] = True
        if "result" not in result:
            result["result"] = None
        if "error" not in result:
            result["error"] = None
        # Anadimos tool_id/action al resultado para que el log de auditoria
        # siempre pueda saber QUE herramienta y accion se ejecuto, incluso en OK.
        result["tool_id"] = tool_id
        result["action"] = action

        return self._log_and_return(result, t0, agent_id, execution_id, "ok" if result["success"] else "error")

    # ------------------------------------------------------------------
    # Log (V0.5)
    # ------------------------------------------------------------------

    def get_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Devuelve las ultimas ejecuciones del manager (orden cronologico inverso)."""
        log_list = list(self._log)
        log_list.reverse()
        if limit:
            log_list = log_list[:limit]
        return log_list

    def _log_and_return(
        self,
        result: Dict[str, Any],
        t0: float,
        agent_id: Optional[int],
        execution_id: Optional[int],
        outcome: str,
    ) -> Dict[str, Any]:
        entry = {
            "ts": time.time(),
            "duration_ms": int((time.monotonic() - t0) * 1000),
            "agent_id": agent_id,
            "execution_id": execution_id,
            "tool_id": result.get("tool_id"),
            "action": result.get("action"),
            "outcome": outcome,
            "success": result.get("success", False),
            "error": result.get("error"),
        }
        self._log.append(entry)
        return result


def _common_param_check(params: Dict[str, Any]) -> Optional[str]:
    """Validaciones de seguridad comunes a TODAS las tools.

    Devuelve None si OK, o un string con la razon del rechazo.
    Se ejecuta en el manager ANTES de delegar a la tool concreta, como
    segunda linea de defensa por si una tool nueva se olvida de validar
    algo.
    """
    if not isinstance(params, dict):
        return "params debe ser un objeto JSON"

    def _walk_strings(value, path: str = ""):
        if isinstance(value, str):
            yield path, value
        elif isinstance(value, list):
            for i, v in enumerate(value):
                yield from _walk_strings(v, f"{path}[{i}]")
        elif isinstance(value, dict):
            for k, v in value.items():
                yield from _walk_strings(v, f"{path}.{k}" if path else k)

    for path, s in _walk_strings(params):
        # Bloqueo absoluto de path traversal: si CUALQUIER string contiene
        # '..' como componente, lo rechazamos. Esto protege aunque la tool
        # olvide validar (defensa en profundidad).
        if "/.." in s or s.startswith("..") or "\\..\\" in s or s.endswith("\\.."):
            return f"path traversal detectado en {path}: {s[:80]!r}"
        # Bloqueo de paths absolutos a zonas sensibles del sistema.
        s_lower = s.lower().replace("/", "\\")
        for blocked in ("c:\\windows", "c:\\program files", "c:\\programdata",
                         "/etc/", "/sys/", "/proc/", "/dev/"):
            if s_lower.startswith(blocked):
                return f"path a zona restringida en {path}: {s[:80]!r}"
    return None


# Singleton global (V0.4 + V0.5).
tool_manager = ToolManager()
# Auto-registro de las tools por defecto al importar este modulo.
# Lo hacemos aqui (no en __init__.py) para que el singleton este
# disponible antes que las tools.
tool_manager._register_default_tools()