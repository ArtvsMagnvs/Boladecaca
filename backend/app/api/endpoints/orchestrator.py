# app/api/endpoints/orchestrator.py — runs de orquestación (V1.0, R2)
#
# Un "run" es lo que Aithera hizo con UN mensaje del usuario que contenía varios
# encargos: qué objetivos identificó, qué misión resolvió cada uno y en qué
# estado quedó. Es lo que la UI necesita para enseñar el árbol de trabajo.
from __future__ import annotations

import app.orchestrator as orchestrator
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.get("/runs")
def list_runs(limit: int = 30):
    """Runs recientes; los que siguen en marcha, primero."""
    return {"runs": orchestrator.recent_runs(limit)}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    """Un run con todos sus objetivos: estado, dependencias y la misión que
    resolvió cada uno (para enlazar con la vista de Misiones)."""
    run = orchestrator.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run no encontrado: {run_id}")
    return run


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str):
    """Para el run: no se lanzan más objetivos. Los que ya están en vuelo los
    corta el kill-switch del TIE."""
    if not orchestrator.cancel_run(run_id):
        raise HTTPException(status_code=409, detail="el run no está en marcha")
    return {"run_id": run_id, "cancelled": True}
