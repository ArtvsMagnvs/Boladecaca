# app/workspace/service.py — Logica del WPMS (V0.87, doc 18 §5, §6, §8, §10)
#
# La capa que consulta la BD y aplica las reglas: progreso automatico por evento,
# versionado (completar milestone -> propagar version + activar el siguiente),
# efectos de cierre de tarea (closed_at real), destilado a mem_project (SOLO
# hechos permanentes, doc 18 §5.1 — el estado operativo JAMAS se escribe al MOS)
# y emision de eventos al Event Bus (doc 18 §10, doc 17).
#
# Nota de concurrencia (importante para quien toque esto despues): `events.emit`
# necesita un event loop CORRIENDO en el hilo actual (asyncio.get_running_loop);
# los endpoints que llaman a las funciones de aqui que emiten eventos o escriben
# en el MOS son `async def` (workspace.py) precisamente por eso — al ejecutarse
# directamente sobre el loop (no en threadpool, que es lo que pasa con `def`
# sync en FastAPI), cualquier llamada sync anidada a events.emit() funciona sin
# necesitar puentes entre hilos. Las funciones de aqui que SOLO emiten (sin
# tocar el MOS) se quedan sync a proposito — no necesitan `await`, solo que se
# invoquen desde dentro de esa pila de llamadas async.
#
# Importa los submodulos hermanos por su ruta (no por el paquete, que puede estar
# a medio inicializar). Acceso a otros modulos SOLO por su API publica (doc 16).
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from app.core.events import emit
from app.db.database import SessionLocal
from app.db.models import Project, Task
from app.memory import MemoryType, memory_router
from app.services.decision_service import store_decision
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
    y barato (una consulta agregada). None si el proyecto no existe.

    Emite `project.progress_changed` (doc 18 §10) SOLO si el ratio realmente
    cambio — evita ruido en el bus cuando se recalcula sin que nada se moviera
    (p.ej. borrar una tarea de un milestone distinto al que se muestra)."""
    if project_id is None:
        return None
    proj = db.get(Project, project_id)
    if proj is None:
        return None
    old_ratio = proj.progress
    prog = compute_progress(
        [r[0] for r in db.query(Task.status).filter(Task.project_id == project_id).all()]
    )
    proj.progress = prog["ratio"]
    db.commit()
    if old_ratio != prog["ratio"]:
        emit(
            "project.progress_changed",
            source="workspace",
            payload={"project_id": project_id, "ratio": prog["ratio"], "done": prog["done"], "total": prog["total"]},
        )
    return prog


# ---------------------------------------------------------------------------
# Efectos de cierre de tarea (doc 18 §3.5: closed_at real -> Learner/metricas)
# ---------------------------------------------------------------------------
def apply_task_status_side_effects(task: Task) -> bool:
    """Mantiene closed_at coherente con el estado. Entrar en un estado 'hecho'
    sella closed_at (si no estaba); salir de 'hecho' lo limpia. NO hace commit —
    lo hace el endpoint que ya iba a commitear el cambio de estado.

    Devuelve True si la tarea ACABA de cerrarse en esta llamada (closed_at
    pasa de None a un valor) — el endpoint lo usa para decidir si dispara
    `on_task_closed` (evento + posible decision), sin repetirlo si la tarea
    ya estaba cerrada y solo cambio otro campo."""
    if is_done(task.status):
        if task.closed_at is None:
            task.closed_at = datetime.utcnow()
            return True
        return False
    task.closed_at = None
    return False


def emit_task_created(task: Task) -> None:
    """`task.created` (doc 18 §10). Sync — ver nota de concurrencia arriba."""
    emit(
        "task.created",
        source="workspace",
        payload={"task_id": task.id, "project_id": task.project_id, "title": task.title, "status": task.status},
    )


def emit_task_status_changed(task: Task, old_status: str, new_status: str) -> None:
    """`task.status_changed` (doc 18 §10), payload {task_id, from, to} tal cual
    lo pide el diseno."""
    emit(
        "task.status_changed",
        source="workspace",
        payload={"task_id": task.id, "project_id": task.project_id, "from": old_status, "to": new_status},
    )


# ---------------------------------------------------------------------------
# Versionado (doc 18 §6) — completar milestone propaga la version
# ---------------------------------------------------------------------------
async def complete_milestone(milestone_id: int, db) -> Optional[Milestone]:
    """Marca un milestone como 'done' y aplica el flujo de version real de
    Aithera: current_version <- milestone.version, el siguiente milestone
    'planned' pasa a 'active' (y su version es el nuevo target). None si no
    existe."""
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
    await _on_milestone_completed(m, proj, db)
    return m


# ---------------------------------------------------------------------------
# Archivado (doc 18 §5.1: "al archivar un proyecto -> resumen final")
# ---------------------------------------------------------------------------
async def archive_project(project_id: int, db) -> Optional[Project]:
    """Archiva un proyecto (sella `archived_at`) y destila un resumen final a
    mem_project. Los proyectos se archivan, no se borran (doc 18 §3.3) — sigue
    consultable, solo deja de contar como 'activo'. Idempotente: archivar dos
    veces no reescribe `archived_at` (conserva la fecha real de archivado)."""
    proj = db.get(Project, project_id)
    if proj is None:
        return None
    if proj.archived_at is None:
        proj.archived_at = datetime.utcnow()
        db.commit()
        db.refresh(proj)
        await _on_project_archived(proj, db)
    return proj


# ---------------------------------------------------------------------------
# Hooks de integracion con el MOS (doc 18 §5, §10) — SOLO hechos permanentes,
# nunca estado operativo (§5.1 primera linea). `dedup_key` por entidad hace
# cada escritura idempotente: re-archivar o completar de nuevo no duplica.
# ---------------------------------------------------------------------------
async def _on_milestone_completed(milestone: Milestone, project: Optional[Project], db) -> None:
    """Destila un resumen del milestone a mem_project (memory_router.store,
    type=PROJECT) y emite `milestone.completed` al Event Bus. Best-effort: si
    el MOS esta caido, el versionado (ya commiteado) no se revierte — la
    memoria semantica es un espejo, nunca la fuente de verdad operativa."""
    proj_name = project.name if project else str(milestone.project_id)
    content = f"Milestone '{milestone.name}'" + (f" ({milestone.version})" if milestone.version else "")
    content += f" completado en el proyecto {proj_name}."
    if milestone.description:
        content += f" {milestone.description}"
    try:
        await memory_router.store(
            content=content,
            memory_type=MemoryType.PROJECT,
            source="workspace",
            metadata={
                "kind": "milestone_completed",
                "project_id": milestone.project_id,
                "milestone_id": milestone.id,
                "version": milestone.version,
            },
            dedup_key=f"milestone:{milestone.id}",
        )
    except Exception as e:  # el espejo nunca rompe el versionado ya commiteado
        print(f"[workspace] destilado mem_project (milestone) fallo (no critico): {e}")

    emit(
        "milestone.completed",
        source="workspace",
        payload={"milestone_id": milestone.id, "project_id": milestone.project_id, "version": milestone.version},
    )


async def _on_project_archived(project: Project, db) -> None:
    """Resumen final del proyecto a mem_project al archivarlo (doc 18 §5.1).
    No emite evento propio — doc 18 §10 no lista `project.archived` entre los
    5 eventos del WPMS; es una accion deliberada y puntual del usuario, no un
    hecho operativo del que otros sistemas necesiten reaccionar en caliente."""
    content = f"Proyecto '{project.name}' archivado"
    if project.current_version:
        content += f" en la version {project.current_version}"
    content += "."
    if project.description:
        content += f" {project.description}"
    try:
        await memory_router.store(
            content=content,
            memory_type=MemoryType.PROJECT,
            source="workspace",
            metadata={
                "kind": "project_archived",
                "project_id": project.id,
                "final_version": project.current_version,
            },
            dedup_key=f"project_archived:{project.id}",
        )
    except Exception as e:
        print(f"[workspace] destilado mem_project (archivado) fallo (no critico): {e}")


async def on_task_closed(task: Task, db) -> None:
    """Se llama cuando una tarea ACABA de cerrarse (ver
    `apply_task_status_side_effects`). Si trae `links.decision`, registra el
    hecho en `decisions` (decision_service — fuente de verdad SQL + espejo
    mem_decision, doc 18 §5.1); una tarea cerrada SIN decision no escribe nada
    al MOS (es estado operativo puro). Siempre emite `task.closed` — el AE/
    Learner (futuro) quieren saber que se cerro una tarea aunque no traiga
    decision."""
    links = task.links or {}
    decision_text = (links.get("decision") or "").strip()
    if decision_text:
        proj = db.get(Project, task.project_id) if task.project_id else None
        try:
            await store_decision(
                title=task.title,
                body=decision_text,
                project=proj.name if proj else None,
                mission_id=links.get("mission_id") or None,
            )
        except Exception as e:  # la decision es best-effort; el cierre de la tarea ya esta commiteado
            print(f"[workspace] registro de decision (task.closed) fallo (no critico): {e}")

    emit(
        "task.closed",
        source="workspace",
        payload={"task_id": task.id, "project_id": task.project_id, "title": task.title},
    )


# ---------------------------------------------------------------------------
# Briefing (doc 18 §7): lo que el daily_briefing (V0.85 M3) lee del WPMS.
# Consulta SQL barata — sin Gmail, sin LLM en caliente (mismo presupuesto de
# latencia que el resto del briefing). Vive aqui (no en memory/summarizer.py)
# por disciplina modular (doc 16): el WPMS es dueño de sus propias consultas,
# summarizer.py solo llama a esta API publica y mezcla el resultado.
# ---------------------------------------------------------------------------
def _task_brief(t: Task) -> dict[str, Any]:
    return {
        "task_id": t.id, "project_id": t.project_id, "title": t.title,
        "priority": t.priority, "due_date": t.due_date.isoformat() if t.due_date else None,
    }


def briefing_snapshot(db) -> dict[str, Any]:
    """Milestone activo + progreso (por proyecto no archivado), deadlines
    próximos (7 días), tareas de alta prioridad abiertas, bloqueos
    (`depends_on` con alguna dependencia aun sin cerrar) y actividad reciente
    (últimas tareas tocadas). Exactamente lo que pide doc 18 §7."""
    projects = db.query(Project).filter(Project.archived_at.is_(None)).all()
    active_milestones = []
    for p in projects:
        m = (
            db.query(Milestone)
            .filter(Milestone.project_id == p.id, Milestone.status == "active")
            .order_by(Milestone.order_index.asc(), Milestone.id.asc())
            .first()
        )
        if m is not None:
            active_milestones.append({
                "project_id": p.id,
                "project_name": p.name,
                "milestone_id": m.id,
                "name": m.name,
                "version": m.version,
                **milestone_progress(m.id, db),
            })

    upcoming_cutoff = datetime.utcnow() + timedelta(days=7)
    upcoming = (
        db.query(Task)
        .filter(Task.due_date.isnot(None), Task.due_date <= upcoming_cutoff, Task.closed_at.is_(None))
        .order_by(Task.due_date.asc())
        .limit(10)
        .all()
    )

    high_priority = (
        db.query(Task)
        .filter(Task.priority == "high", Task.closed_at.is_(None))
        .order_by(Task.id.desc())
        .limit(10)
        .all()
    )

    open_task_ids = {
        r[0] for r in db.query(Task.id).filter(Task.closed_at.is_(None)).all()
    }
    blocked = []
    if open_task_ids:
        for t in db.query(Task).filter(Task.closed_at.is_(None), Task.depends_on.isnot(None)).all():
            unresolved = [d for d in (t.depends_on or []) if d in open_task_ids]
            if unresolved:
                blocked.append({**_task_brief(t), "blocked_by": unresolved})

    recent_activity = (
        db.query(Task).order_by(Task.updated_at.desc()).limit(8).all()
    )

    return {
        "active_milestones": active_milestones,
        "upcoming_deadlines": [_task_brief(t) for t in upcoming],
        "high_priority_open": [_task_brief(t) for t in high_priority],
        "blocked": blocked[:10],
        "recent_activity": [
            {**_task_brief(t), "status": t.status, "updated_at": t.updated_at.isoformat() if t.updated_at else None}
            for t in recent_activity
        ],
    }
