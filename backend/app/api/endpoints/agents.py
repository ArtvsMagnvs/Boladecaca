# /api/agents - CRUD + lifecycle de agentes (V0.5 Fase 2).
#
# Endpoints:
#   GET    /api/agents/                       listar agentes (filtro ?is_active=true)
#   POST   /api/agents/                       crear agente
#   GET    /api/agents/{agent_id}             detalle
#   PATCH  /api/agents/{agent_id}             actualizar campos
#   DELETE /api/agents/{agent_id}             eliminar (cancela ejecuciones en curso)
#
#   POST   /api/agents/{agent_id}/execute     lanzar una tarea (crea AgentExecution)
#   GET    /api/agents/{agent_id}/executions  historial de ejecuciones del agente
#   GET    /api/agents/executions/{exec_id}   detalle de una ejecucion concreta
#   DELETE /api/agents/executions/{exec_id}   eliminar / cancelar ejecucion

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.db.database import SessionLocal
from app.db.models import Agent, AgentExecution
from app.db.schemas import (
    AgentCreate, AgentUpdate, AgentResponse,
    AgentExecutionCreate, AgentExecutionResponse,
)
from app.agents.agent_manager import agent_manager

# V0.5 (Fase 2 AgentManager + ExecutionEngine): el prefix="/agents" es
# necesario para que las rutas sean /api/agents/ (no /api/ como seria
# sin prefix). Esto es asi porque el main.py hace include_router con
# prefix="/api" - los routers son responsables de anadir su propia
# seccion del path.
router = APIRouter(prefix="/agents", tags=["agents"])

# [2026-08-02] Tope de un adjunto del chat. Generoso para un documento o una
# captura, acotado para que nadie llene el disco desde el chat sin querer.
MAX_ATTACH_BYTES = 50 * 1024 * 1024


def _agent_to_response(agent: Agent) -> AgentResponse:
    """Convierte el modelo SQLAlchemy Agent a AgentResponse (Pydantic).
    El field_validator de AgentResponse parsea allowed_tools de JSON."""
    return AgentResponse.model_validate(agent)


def _execution_to_response(ex: AgentExecution) -> AgentExecutionResponse:
    return AgentExecutionResponse.model_validate(ex)


@router.get("/", response_model=List[AgentResponse])
def list_agents(
    is_active: Optional[bool] = Query(None, description="Filtrar por agentes activos"),
    project_id: Optional[int] = Query(None, description="V0.87 WPMS: filtrar por proyecto (tarjeta del lienzo)"),
):
    """Lista todos los agentes (mas recientes primero). Opcionalmente filtra por is_active/project_id."""
    return [
        _agent_to_response(a)
        for a in agent_manager.list_agents(only_active=bool(is_active), project_id=project_id)
    ]


@router.post("/", response_model=AgentResponse, status_code=201)
def create_agent(payload: AgentCreate):
    """Crea un nuevo agente."""
    try:
        agent = agent_manager.create_agent(
            name=payload.name,
            agent_type=payload.agent_type or "generic",
            description=payload.description,
            system_prompt=payload.system_prompt,
            allowed_tools=payload.allowed_tools,
            max_execution_time=payload.max_execution_time,
            is_active=payload.is_active,
            project_id=payload.project_id,
            skills=payload.skills,
            icon=payload.icon,
            role=payload.role,
        )
        return _agent_to_response(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error creando agente: {type(e).__name__}: {e}")


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: int):
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"agente no encontrado: id={agent_id}")
    return _agent_to_response(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: int, payload: AgentUpdate):
    """Actualiza parcialmente un agente."""
    try:
        # Solo pasamos los campos que el cliente envio (no None).
        kwargs = payload.model_dump(exclude_unset=True)
        agent = agent_manager.update_agent(agent_id, **kwargs)
        if not agent:
            raise HTTPException(status_code=404, detail=f"agente no encontrado: id={agent_id}")
        return _agent_to_response(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error actualizando agente: {type(e).__name__}: {e}")


@router.delete("/{agent_id}", status_code=204)
def delete_agent(agent_id: int):
    try:
        ok = agent_manager.delete_agent(agent_id)
    except ValueError as e:
        # [2026-08-02] El orquestador de un proyecto no se borra. 409 y no 400:
        # la peticion es valida, el estado del recurso es lo que lo impide.
        raise HTTPException(status_code=409, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"agente no encontrado: id={agent_id}")
    return None


# ----------------------------------------------------------------------
# Ejecuciones (Fase 2 AgentManager + ExecutionEngine)
# ----------------------------------------------------------------------

@router.post("/{agent_id}/execute", response_model=AgentExecutionResponse, status_code=201)
async def execute_agent(agent_id: int, payload: AgentExecutionCreate):
    """Lanza una tarea sobre el agente. Devuelve el AgentExecution en
    estado 'pending' (la coroutine arrancara inmediatamente en background)."""
    try:
        execution = agent_manager.create_execution(
            agent_id=agent_id, task=payload.task, model=payload.model)
        return _execution_to_response(execution)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error lanzando tarea: {type(e).__name__}: {e}")


class AttachResult(BaseModel):
    """Lo que devuelve subir un adjunto: dónde quedó, para que el chat pueda
    nombrarlo en el mensaje y el agente leerlo con `document`/`filesystem`."""
    path: str
    name: str
    size: int


@router.post("/{agent_id}/attach", response_model=AttachResult, status_code=201)
async def attach_file(agent_id: int, file: UploadFile = File(...)):
    """[2026-08-02] Adjuntar un archivo o imagen desde el chat del agente.

    DECISIÓN DEL USUARIO: el archivo se COPIA a la carpeta del proyecto (en
    `_adjuntos/`), no se lee y se tira. Así el agente puede volver a
    consultarlo en misiones futuras y no hay que inventar permisos nuevos: cae
    dentro de `repo_path`, que es donde ya puede trabajar.

    CUALQUIER formato: no se filtra por extensión (petición explícita — "solo
    añadir archivos o fotos"). Lo que sí se acota es el TAMAÑO."""
    import shutil
    from pathlib import Path

    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"agente no encontrado: id={agent_id}")
    if not agent.project_id:
        raise HTTPException(status_code=400, detail="este agente no pertenece a ningún proyecto")

    db = SessionLocal()
    try:
        from app.db.database import Project

        project = db.get(Project, agent.project_id)
        repo = (project.repo_path or "").strip() if project else ""
    finally:
        db.close()
    if not repo:
        raise HTTPException(
            status_code=400,
            detail="el proyecto no tiene carpeta asignada: elígela primero (📁 en el proyecto)")

    destino_dir = Path(repo).expanduser() / "_adjuntos"
    try:
        destino_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"no se pudo crear {destino_dir}: {e}")

    # Nombre saneado: solo el nombre base, nunca una ruta que se escape.
    nombre = Path(file.filename or "adjunto").name or "adjunto"
    destino = destino_dir / nombre
    i = 1
    while destino.exists():                      # no pisar un adjunto anterior
        destino = destino_dir / f"{Path(nombre).stem}_{i}{Path(nombre).suffix}"
        i += 1

    escritos = 0
    try:
        with destino.open("wb") as out:
            while True:
                trozo = await file.read(1024 * 1024)
                if not trozo:
                    break
                escritos += len(trozo)
                if escritos > MAX_ATTACH_BYTES:
                    out.close()
                    destino.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"archivo demasiado grande (máx. {MAX_ATTACH_BYTES // (1024*1024)} MB)")
                out.write(trozo)
    except HTTPException:
        raise
    except Exception as e:
        destino.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"no se pudo guardar: {type(e).__name__}: {e}")

    return AttachResult(path=str(destino), name=destino.name, size=escritos)


