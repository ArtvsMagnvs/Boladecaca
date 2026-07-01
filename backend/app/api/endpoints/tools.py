# /api/tools - Catalogo y log del ExecutionEngine (V0.5 Fase 2).
#
# Endpoints:
#   GET /api/tools/                   Lista de tools registradas con sus acciones
#   GET /api/tools/execution-log      Ultimas ejecuciones del engine (auditoria)
#   POST /api/tools/test              Ejecuta una tool concreta (para debugging)
#
# NOTA: el endpoint /test SOLO esta disponible si el backend se ejecuta
# con AITHERA_ENABLE_TOOL_TEST=1 en el entorno. Por defecto esta apagado
# para evitar que un usuario pueda ejecutar acciones destructivas sin
# pasar por el AgentManager.

import os
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.tools import tool_manager

# V0.5: prefix="/tools" para que las rutas sean /api/tools/ (no /api/).
router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/")
def list_tools():
    """Lista todas las herramientas registradas con sus acciones disponibles.
    El frontend usa esto para mostrar el catalogo en el formulario de
    creacion de agentes (multi-select de tools)."""
    return {"tools": tool_manager.list_tools(), "count": len(tool_manager.list_tools())}


@router.get("/execution-log")
def get_execution_log(limit: int = 50):
    """Devuelve las ultimas N ejecuciones del engine (orden cronologico
    inverso). Util para la UI de auditoria y para debug."""
    return {"log": tool_manager.get_log(limit=limit)}


class ToolTestRequest(BaseModel):
    tool_id: str
    action: str
    params: Dict[str, Any] = {}
    timeout: int = 30


@router.post("/test")
async def test_tool(req: ToolTestRequest):
    """Ejecuta una tool concreta sin pasar por el AgentManager. Pensado
    SOLO para debug manual desde el frontend (boton "Probar tool").

    Habilitado solo si AITHERA_ENABLE_TOOL_TEST=1. Por defecto apagado."""
    if os.getenv("AITHERA_ENABLE_TOOL_TEST") != "1":
        raise HTTPException(
            status_code=403,
            detail="AITHERA_ENABLE_TOOL_TEST no esta habilitado. Define AITHERA_ENABLE_TOOL_TEST=1 en .env para usar este endpoint.",
        )

    result = await tool_manager.execute(
        tool_id=req.tool_id,
        action=req.action,
        params=req.params,
        timeout=req.timeout,
    )
    return result
