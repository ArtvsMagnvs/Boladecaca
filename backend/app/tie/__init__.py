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
from app.tie import responder
from app.tie import conversation
from app.tie.missions import new_mission

# --- Pipeline (la interfaz de orquestación) ---
from app.tie.pipeline import handle, handle_stream, submit_mission, resolve_plan, register_plan_handlers

# --- Mapa de capacidades (R6, doc 23): lo que Aithera sabe hacer, generado
# desde el catálogo real. `chat_service.py` lo consume vía esta API pública. ---
from app.tie.capabilities_map import summary as capabilities_summary

# --- Orquestador de proyecto (R4 + hotfix 2026-08-02) ---
# `app.tie.authority` es INTERNO del TIE (lo vigila test_module_boundaries), así
# que el chat del proyecto (capa API) llega a él por aquí. `ensure_orchestrator`
# es lo que hace que "cada proyecto tiene su orquestador" deje de ser solo una
# columna en la BD y pase a existir de verdad.
from app.tie.authority import (ensure_orchestrator, orchestrator_of,
                               orchestrator_tools)


def register_handlers() -> None:
    """Cablea el TIE con el ApprovalGate y el bus de eventos: gates de NODO
    (executor, T3) + gate del PLAN (pipeline, T4) + reporte de misiones en
    segundo plano (conversation, A·VOZ-4). Lo llama el `lifespan`. Idempotente."""
    executor.register_gate_handlers()
    register_plan_handlers()
    conversation.register_handlers()

# `classify` promovido al top-level por comodidad (lo usan el pipeline y quien
# quiera "entender" un mensaje sin ejecutarlo — p.ej. el AE al decidir delegar).
classify = intents.classify
# [A·VOZ-6] El pre-clasificador determinista (0 LLM) también se expone: el
# Orquestador lo usa para NO mostrar "analizando" ni pagar el round-trip del
# clasificador en la charla obvia (una charla no debe parecer una misión).
fast_precheck = intents.fast_precheck
# [2026-07-24] Respuesta determinista sobre los datos propios (proyectos,
# agentes, reglas, tareas): SQL + plantilla, 0 LLM, 0 alucinación. El
# Orquestador la consulta ANTES de clasificar.
from app.tie import quick_answers as _quick_answers  # noqa: E402
quick_answer = _quick_answers.try_answer
# [PU4, doc 35] Hermano async: el Orquestador lo consulta ANTES de emitir
# "analizando" y de clasificar — mismo criterio que `quick_answer`, pero
# la respuesta puede requerir I/O async (leer la locución cacheada del MOS).
quick_answer_async = _quick_answers.try_answer_async
# [PU10, doc 35] Mini-chat de memoria ("guarda esto en la memoria...", "busca
# en la memoria...", "olvida esto de la memoria..."): vive en `app.memory`
# (dominio de memoria, no del TIE) — se re-expone aquí para que el
# Orquestador (que solo conoce la API pública de `app.tie`, nunca importa
# `app.memory` directo) lo consulte con el mismo criterio que el briefing.
# Con ancla obligatoria: "guárdame un resumen" (NEW-7b, un archivo) no debe
# confundirse con esto.
from app.memory import quick_memory as _quick_memory  # noqa: E402
quick_memory_answer_async = _quick_memory.try_answer_async
# [C·WEB-3, doc 32] El bucle agentic de NAVEGACIÓN: observar la página →
# elegir por índice → actuar → repetir. Se expone como `browse` (el módulo
# `webloop` es interno, igual que `toolloop`). Lo usa `browser_tool.browse`,
# que es la puerta por la que el TIE general llega a la navegación profunda.
from app.tie import webloop as _webloop  # noqa: E402
browse = _webloop.run

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
    "fast_precheck",
    "quick_answer",
    "quick_answer_async",
    "quick_memory_answer_async",
    "new_mission",
    "tracer",
    # motor de ejecución del grafo (T3): run/cancel/resume_pending/register_gate_handlers
    "executor",
    # response builder (T4)
    "responder",
    # pipeline (interfaz de orquestación)
    "handle",
    "handle_stream",
    "submit_mission",
    "resolve_plan",
    "register_handlers",
    # mapa de capacidades (R6)
    "capabilities_summary",
    # orquestador de proyecto (R4 + hotfix 2026-08-02)
    "ensure_orchestrator",
    "orchestrator_of",
    "orchestrator_tools",
    # bucle agentic de navegación web (C·WEB-3)
    "browse",
]
