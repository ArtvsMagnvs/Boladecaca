# app/api/endpoints/tie.py — API del Task Intelligence Engine (V1.0, T4)
#
# Superficie que consume el frontend (T4b): listar misiones, ver el grafo de una
# misión con el estado de cada paso, cancelarla (kill-switch) y aprobar/rechazar
# un plan pendiente.
#
# La misión de V1.0 es IMPLÍCITA (doc 14 §3.6): 1 misión = 1 grafo = 1 fila de
# `orchestrator_traces`. Por eso estos endpoints hablan de trazas por dentro y de
# misiones por fuera — cuando V1.2 traiga la tabla `missions`, el contrato
# público de estos endpoints no cambia.
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.database import OrchestratorTrace, SessionLocal
from app.tie import executor, resolve_plan, tracer

router = APIRouter(prefix="/tie", tags=["tie"])


def _mission_out(row: OrchestratorTrace, *, with_graph: bool = False) -> dict:
    intent = row.intent or {}
    out = {
        "mission_id": row.mission_id,
        "trace_id": row.id,
        "goal": intent.get("goal") or "",
        "type": intent.get("type"),
        "channel": row.channel,
        "state": row.state,
        "outcome": row.outcome,
        "model_used": row.model_used,
        "decision_id": row.decision_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "node_count": len((row.plan or {}).get("nodes", {})) if row.plan else 0,
    }
    if with_graph:
        out["intent"] = intent
        out["graph"] = row.plan
    return out


@router.get("/missions")
def list_missions(
    state: Optional[str] = Query(None, description="running|waiting|done|failed|cancelled"),
    limit: int = Query(30, ge=1, le=200),
):
    """Misiones recientes (las que esperan aprobación primero — son las que piden
    algo del usuario)."""
    db = SessionLocal()
    try:
        q = db.query(OrchestratorTrace)
        if state:
            q = q.filter(OrchestratorTrace.state == state)
        rows = q.order_by(OrchestratorTrace.created_at.desc()).limit(limit).all()
        out = [_mission_out(r) for r in rows]
        out.sort(key=lambda m: 0 if m["state"] == "waiting" else 1)
        return out
    finally:
        db.close()


@router.get("/missions/{trace_id}")
def get_mission(trace_id: str):
    """Una misión con su grafo completo: los pasos y el estado de cada uno."""
    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, trace_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Mission not found")
        return _mission_out(row, with_graph=True)
    finally:
        db.close()


@router.post("/missions/{trace_id}/cancel")
def cancel_mission(trace_id: str):
    """Kill-switch (doc 14 §3.4.6): para la misión. El nodo en vuelo recibe
    cancelación cooperativa; el resto queda CANCELLED."""
    meta = tracer.get_meta(trace_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    if meta["state"] in ("done", "failed", "cancelled"):
        return {"trace_id": trace_id, "state": meta["state"], "cancelled": False,
                "detail": "la misión ya había terminado"}
    executor.cancel(meta["mission_id"])
    return {"trace_id": trace_id, "mission_id": meta["mission_id"], "cancelled": True}


class PlanVerdict(BaseModel):
    approved: bool
    note: str = ""


@router.post("/missions/{trace_id}/approve-plan")
async def approve_plan(trace_id: str, payload: PlanVerdict):
    """Aprueba o rechaza el PLAN de una misión que espera visto bueno. La
    ejecución arranca en background (el POST responde al instante aunque el grafo
    tarde minutos). La lógica vive en el TIE (`tie.resolve_plan`); aquí solo se
    traduce a HTTP."""
    result = await resolve_plan(trace_id, payload.approved, payload.note)
    if result is None:
        raise HTTPException(status_code=404, detail="No hay un plan pendiente de aprobación para esta misión")
    return {"trace_id": trace_id, **result}
