# app/tie/tracer.py — Trace & Learn del TIE (doc 11-B §B.1/§6, T1 base)
#
# Escribe la traza de cada misión en `orchestrator_traces` (estado operativo del
# TIE en SQL — NO en el MOS). En T1: record_start / record_intent / record_end.
# En T2 se añade el espejo Decision API (record_plan); en T3 el checkpoint por
# transición (update_graph); en T4 los eventos mission.* + el outcome del
# responder. Es la fuente de la que el Learner (V1.1) aprende (doc 14 §4.4).
#
# BEST-EFFORT SIEMPRE: un fallo del tracer nunca rompe el pipeline (la respuesta
# al usuario es lo primero). Cada método traga sus excepciones y loguea.
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from app.core.logging_config import get_system_logger
from app.db.database import OrchestratorTrace, SessionLocal
from app.tie.contracts import Intent, Mission, TaskGraph

logger = get_system_logger("tie.tracer")


def record_start(mission: Mission, *, channel: Optional[str] = None) -> str:
    """Abre una traza para una misión. Devuelve el trace_id (uuid). El trace_id
    y el mission_id son distintos: una misión puede (V1.2) tener varias trazas."""
    trace_id = uuid.uuid4().hex
    db = SessionLocal()
    try:
        db.add(OrchestratorTrace(
            id=trace_id,
            mission_id=mission.id,
            channel=channel or mission.channel,
            state="running",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        db.commit()
    except Exception as e:
        logger.error(f"[tracer] record_start falló (no crítico): {type(e).__name__}: {e}")
        db.rollback()
    finally:
        db.close()
    return trace_id


def record_intent(trace_id: str, intent: Intent, *, model_used: Optional[str] = None) -> None:
    """Guarda la intención clasificada (qué quería el usuario + qué necesita)."""
    _update(trace_id, intent=intent.to_dict(), model_used=model_used)


def record_plan(trace_id: str, graph: TaskGraph, *, decision_id: Optional[str] = None,
                context_query_id: Optional[str] = None) -> None:
    """T2: guarda el TaskGraph y enlaza la decisión/contexto. En T3 el checkpoint
    por transición reescribe `plan` en cada cambio de estado de nodo."""
    _update(trace_id, plan=graph.to_dict(), decision_id=decision_id,
            context_query_id=context_query_id, state="running")


def update_graph(trace_id: str, graph: TaskGraph) -> None:
    """T3: checkpoint — reescribe el grafo serializado. Un UPDATE por transición."""
    _update(trace_id, plan=graph.to_dict())


def record_end(trace_id: str, *, outcome: str, state: str = "done",
               result: Optional[str] = None) -> None:
    """Cierra la traza con el resultado. `state` ∈ done|failed|cancelled."""
    _update(trace_id, outcome=outcome, result=result, state=state)


def set_state(trace_id: str, state: str) -> None:
    """Cambia el estado de la traza (running|waiting|done|failed|cancelled). Lo
    usa el executor al pausar en un gate (waiting) o al cancelar."""
    _update(trace_id, state=state)


def load_graph(trace_id: str) -> Optional[TaskGraph]:
    """Recupera el TaskGraph persistido de una traza (T3: reanudación tras gate
    o tras reinicio). None si no hay traza o aún no tiene plan."""
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None or not row.plan:
            return None
        return TaskGraph.from_dict(row.plan)
    except Exception as e:
        logger.error(f"[tracer] load_graph({trace_id}) falló: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def get_meta(trace_id: str) -> Optional[dict]:
    """Metadatos de la traza (mission_id, channel, state) — el executor los
    necesita al reanudar (la Mission de V1.0 es implícita: vive aquí)."""
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None:
            return None
        return {"id": row.id, "mission_id": row.mission_id, "channel": row.channel,
                "state": row.state}
    finally:
        db.close()


def pending_trace_ids() -> list[str]:
    """Trazas sin terminar (running|waiting) — las que `resume_pending()` del
    executor recarga al arrancar el backend (doc 14 §3.4.3)."""
    db = SessionLocal()
    try:
        rows = (
            db.query(OrchestratorTrace)
            .filter(OrchestratorTrace.state.in_(["running", "waiting"]))
            .all()
        )
        return [r.id for r in rows]
    except Exception as e:
        logger.error(f"[tracer] pending_trace_ids falló: {type(e).__name__}: {e}")
        return []
    finally:
        db.close()


def _update(trace_id: str, **fields) -> None:
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None:
            return
        for k, v in fields.items():
            if v is not None:
                setattr(row, k, v)
        row.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.error(f"[tracer] update({trace_id}) falló (no crítico): {type(e).__name__}: {e}")
        db.rollback()
    finally:
        db.close()
