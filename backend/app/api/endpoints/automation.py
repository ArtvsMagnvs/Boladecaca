# app/api/endpoints/automation.py — API del Automation Engine (V0.9)
#
# A1: superficie del ApprovalGate (aprobaciones pendientes, el Hub sondea — no
# recibe push). A3: reglas (listar + activar/desactivar EN CALIENTE, sin
# reiniciar el backend) + historial de ejecuciones, para la UI de
# Automatizaciones y el stub por proyecto de ProjectCard.tsx (Δ10).
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.automation import Approval, AutomationExecution, AutomationRule, approval_gate, automation_engine

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


# ---------------------------------------------------------------------------
# Reglas (A3) — lista/activar-desactivar. Sin CRUD completo todavía: las 5
# predefinidas se siembran en el arranque (rules_builtin.py) y se editan
# directo en BD hasta que haga falta más (YAGNI — nada lo pide aún).
# ---------------------------------------------------------------------------
def _rule_out(r: AutomationRule) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "enabled": r.enabled,
        "trigger_type": r.trigger_type,
        "trigger_config": r.trigger_config,
        "condition_config": r.condition_config,
        "action_type": r.action_type,
        "action_config": r.action_config,
        "project_id": r.project_id,
        "cooldown_s": r.cooldown_s,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("/rules")
def list_rules(project_id: Optional[int] = Query(None)):
    """Todas las reglas, opcionalmente filtradas por proyecto (Δ10: la sección
    "Automatizaciones" de ProjectCard.tsx pide `project_id=<el suyo>`)."""
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        q = db.query(AutomationRule)
        if project_id is not None:
            q = q.filter(AutomationRule.project_id == project_id)
        rows = q.order_by(AutomationRule.id.asc()).all()
        return [_rule_out(r) for r in rows]
    finally:
        db.close()


class RuleTogglePayload(BaseModel):
    enabled: bool


@router.patch("/rules/{rule_id}")
def toggle_rule(rule_id: int, payload: RuleTogglePayload):
    """Activa/desactiva una regla EN CALIENTE (arma/desarma el trigger en el
    motor sin reiniciar el backend) — el toggle HITL que pide la UI."""
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        rule = db.get(AutomationRule, rule_id)
        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        rule.enabled = payload.enabled
        db.commit()
        db.refresh(rule)
        out = _rule_out(rule)
    finally:
        db.close()

    if payload.enabled:
        automation_engine.arm_rule(out["id"], out["trigger_type"], out["trigger_config"] or {})
    else:
        automation_engine.disarm_rule(out["id"])
    return out


@router.get("/executions")
def list_executions(rule_id: Optional[int] = Query(None), limit: int = Query(50, ge=1, le=200)):
    """Historial de ejecuciones — global o de una regla concreta (recientes primero)."""
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        q = db.query(AutomationExecution)
        if rule_id is not None:
            q = q.filter(AutomationExecution.rule_id == rule_id)
        rows = q.order_by(AutomationExecution.id.desc()).limit(limit).all()
        return [
            {
                "id": e.id,
                "rule_id": e.rule_id,
                "trigger_source": e.trigger_source,
                "event_key": e.event_key,
                "status": e.status,
                "result": e.result,
                "error": e.error,
                "duration_ms": e.duration_ms,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in rows
        ]
    finally:
        db.close()
