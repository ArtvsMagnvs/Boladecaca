# backend/app/tie/__init__.py — API PÚBLICA del TIE (Task Intelligence Engine)
#
# [doc 16] Disciplina modular: este __init__ ES la API pública del paquete. El
# resto de la app importa SOLO desde `app.tie` — nunca de los internos
# (contracts/runtime/intents/tracer/missions/pipeline, ni de los futuros
# enricher/planner/graph/executor/responder/router). La frontera la vigila
# tests/test_module_boundaries.py.
#
# V1.0 T1: contratos congelados + AgentRuntime/NullRuntime + intent classifier +
# camino corto + tracer/misiones. `handle`/`submit_mission` son la INTERFAZ de
# orquestación: en T4 el Gateway hará `gateway.set_handler(tie.handle)` y el AE/
# WPMS usarán `submit_mission`. En T1 el pipeline resuelve el camino corto y
# degrada el complejo (planner/executor son T2-T4).

# --- Contratos congelados (T1) ---
from app.tie.contracts import (
    NodeState,
    IntentType,
    Intent,
    MEL_CAPABILITIES,
    TaskNode,
    TaskGraph,
    Mission,
)

# --- Interfaz de ejecución (doc 10) + NullRuntime + registro ---
from app.tie.runtime import (
    AgentRuntime,
    AgentTask,
    AgentResult,
    AgentChunk,
    RuntimeHealth,
    NullRuntime,
    register_runtime,
    get_runtime,
    list_runtimes,
)

# --- Clasificación de intención + misiones ---
from app.tie import intents
from app.tie import tracer
from app.tie import executor
from app.tie.missions import new_mission

# --- Pipeline (la interfaz de orquestación) ---
from app.tie.pipeline import handle, submit_mission

# `classify` promovido al top-level por comodidad (lo usan el pipeline y quien
# quiera "entender" un mensaje sin ejecutarlo — p.ej. el AE al decidir delegar).
classify = intents.classify

__all__ = [
    # contratos
    "NodeState",
    "IntentType",
    "Intent",
    "MEL_CAPABILITIES",
    "TaskNode",
    "TaskGraph",
    "Mission",
    # runtime
    "AgentRuntime",
    "AgentTask",
    "AgentResult",
    "AgentChunk",
    "RuntimeHealth",
    "NullRuntime",
    "register_runtime",
    "get_runtime",
    "list_runtimes",
    # intent + misiones + trazas
    "classify",
    "new_mission",
    "tracer",
    # motor de ejecución del grafo (T3): run/cancel/resume_pending/register_gate_handlers
    "executor",
    # pipeline (interfaz de orquestación)
    "handle",
    "submit_mission",
]
