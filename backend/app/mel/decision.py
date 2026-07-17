# app/mel/decision.py — Rule Engine (doc 19 §9.1, E1)
#
# La decisión en tiempo real: qué modelo ejecuta esta petición. DETERMINISTA, sin
# LLM, sin I/O — todo el estado (cadena compilada de la política, breakers) llega
# por parámetro. Coste < 1 ms (doc 19 §6). Explicable: produce un DecisionTrace.
#
# Por qué reglas y no "un LLM decide qué LLM": una decisión por-request con LLM
# costaría 300-2000 ms y dinero, sería irreproducible y acoplaría el selector a un
# proveedor (¿quién decide si el decisor está caído?). Con reglas: microsegundos,
# coste cero, depurable (doc 19 §9).
#
# Precedencia (doc 19 §9.1 con el delta de §7b): override explícito del usuario >
# pin de proyecto > cadena de la política. En E1 la rama de override está escrita
# pero INACTIVA (nadie pasa `forced` todavía — lo hará E2b); cero coste.
from __future__ import annotations

from collections import deque
from typing import Callable, Optional

from app.mel.contracts import DecisionTrace, ExecutionRequest, ModelRef

# Ring buffer de trazas recientes — consultable vía mel.decision_trace(id).
_TRACES: deque[DecisionTrace] = deque(maxlen=500)


def decide(
    req: ExecutionRequest,
    chain: list[ModelRef],
    is_viable: Callable[[ModelRef], bool],
    *,
    forced: Optional[ModelRef] = None,
    forced_origin: str = "policy",
) -> DecisionTrace:
    """Elige el primer candidato VIABLE de la cadena (breaker cerrado). Si `forced`
    está presente (override explícito del usuario o pin de proyecto — E2b), la
    cadena se reduce a él: o es viable, o la decisión queda sin `chosen`
    (`ExplicitModelUnavailable` lo maneja el executor — NUNCA se sustituye en
    silencio una elección explícita, doc 19 §7b.1).

    Registra la traza en el ring buffer y la devuelve. Determinista."""
    if forced is not None:
        effective = [forced]
        origin = forced_origin
    else:
        effective = list(chain)
        origin = "policy"

    trace = DecisionTrace(
        capability=req.capability.value,
        policy=req.policy_override or "active",
        chain=[r.key for r in effective],
        origin=origin,
    )

    for ref in effective:
        if is_viable(ref):
            trace.chosen = ref.key
            break
        trace.skipped.append((ref.key, "no_viable (breaker abierto o no disponible)"))

    _TRACES.appendleft(trace)
    return trace


def get_trace(decision_id: str) -> Optional[DecisionTrace]:
    """Recupera una traza reciente por id (observabilidad, doc 19 §9.1)."""
    for t in _TRACES:
        if t.id == decision_id:
            return t
    return None


def recent_traces(limit: int = 50) -> list[DecisionTrace]:
    """Las trazas más recientes (la más nueva primero)."""
    return list(_TRACES)[:limit]


def ref_from_key(key: str, available: list[ModelRef]) -> Optional[ModelRef]:
    """Recupera el ModelRef cuyo `.key` coincide, dentro de los disponibles."""
    for ref in available:
        if ref.key == key:
            return ref
    return None
