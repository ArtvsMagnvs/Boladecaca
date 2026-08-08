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
# [C1c] OAuth: el usuario autoriza en la web del propio servicio, sin pegar
# tokens. Se expone lo mínimo — el flujo lo conduce el cliente.
from app.mcp.oauth import AUTHORIZE_TIMEOUT_S
from app.mcp.oauth import cancel as cancel_oauth
from app.mcp.oauth import forget as forget_oauth
from app.mcp.oauth import is_authorized
from app.mcp.oauth import pending_url as pending_authorize_url
from app.mcp.oauth import redirect_uri as oauth_redirect_uri
from app.mcp.oauth import resolve_callback as resolve_oauth_callback
# [C1b, doc 42 §2] El registro OFICIAL de servidores MCP: buscar lo que no
# esté en el catálogo curado y traducirlo a una config conectable.
from app.mcp.directory import (
    DirectoryEntry,
    entry_to_dict,
    map_entry,
    search as search_directory,
)

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
    "DirectoryEntry",
    "entry_to_dict",
    "map_entry",
    "search_directory",
    "AUTHORIZE_TIMEOUT_S",
    "cancel_oauth",
    "forget_oauth",
    "is_authorized",
    "oauth_redirect_uri",
    "pending_authorize_url",
    "resolve_oauth_callback",
]
