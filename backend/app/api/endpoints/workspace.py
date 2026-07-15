# app/api/endpoints/workspace.py — WPMS API (V0.87, doc 18 §11)
#
# ABSORBE /api/projects y /api/tasks manteniendo las rutas IDENTICAS por
# contrato (mismo patron que el split del god-endpoint de email, CLAUDE §16.1) +
# anade /api/milestones (CRUD + completar) y /api/workspace/progress.
#
# Progreso automatico: crear/editar/borrar una tarea recalcula el progreso del
# proyecto (workspace_service, doc 18 §8) — el usuario NUNCA teclea un %.
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db.models import Project, Task
from app.db.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    MilestoneCreate, MilestoneUpdate, MilestoneResponse,
)
from app.workspace import Milestone, workspace_service

# Sub-routers con las rutas historicas intactas + las nuevas.
projects_router = APIRouter(prefix="/projects", tags=["workspace:projects"])
tasks_router = APIRouter(prefix="/tasks", tags=["workspace:tasks"])
milestones_router = APIRouter(prefix="/milestones", tags=["workspace:milestones"])
workspace_router = APIRouter(prefix="/workspace", tags=["workspace"])


# ===========================================================================
# PROJECTS — contrato identico al viejo projects.py
# ===========================================================================
@projects_router.get("/", response_model=List[ProjectResponse])
def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get all projects (paginated)."""
    return db.query(Project).order_by(Project.id.desc()).offset(skip).limit(limit).all()


@projects_router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    project = Project(**project_data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@projects_router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@projects_router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project_data: ProjectUpdate, db: Session = Depends(get_db)):
    """Update a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in project_data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@projects_router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


@projects_router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(project_id: int, db: Session = Depends(get_db)):
    """Archiva un proyecto — sella `archived_at` y destila un resumen final a
    mem_project (doc 18 §5.1). Los proyectos se archivan, no se borran; siguen
    listados y consultables, solo dejan de contar como activos."""
    project = await workspace_service.archive_project(project_id, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ===========================================================================
# TASKS — contrato identico al viejo tasks.py + progreso automatico (§8)
# ===========================================================================
@tasks_router.get("/", response_model=List[TaskResponse])
def get_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get all tasks (paginated)."""
    return db.query(Task).order_by(Task.id.desc()).offset(skip).limit(limit).all()


@tasks_router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task. Recalcula el progreso del proyecto (doc 18 §8) y
    emite `task.created` (+ `task.closed` si nace ya en un estado 'hecho',
    doc 18 §10). `async def` a proposito: los eventos/MOS necesitan un event
    loop corriendo en el hilo (ver nota de concurrencia en workspace/service.py)."""
    task = Task(**task_data.model_dump())
    just_closed = workspace_service.apply_task_status_side_effects(task)  # closed_at si nace 'done'
    db.add(task)
    db.commit()
    db.refresh(task)
    workspace_service.recompute_project_progress(task.project_id, db)
    workspace_service.emit_task_created(task)
    if just_closed:
        await workspace_service.on_task_closed(task, db)
    return task


@tasks_router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@tasks_router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_data: TaskUpdate, db: Session = Depends(get_db)):
    """Update a task. Mantiene closed_at coherente, recalcula el progreso de
    los proyectos afectados (el viejo y el nuevo si la tarea cambia de
    proyecto) y emite `task.status_changed`/`task.closed` (doc 18 §10)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_project_id = task.project_id
    old_status = task.status
    for key, value in task_data.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    just_closed = workspace_service.apply_task_status_side_effects(task)

    db.commit()
    db.refresh(task)

    workspace_service.recompute_project_progress(task.project_id, db)
    if old_project_id is not None and old_project_id != task.project_id:
        workspace_service.recompute_project_progress(old_project_id, db)

    if task.status != old_status:
        workspace_service.emit_task_status_changed(task, old_status, task.status)
    if just_closed:
        await workspace_service.on_task_closed(task, db)
    return task


@tasks_router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task. Recalcula el progreso del proyecto que la contenia
    (puede emitir `project.progress_changed`, doc 18 §10)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project_id = task.project_id
    db.delete(task)
    db.commit()
    workspace_service.recompute_project_progress(project_id, db)
    return {"message": "Task deleted"}


# ===========================================================================
# MILESTONES — CRUD + completar (versionado, doc 18 §6)
# ===========================================================================
def _milestone_out(m: Milestone, db: Session) -> MilestoneResponse:
    """Respuesta de un milestone con su progreso calculado (no es columna)."""
    resp = MilestoneResponse.model_validate(m)
    resp.progress = workspace_service.milestone_progress(m.id, db)
    return resp


@milestones_router.get("/", response_model=List[MilestoneResponse])
def get_milestones(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Milestones (opcionalmente filtrados por proyecto), ordenados por roadmap."""
    q = db.query(Milestone)
    if project_id is not None:
        q = q.filter(Milestone.project_id == project_id)
    milestones = q.order_by(Milestone.order_index.asc(), Milestone.id.asc()).all()
    return [_milestone_out(m, db) for m in milestones]


@milestones_router.post("/", response_model=MilestoneResponse, status_code=201)
def create_milestone(data: MilestoneCreate, db: Session = Depends(get_db)):
    """Create a milestone."""
    milestone = Milestone(**data.model_dump())
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return _milestone_out(milestone, db)


@milestones_router.get("/{milestone_id}", response_model=MilestoneResponse)
def get_milestone(milestone_id: int, db: Session = Depends(get_db)):
    """Get a specific milestone."""
    m = db.get(Milestone, milestone_id)
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return _milestone_out(m, db)


@milestones_router.put("/{milestone_id}", response_model=MilestoneResponse)
def update_milestone(milestone_id: int, data: MilestoneUpdate, db: Session = Depends(get_db)):
    """Update a milestone."""
    m = db.get(Milestone, milestone_id)
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(m, key, value)
    db.commit()
    db.refresh(m)
    return _milestone_out(m, db)


@milestones_router.post("/{milestone_id}/complete", response_model=MilestoneResponse)
async def complete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    """Marca un milestone como completado: propaga la version al proyecto,
    activa el siguiente (doc 18 §6), destila un resumen a mem_project y emite
    `milestone.completed` (doc 18 §5.1, §10)."""
    m = await workspace_service.complete_milestone(milestone_id, db)
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return _milestone_out(m, db)


@milestones_router.delete("/{milestone_id}")
def delete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    """Delete a milestone. Las tareas que lo referencian pasan a backlog
    (milestone_id = None) — una tarea puede vivir sin milestone (doc 18 §4)."""
    m = db.get(Milestone, milestone_id)
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")

    db.query(Task).filter(Task.milestone_id == milestone_id).update(
        {Task.milestone_id: None}, synchronize_session=False
    )
    db.delete(m)
    db.commit()
    return {"message": "Milestone deleted"}


# ===========================================================================
# WORKSPACE — progreso global del proyecto (§8) + desglose por milestone
# ===========================================================================
@workspace_router.get("/progress")
def get_project_progress(project_id: int = Query(...), db: Session = Depends(get_db)):
    """Progreso del proyecto: overall (todas las tareas) + por milestone.
    Consulta SQL barata — la que consumira el briefing en W3 (sin Gmail/LLM)."""
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return workspace_service.project_progress(project_id, db)


# Router agregado que monta main.py (un solo include_router, prefijo /api).
router = APIRouter()
router.include_router(projects_router)
router.include_router(tasks_router)
router.include_router(milestones_router)
router.include_router(workspace_router)
