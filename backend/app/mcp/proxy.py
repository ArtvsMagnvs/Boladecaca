# app/mcp/proxy.py — MCPToolProxy: tools de servidores MCP externos como
# ciudadanos de PRIMERA del ToolManager (V1.2 C1, doc 27 §C1)
#
# EL PRINCIPIO (contrato de producto de la fase): una tool MCP pasa por LAS
# MISMAS puertas que cualquier tool nativa — whitelist del agente, validación
# de parámetros del ToolManager, timeout duro, log de auditoría — MÁS las
# suyas propias, porque un servidor MCP es código externo de facto:
#
#   1. GATE SIEMPRE: `requires_confirmation=True` a nivel de tool Y en CADA
#      acción. Con `_is_sensitive` del toolloop eso significa que ninguna
#      acción MCP se ejecuta sin abrir el ApprovalGate. El permiso `mcp.use`
#      (A3b) puede auto-resolverlo — CON rastro en `approvals`, regla de oro.
#   2. SANDBOX DE ARGUMENTOS: solo se envían al servidor los parámetros que su
#      propio inputSchema declara — un argumento desconocido se RECHAZA, no se
#      reenvía (un servidor malicioso no puede pescar campos extra que el
#      modelo decida inventar), y los tipos primitivos se comprueban.
#   3. RESPUESTA = DATOS, NUNCA ÓRDENES: el texto que devuelve el servidor se
#      sanea (`clean_external`, S9c) antes de entrar al transcript; el
#      envoltorio <datos> lo pone el toolloop (PU8) como con toda observación.
#
# tool_id = "mcp_<servidor>" — el prefijo vive en permissions.py
# (MCP_TOOL_PREFIX) porque es vocabulario de SEGURIDAD: es lo que traduce
# cualquier tool MCP presente o futura al permiso `mcp.use`. Un test de
# contrato vigila que este archivo y aquel usen la MISMA constante.
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.automation import permission_service
from app.core.sanitize import clean_external
from app.tools.base import BaseTool

from . import client as mcp_client
from . import store

logger = logging.getLogger(__name__)

_TYPE_MAP = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}