class GrantFolder(BaseModel):
    path: str


@router.post("/{agent_id}/folders", response_model=AgentResponse)
def grant_folder(agent_id: int, payload: GrantFolder):
    """[2026-08-02] Dar a ESTE agente acceso a una carpeta CONCRETA, además de
    la del proyecto (botón de carpeta del chat). Se acumulan en
    `Agent.extra_paths` y `Authority._check_path_scope` las trata como raíces
    válidas — nunca sustituyen a la del proyecto, la amplían."""
    import os

    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"agente no encontrado: id={agent_id}")
    ruta = (payload.path or "").strip()
    if not ruta:
        raise HTTPException(status_code=400, detail="falta la carpeta")
    ruta = os.path.abspath(os.path.expanduser(ruta))
    if not os.path.isdir(ruta):
        raise HTTPException(status_code=400, detail=f"no es una carpeta existente: {ruta}")

    actuales = list(agent.extra_paths or [])
    if ruta not in actuales:
        actuales.append(ruta)
    try:
        actualizado = agent_manager.update_agent(agent_id, extra_paths=actuales)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _agent_to_response(actualizado)


@router.get("/{agent_id}/executions", response_model=List[AgentExecutionResponse])
def list_agent_executions(
    agent_id: int,
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filtrar por status (pending/running/completed/failed/cancelled)"),
):
    if not agent_manager.get_agent(agent_id):
        raise HTTPException(status_code=404, detail=f"agente no encontrado: id={agent_id}")
    return [
        _execution_to_response(e) for e in agent_manager.list_executions(
            agent_id=agent_id, limit=limit, only_status=status,
        )
    ]


@router.get("/executions/{execution_id}", response_model=AgentExecutionResponse)
def get_execution(execution_id: int):
    ex = agent_manager.get_execution(execution_id)
    if not ex:
        raise HTTPException(status_code=404, detail=f"ejecucion no encontrada: id={execution_id}")
    return _execution_to_response(ex)


@router.delete("/executions/{execution_id}", status_code=204)
def cancel_or_delete_execution(execution_id: int):
    """Cancela (si esta en curso) o elimina del historial una ejecucion."""
    ex = agent_manager.get_execution(execution_id)
    if not ex:
        raise HTTPException(status_code=404, detail=f"ejecucion no encontrada: id={execution_id}")
    # Si esta en curso o pendiente, lo marcamos como cancelado.
    if ex.status in ("pending", "running"):
        ok = agent_manager.cancel_execution(execution_id)
        if not ok:
            raise HTTPException(status_code=500, detail="no se pudo cancelar")
        return None
    # Si ya termino, lo eliminamos del historial.
    if not agent_manager.delete_execution(execution_id):
        raise HTTPException(status_code=500, detail="no se pudo eliminar")
    return None
