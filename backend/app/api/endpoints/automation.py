# app/api/endpoints/automation.py — API del Automation Engine (V0.9)
#
# A1: superficie mínima del ApprovalGate para que el Hub liste y resuelva
# aprobaciones pendientes (el Hub NO recibe push — sondea GET /approvals). La UI
# de reglas/historial y la lista por proyecto llegan en A3; aquí sólo el gate.
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.automation import Approval, approval_gate

router = APIRouter(prefix="/automation", tags=["automation"])


def _approval_out(a: Approval) -> dict:
    """Serializa una aprobación para la UI (sin exponer el action_payload crudo —
    puede llevar detalles internos; la UI muestra title/summary)."""
    return {
        "gate_id": a.id,
        "kind": a.kind,
        "title": a.title,
        "summary": a.summary,
        "action_type": a.action_type,
        "status": a.status,
        "channel": a.channel,
        "requested_at": a.requested_at.isoformat() if a.requested_at else None,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
    }


@router.get("/approvals")
def list_approvals():
    """Aprobaciones pendientes (las que el Hub debe mostrar para resolver)."""
    return [_approval_out(a) for a in approval_gate.list_pending()]


@router.get("/approvals/{gate_id}")
def get_approval(gate_id: str):
    a = approval_gate.get(gate_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return _approval_out(a)


class ResolvePayload(BaseModel):
    approved: bool
    note: str = ""


@router.post("/approvals/{gate_id}/resolve")
async def resolve_approval(gate_id: str, payload: ResolvePayload):
    """Aprueba (ejecuta la acción) o rechaza (la descarta). Idempotente: resolver
    dos veces no re-ejecuta. Escribe en la Decision API y emite approval.resolved."""
    result = await approval_gate.resolve(gate_id, payload.approved, payload.note)
    if result.status == "not_found":
        raise HTTPException(status_code=404, detail="Approval not found")
    return {
        "gate_id": result.gate_id,
        "status": result.status,
        "executed": result.executed,
        "result": result.result,
        "error": result.error,
    }
