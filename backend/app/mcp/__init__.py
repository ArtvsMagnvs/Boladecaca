# app/mcp/__init__.py — API pública del cliente MCP (V1.2 C1, doc 27 §C1)
#
# Disciplina modular (doc 16): el resto de la app consume SOLO lo de aquí.
# store/client/proxy son internos (vigilados por test_module_boundaries).
#
# Qué es este módulo: Aithera como CLIENTE del Model Context Protocol — el
# usuario conecta servidores MCP externos (GitHub, o cualquier otro del
# ecosistema) y sus tools entran al ToolManager con las MISMAS validaciones
# que una tool nativa, más gate obligatorio y permiso `mcp.use` (A3b).
# El servidor MCP de Aithera (exponer el ToolManager hacia fuera) es C2.
from app.mcp.proxy import MCPToolProxy, register_enabled_servers, unregister_server
from app.mcp.store import (
    MCPServerConfig,
    TRANSPORTS,
    cached_tools,
    delete_server,
    get_server,
    list_servers,
    secret_key_names,
    set_enabled,
    upsert_server,
    validate_config,
)
from app.mcp.client import get_connection, drop_connection, shutdown_all

__all__ = [
    "MCPToolProxy",
    "MCPServerConfig",
    "TRANSPORTS",
    "register_enabled_servers",
    "unregister_server",
    "cached_tools",
    "delete_server",
    "get_server",
    "list_servers",
    "secret_key_names",
    "set_enabled",
    "upsert_server",
    "validate_config",
    "get_connection",
    "drop_connection",
    "shutdown_all",
]
