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

    # [2026-07-19] Tool INTERNA: capacidad propia de Aithera sobre si misma, no
    # una herramienta externa que se "concede" a un agente.
    #
    # LA DISTINCION (correccion de diseño de R3): `filesystem`, `email` o `shell`
    # son puertas al mundo de fuera — tiene sentido decidir a que agente se le
    # abren. Crear un proyecto o dar de alta una regla NO es eso: es el
    # Orquestador operando su propia casa, algo que puede hacer por definicion.
    # Ponerlo como casilla junto a las demas implicaba justo lo contrario: que un
    # agente al que el Orquestador le encarga eso no pudiera hacerlo por no tener
    # marcada la casilla.
    #
    # Una tool interna: NO aparece en el catalogo publico (`/api/tools/`, la UI
    # de agentes), NO se puede asignar a mano, y NO esta sujeta a la whitelist
    # del agente. Lo que si sigue aplicando es (a) la confirmacion del usuario en
    # sus acciones de escritura y (b) la frontera de autoridad por proyecto (R4).
    internal: bool = False

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