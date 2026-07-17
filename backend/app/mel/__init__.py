# backend/app/mel/__init__.py — API PÚBLICA del MEL (Model Execution Layer)
#
# [doc 16] Disciplina modular: este __init__ ES la API pública del paquete. El
# resto de la app importa SOLO desde `app.mel` — nunca de los internos
# (contracts/registry/decision/policies/fallback/executor/catalog/capabilities/
# models). La frontera la vigila tests/test_module_boundaries.py. En particular,
# NADIE fuera de `app.mel` importa `ai_manager` ni providers: solo `registry.py`
# lo hace (doc 19 §1.2).
#
# V1.0 E1: contratos congelados + registry (envuelve ai_manager) + Rule Engine +
# fallback/breakers + compilador de políticas. El resto del sistema NO llama
# todavía al MEL (el switch de `tie/router.py` y los ~9 call-sites es E2).
from __future__ import annotations

from typing import Optional

# --- Contratos congelados (E1) ---
from app.mel.contracts import (
    Capability,
    PolicyName,
    ModelRef,
    Constraints,
    ExecutionRequest,
    ExecutionResult,
    ServedBy,
    Usage,
    DecisionTrace,
)

# --- Internos (para exponer funciones públicas; no se re-exportan los módulos) ---
from app.mel import executor as _executor
from app.mel import decision as _decision
from app.mel import registry as _registry
from app.mel.policies import policy_store as _policy_store


# ---------------------------------------------------------------------------
# API pública (doc 19 §1.2 / §2)
# ---------------------------------------------------------------------------
async def complete(req: ExecutionRequest) -> ExecutionResult:
    """Ejecuta una petición de capacidad y devuelve el resultado. El caller pide
    QUÉ (capability), el MEL decide CON QUÉ MODELO. Nunca lanza."""
    return await _executor.complete(req)


def stream(req: ExecutionRequest):
    """Igual que complete pero streaming (AsyncIterator[str] de texto ya filtrado)."""
    return _executor.stream(req)


def decision_trace(decision_id: str) -> Optional[DecisionTrace]:
    """La traza de una decisión reciente (por qué se eligió ese modelo)."""
    return _decision.get_trace(decision_id)


def recent_decisions(limit: int = 50) -> list[DecisionTrace]:
    """Las decisiones más recientes (observabilidad — pantalla Actividad, v2)."""
    return _decision.recent_traces(limit)


def policies() -> list[dict]:
    """Las políticas compiladas (Economy/Quality/Offline) con su estado."""
    return _policy_store.list_policies()


def set_active_policy(name: str) -> bool:
    """Cambia la política activa (Settings → Inteligencia). True si existía."""
    return _policy_store.set_active(name)


def resolve_model_name(text: str) -> Optional[ModelRef]:
    """Resuelve un nombre coloquial de modelo al (provider, model) configurado, o
    None. La usa el TIE (E2b) para el override explícito del usuario (doc 19 §7b.2)."""
    return _registry.resolve_model_name(text)


def ensure_ready() -> None:
    """Compila las políticas si no existen (idempotente). Lo llama el wizard (O5)
    o, de forma defensiva, cualquier `complete()`. Seguro llamarlo en el lifespan."""
    _policy_store.ensure_compiled(_registry.list_available())


__all__ = [
    # contratos
    "Capability", "PolicyName", "ModelRef", "Constraints",
    "ExecutionRequest", "ExecutionResult", "ServedBy", "Usage", "DecisionTrace",
    # API pública
    "complete", "stream", "decision_trace", "recent_decisions",
    "policies", "set_active_policy", "resolve_model_name", "ensure_ready",
]
