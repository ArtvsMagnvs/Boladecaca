# backend/app/tools/base.py
#
# V0.4 (Fase 2 AgentManager + ToolSystem) + V0.5 (Fase 2 ExecutionEngine):
# Interfaz abstracta BaseTool que TODAS las herramientas deben implementar.
#
# V0.5 extiende esta interfaz con:
#   - tool_id / name / description / requires_confirmation como atributos
#     de clase (antes del V0.5 eran @abstractmethod)
#   - list_actions() devuelve ademas los parametros esperados por accion
#     para que el frontend pueda mostrar el formulario dinamico.
#
# V0.4 establecio el contrato basico: execute(action, params) -> {success, result, error}.
# V0.5 lo mantiene y lo blind anado con la whitelist del ToolManager y el timeout duro.

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseTool(ABC):
    """Interfaz que deben implementar todas las herramientas de Aithera."""

    # Atributos de clase que cada subclase debe definir.
    tool_id: str = ""          # "filesystem", "git", "shell", "powershell"
    name: str = ""             # "Filesystem Tool"
    description: str = ""      # descripcion legible para humanos
    requires_confirmation: bool = False  # pedir confirmacion antes de ejecutar

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta una accion de la herramienta.

        Args:
            action: una de las acciones listadas en list_actions()
            params: parametros validados por el ToolManager

        Returns:
            Dict uniforme: {"success": bool, "result": Any, "error": Optional[str]}
        """
        raise NotImplementedError

    @abstractmethod
    def list_actions(self) -> List[Dict[str, Any]]:
        """Lista de acciones disponibles con su descripcion.

        Returns:
            Lista de dicts: [{"id": "read_file", "description": "...", "params": {...}}, ...]
        """
        raise NotImplementedError

    def validate_params(self, action: str, params: Dict[str, Any]) -> bool:
        """Validacion adicional especifica de la herramienta. Override si necesario.

        El ToolManager ya hace una primera validacion comun (paths sin '..',
        comandos fuera de whitelist, etc.). Aqui cada herramienta puede
        anadir sus reglas.

        Returns:
            True si OK, False si algun parametro es invalido.
        """
        return True