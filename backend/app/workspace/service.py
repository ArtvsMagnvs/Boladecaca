# app/workspace/service.py — Logica del WPMS (V0.87, doc 18 §5, §6, §8)
#
# La capa que consulta la BD y aplica las reglas: progreso automatico por evento,
# versionado (completar milestone -> propagar version + activar el siguiente), y
# efectos de cierre de tarea (closed_at real). El destilado a mem_project y la
# emision de eventos al Event Bus son W3 — aqui quedan como hooks vacios para que
# W3 los rellene sin tocar el resto.
#
# Importa los submodulos hermanos por su ruta (no por el paquete, que puede estar
# a medio inicializar). Acceso a otros modulos SOLO por su API publica (doc 16).
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.db.database import SessionLocal
from app.db.models import Project, Task
from app.workspace.models import Milestone
from app.workspace.progress import compute_progress, is_done


# ---------------------------------------------------------------------------
# Progreso (doc 18 §8) — conteo de tareas, ratio 0.0-1.0
# ---------------------------------------------------------------------------
def milestone_progress(milestone_id: int, db) -> dict:
    """Progreso de un milestone: done/total de SUS tareas."""
    rows = db.query(Task.status).filter(Task.milestone_id == milestone_id).all()
    return compute_progress([r[0] for r in rows])


def project_progress(project_id: int, db) -> dict:
    """Progreso global del proyecto (todas sus tareas, con o sin milestone) +
    desglose por milestone. Es la union del estado operativo con significado de
    version que consumira el briefing (W3)."""
    rows = db.query(Task.status).filter(Task.project_id == project_id).all()
    overall = compute_progress([r[0] for r in rows])

    milestones = (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id)
        .order_by(Milestone.order_index.asc(), Milestone.id.asc())
        .all()
    )
    per_milestone = [
        {
            "milestone_id": m.id,
            "name": m.name,
            "version": m.version,
            "status": m.status,
            **milestone_progress(m.id, db),
        }
        for m in milestones
    ]
    return {"project_id": project_id, "overall": overall, "milestones": per_milestone}


def recompute_project_progress(project_id: Optional[int], db) -> Optional[dict]:
    """Reescribe Project.progress (ratio 0.0-1.0) por evento — NUNCA lo teclea el
    usuario (doc 18 §8). Se llama tras crear/editar/borrar una tarea. Idempotente
    y barato (una consulta agregada). None si el proyecto no existe."""
    if project_id is None:
        return None
    proj = db.get(Project, project_id)
    if proj is None:
        return None
    prog = compute_progress(
        [r[0] for r in db.query(Task.status).filter(Task.project_id == project_id).all()]
    )
    proj.progress = prog["ratio"]
    db.commit()
    return prog


# ---------------------------------------------------------------------------
# Efectos de cierre de tarea (doc 18 §3.5: closed_at real -> Learner/metricas)
# ---------------------------------------------------------------------------
def apply_task_status_side_effects(task: Task) -> None:
    """Mantiene closed_at coherente con el estado. Entrar en un estado 'hecho'
    sella closed_at (si no estaba); salir de 'hecho' lo limpia. NO hace commit —
    lo hace el endpoint que ya iba a commitear el cambio de estado."""
    if is_done(task.status):
        if task.closed_at is None:
            task.closed_at = datetime.utcnow()
    else:
        task.closed_at = None


# ---------------------------------------------------------------------------
# Versionado (doc 18 §6) — completar milestone propaga la version
# ---------------------------------------------------------------------------
def complete_milestone(milestone_id: int, db) -> Optional[Milestone]:
    """Marca un milestone como 'done' y aplica el flujo de version real de
    Aithera: current_version <- milestone.version, el siguiente milestone
    'planned' pasa a 'active' (y su version es el nuevo target). None si no
    existe. El destilado a mem_project + evento milestone.completed son W3
    (hook _on_milestone_completed)."""
    m = db.get(Milestone, milestone_id)
    if m is None:
        return None

    m.status = "done"
    m.completed_at = datetime.utcnow()

    proj = db.get(Project, m.project_id) if m.project_id else None
    if proj is not None and m.version:
        proj.current_version = m.version

    nxt = (
        db.query(Milestone)
        .filter(Milestone.project_id == m.project_id, Milestone.status == "planned")
        .order_by(Milestone.order_index.asc(), Milestone.id.asc())
        .first()
    )
    if nxt is not None:
        nxt.status = "active"
        if proj is not None and nxt.version:
            proj.target_version = nxt.version

    db.commit()
    db.refresh(m)

    recompute_project_progress(m.project_id, db)
    _on_milestone_completed(m, db)  # W3: destilado a mem_project + evento
    return m


# ---------------------------------------------------------------------------
# Hooks de integracion — VACIOS en W1, los rellena W3 (doc 18 §5, §10)
# ---------------------------------------------------------------------------
def _on_milestone_completed(milestone: Milestone, db) -> None:
    """W3: destila un resumen del milestone a mem_project (memory_router.store,
    type=PROJECT) y emite `milestone.completed` al Event Bus. En W1 es no-op a
    proposito — el modelo y el versionado se prueban sin acoplar el MOS todavia."""
    return None


def _on_task_closed(task: Task, db) -> None:
    """W3: si la tarea trae links.decision, registra el hecho en `decisions`
    (decision_service) y emite `task.closed`. No-op en W1."""
    return None