class MCPToolProxy(BaseTool):
    """Una tool del ToolManager por cada SERVIDOR MCP conectado; las tools del
    servidor son sus acciones. Registrable/asignable a agentes como cualquier
    otra (aparece en el catálogo público y en `allowed_tools`)."""

    requires_confirmation = True     # código externo: gate SIEMPRE (contrato nº 1)
    internal = False                 # pública: el usuario la asigna a agentes

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.tool_id = permission_service.MCP_TOOL_PREFIX + server_name
        cfg = store.get_server(server_name)
        descripcion = (cfg.description if cfg else "") or ""
        self.name = f"MCP · {server_name}"
        self.description = (
            f"Servidor MCP externo '{server_name}'"
            + (f": {descripcion}" if descripcion else "")
            + ". Sus acciones las define el propio servidor."
        )

    # -- catálogo -------------------------------------------------------
    def _discovered(self) -> list[dict]:
        """Tools del servidor: las de la conexión viva si existe; si no, la
        caché del último descubrimiento (para que el catálogo del TIE tenga
        las acciones tras un reinicio sin esperar a reconectar)."""
        conn = mcp_client.get_connection(self.server_name)
        if conn is not None and conn.tools:
            return conn.tools
        return store.cached_tools(self.server_name)

    def list_actions(self) -> List[Dict[str, Any]]:
        acciones = []
        for tool in self._discovered():
            schema = tool.get("input_schema") or {}
            props = schema.get("properties") or {}
            required = set(schema.get("required") or [])
            params = {}
            for pname, pdef in props.items():
                if not isinstance(pdef, dict):
                    pdef = {}
                desc = str(pdef.get("description", "") or pdef.get("type", ""))[:120]
                params[pname] = desc + (" (obligatorio)" if pname in required else "")
            acciones.append({
                "id": tool.get("name", ""),
                "description": (tool.get("description") or "")[:300],
                "params": params,
                # Redundante con el atributo de clase A PROPÓSITO: el gate no
                # puede depender de que nadie olvide el nivel de tool.
                "requires_confirmation": True,
            })
        return acciones

    # -- preflight (Sesión A) — barato, NUNCA lanza procesos ------------
    def preflight(self) -> Optional[str]:
        cfg = store.get_server(self.server_name)
        if cfg is None:
            return f"el servidor MCP '{self.server_name}' ya no está configurado"
        if not cfg.enabled:
            return (f"el servidor MCP '{self.server_name}' está desactivado — "
                    f"actívalo en Ajustes → Conexiones")
        conn = mcp_client.get_connection(self.server_name)
        if conn is not None and not conn.connected and conn.last_error:
            return (f"el servidor MCP '{self.server_name}' falló al conectar: "
                    f"{conn.last_error}")
        return None                      # nunca intentado aún → que lo pruebe la llamada

    # -- sandbox de argumentos ------------------------------------------
    def validate_params(self, action: str, params: Dict[str, Any]) -> bool:
        motivo = self._check_args(action, params)
        if motivo:
            logger.info(f"[mcp] argumentos rechazados para "
                        f"{self.tool_id}.{action}: {motivo}")
            return False
        return True

    def _check_args(self, action: str, params: Dict[str, Any]) -> Optional[str]:
        tools = {t.get("name"): t for t in self._discovered()}
        tool = tools.get(action)
        if tool is None:
            # Acción desconocida: sin schema contra el que validar. Se deja
            # pasar al servidor (que la rechazará él) SOLO si no hay catálogo
            # todavía; con catálogo conocido, acción inexistente = rechazo.
            return f"acción desconocida: {action!r}" if tools else None
        schema = tool.get("input_schema") or {}
        props = schema.get("properties")
        if not isinstance(props, dict):
            return None                  # el servidor no declara schema → sin sandbox posible
        for req in (schema.get("required") or []):
            if req not in params:
                return f"falta el parámetro obligatorio {req!r}"
        # Argumento no declarado → RECHAZO (salvo additionalProperties=true
        # explícito). Es la mitad "no reenviar lo que el servidor no pidió".
        if schema.get("additionalProperties") is not True:
            for k in params:
                if k not in props:
                    return f"parámetro no declarado por el servidor: {k!r}"
        for k, v in params.items():
            pdef = props.get(k)
            if not isinstance(pdef, dict):
                continue
            esperado = _TYPE_MAP.get(pdef.get("type"))
            if esperado is None or v is None:
                continue
            # bool es subclase de int en Python: un True donde va un número
            # se rechaza explícitamente.
            if esperado is int and isinstance(v, bool):
                return f"{k!r} debe ser {pdef.get('type')}, llegó bool"
            if not isinstance(v, esperado):
                return (f"{k!r} debe ser {pdef.get('type')}, "
                        f"llegó {type(v).__name__}")
        return None

    # -- ejecución ------------------------------------------------------
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        cfg = store.get_server(self.server_name)
        if cfg is None or not cfg.enabled:
            return {"success": False, "result": None,
                    "error": f"el servidor MCP '{self.server_name}' no está "
                             f"disponible (borrado o desactivado)"}
        conn = mcp_client.get_connection(self.server_name)
        if conn is None:
            return {"success": False, "result": None,
                    "error": f"el servidor MCP '{self.server_name}' no está configurado"}
        try:
            res = await conn.call(action, params)
        except Exception as e:
            # Un servidor caído produce un fallo HONESTO de ESTA tool — jamás
            # una excepción que suba al ToolManager (contrato nº 2 de la fase).
            return {"success": False, "result": None,
                    "error": f"servidor MCP '{self.server_name}' inaccesible: {e}"}
        texto = clean_external(res.get("text") or "")
        structured = res.get("structured")
        if structured is not None:
            structured = clean_external(structured)
        if res.get("is_error"):
            return {"success": False, "result": None,
                    "error": texto or f"'{action}' devolvió un error sin detalle"}
        return {"success": True,
                "result": {"text": texto, "structured": structured},
                "error": None}


# ---------------------------------------------------------------------------
# Registro dinámico en el ToolManager
# ---------------------------------------------------------------------------
def register_enabled_servers(tool_manager) -> list[str]:
    """Registra un MCPToolProxy por cada servidor HABILITADO. Fail-soft por
    servidor: uno mal configurado no impide registrar los demás (y registrar
    NO conecta — la conexión es perezosa, así que un servidor caído tampoco
    frena el arranque). Devuelve los tool_id registrados."""
    registrados = []
    for cfg in store.list_servers():
        if not cfg.enabled:
            continue
        try:
            proxy = MCPToolProxy(cfg.name)
            tool_manager.register(proxy)
            registrados.append(proxy.tool_id)
        except Exception as e:
            logger.warning(f"[mcp] no se pudo registrar '{cfg.name}': {e!r}")
    return registrados


def unregister_server(tool_manager, server_name: str) -> None:
    tool_manager.unregister(permission_service.MCP_TOOL_PREFIX + server_name)
