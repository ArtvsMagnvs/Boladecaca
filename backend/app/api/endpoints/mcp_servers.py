# app/api/endpoints/mcp_servers.py — servidores MCP externos (V1.2 C1)
#
# CRUD de servidores + probar conexión + tools descubiertas. Todo delega en
# el barrel `app.mcp` (disciplina modular doc 16 — esta capa no conoce los
# internos). Los SECRETOS (tokens en env/headers) entran por POST y NUNCA
# vuelven a salir: el status solo devuelve los NOMBRES de las claves
# guardadas (mismo contrato que el token de Telegram).
#
# Efecto EN CALIENTE: añadir/activar registra el proxy en el ToolManager al
# momento; desactivar/borrar lo retira y apaga su conexión — sin reiniciar
# el backend (a diferencia de Telegram, cuyo polling se monta al arrancar).
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import mcp as mcp_service
from app.tools.tool_manager import tool_manager


def _refresh_tie_caches() -> None:
    """[C1b] El TIE cachea la lista de servidores en dos sitios (el bloque del
    clasificador y el mapa de capacidades). Al conectar o desconectar uno hay
    que tirarlas, o el cambio no se notaría hasta que caduquen. Best-effort:
    esto NUNCA puede hacer fallar un alta."""
    try:
        import app.tie as tie

        tie.invalidate_mcp_cache()
    except Exception:           # noqa: BLE001
        pass

router = APIRouter(prefix="/mcp", tags=["MCP"])


class MCPServerIn(BaseModel):
    name: str
    transport: str = "stdio"                 # stdio | sse | http
    command: str = ""
    args: List[str] = []
    url: str = ""
    description: str = ""
    enabled: bool = True
    # Secretos: None/omitido = conservar los guardados; {} = borrarlos.
    env: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None


class MCPServerOut(BaseModel):
    name: str
    transport: str
    command: str
    args: List[str]
    url: str
    description: str
    enabled: bool
    connected: bool
    last_error: Optional[str] = None
    tools_count: int
    secret_keys: Dict[str, List[str]]        # nombres, jamás valores


def _server_out(cfg) -> MCPServerOut:
    conn = mcp_service.get_connection(cfg.name) if cfg.enabled else None
    return MCPServerOut(
        name=cfg.name, transport=cfg.transport, command=cfg.command,
        args=cfg.args, url=cfg.url, description=cfg.description,
        enabled=cfg.enabled,
        connected=bool(conn and conn.connected),
        last_error=(conn.last_error if conn else None),
        tools_count=len(mcp_service.cached_tools(cfg.name)),
        secret_keys=mcp_service.secret_key_names(cfg.name),
    )


@router.get("/servers", response_model=List[MCPServerOut])
def list_mcp_servers():
    return [_server_out(cfg) for cfg in mcp_service.list_servers()]


@router.post("/servers", response_model=MCPServerOut)
async def upsert_mcp_server(body: MCPServerIn):
    cfg = mcp_service.MCPServerConfig(
        name=body.name.strip().lower(), transport=body.transport,
        command=body.command.strip(), args=[a for a in body.args if a.strip()],
        url=body.url.strip(), description=body.description.strip(),
        enabled=body.enabled,
    )
    secrets = None
    if body.env is not None or body.headers is not None:
        secrets = {"env": body.env or {}, "headers": body.headers or {}}
    try:
        mcp_service.upsert_server(cfg, secrets)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Reflejar el cambio EN CALIENTE en el ToolManager. `drop_connection`
    # antes de re-registrar: si cambió el comando/URL, la conexión vieja ya
    # no representa esta config.
    conn = mcp_service.get_connection(cfg.name)
    if conn is not None:
        await conn.shutdown()
    mcp_service.drop_connection(cfg.name)
    mcp_service.unregister_server(tool_manager, cfg.name)
    if cfg.enabled:
        mcp_service.register_enabled_servers(tool_manager)
    _refresh_tie_caches()
    return _server_out(mcp_service.get_server(cfg.name))


@router.delete("/servers/{name}")
async def delete_mcp_server(name: str):
    conn = mcp_service.get_connection(name)
    if conn is not None:
        await conn.shutdown()
    mcp_service.drop_connection(name)
    mcp_service.unregister_server(tool_manager, name)
    if not mcp_service.delete_server(name):
        raise HTTPException(status_code=404, detail=f"servidor no encontrado: {name}")
    _refresh_tie_caches()
    return {"ok": True}


@router.post("/servers/{name}/test", response_model=MCPServerOut)
async def test_mcp_server(name: str):
    """Conecta DE VERDAD (lanza el proceso / abre la URL) y descubre las
    tools. Es la única llamada cara a propósito — el botón «Probar»."""
    cfg = mcp_service.get_server(name)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"servidor no encontrado: {name}")
    if not cfg.enabled:
        raise HTTPException(status_code=400, detail="el servidor está desactivado")
    conn = mcp_service.get_connection(name)
    try:
        await conn.ensure_ready()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return _server_out(cfg)


@router.get("/directory/search")
async def search_directory(q: str, limit: int = 20):
    """[C1b] Busca en el registro OFICIAL de servidores MCP y devuelve cada
    entrada YA traducida a una config conectable (o marcada como no
    conectable, con el motivo). Fail-soft: sin red devuelve lista vacía, y el
    catálogo curado del frontend sigue estando."""
    entradas = await mcp_service.search_directory(q, limit=limit)
    return {"results": [mcp_service.entry_to_dict(e) for e in entradas]}


@router.get("/servers/{name}/tools")
def mcp_server_tools(name: str):
    """Las tools descubiertas (de la caché — para verlas en vivo, /test)."""
    if mcp_service.get_server(name) is None:
        raise HTTPException(status_code=404, detail=f"servidor no encontrado: {name}")
    return {"tools": [
        {"name": t.get("name"), "description": t.get("description", "")}
        for t in mcp_service.cached_tools(name)
    ]}
