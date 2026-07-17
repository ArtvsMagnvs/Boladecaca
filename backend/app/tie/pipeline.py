# app/tie/pipeline.py — el pipeline del TIE: handle() y submit_mission() (doc 14 §3.3)
#
# LA interfaz de orquestación. Desde T4 es el handler del Gateway
# (`gateway.set_handler(tie.handle)`) y la entrada del AE/WPMS (`submit_mission`).
#
# Flujo completo (doc 14 §3.3):
#   entrada → [clasificar ∥ pre-fetch de contexto]  (en PARALELO, doc 11 B.2)
#     ├─ camino corto (~80%): NullRuntime → respuesta      ← sin planner, sin grafo
#     └─ complejo: planner → TaskGraph validado
#                    ├─ ¿plan sensible? → gate del PLAN (HITL) → pausa
#                    └─ executor.run → responder → respuesta
#
# Firma de `handle` = `MessageHandler` del Gateway (envelope → str). Nunca lanza:
# cualquier fallo degrada a una respuesta útil (regla 11-B).
from __future__ import annotations

import asyncio
from typing import Optional

from app.core.config import settings
from app.core.logging_config import get_system_logger
from app.tie import enricher, executor, intents, planner, responder, tracer
from app.tie.contracts import Intent, Mission, NodeState, TaskGraph
from app.tie.missions import new_mission
from app.tie.runtime import AgentTask, get_runtime

logger = get_system_logger("tie.pipeline")

# action_type del gate del PLAN (distinto del gate de nodo, `tie_resume` — T3).
PLAN_ACTION_TYPE = "tie_plan"


# ---------------------------------------------------------------------------
# Entradas públicas
# ---------------------------------------------------------------------------
async def handle(envelope) -> str:
    """Entrada channel-agnostic. Es el handler que el Gateway usa desde T4: el
    chat de Telegram (y cualquier canal futuro) pasa por aquí."""
    text = getattr(envelope, "text", "") or ""
    channel = getattr(envelope, "channel", None)
    try:
        return await _run_pipeline(text, source="user", channel=channel)
    except Exception as e:  # el Gateway ya hace fail-soft, pero el TIE no delega su honestidad
        logger.error(f"[tie] handle falló de forma inesperada: {type(e).__name__}: {e}")
        return "He tenido un problema interno procesando eso. Inténtalo otra vez."


async def handle_stream(text: str, *, channel: str = "web"):
    """[T4b] Entrada STREAMING — la que usa `/api/chat/stream` (el chat de
    Electron). Emite tuplas `(kind, payload)`:
      ("status", "analizando"|"planificando"|…)  → feedback inmediato (≤1 s, doc 11 B.5)
      ("mission", trace_id)                       → hay una misión que se puede seguir/aprobar
      ("text", token|respuesta)                   → lo que el usuario lee

    El camino corto (~80%) streamea TOKENS de verdad (mismo UX de siempre); el
    complejo emite estados gruesos y la respuesta final del responder — el detalle
    paso a paso, en vivo, se ve en la vista de misión (que sondea el grafo).
    """
    from app.automation import approval_gate
    from app.memory import memory_router
    from app.tools import tool_manager

    yield ("status", "analizando")
    try:
        intent_task = asyncio.create_task(intents.classify(text, channel=channel))
        ctx_task = asyncio.create_task(_prefetch_context(text))
        intent = await intent_task
        prefetched = await ctx_task
    except Exception as e:
        logger.error(f"[tie] handle_stream: clasificación falló: {type(e).__name__}: {e}")
        intent, prefetched = Intent.conversational_fallback(text), ""

    mission = new_mission(goal=intent.goal or text, source="user", channel=channel)
    trace_id = tracer.record_start(mission, channel=channel)
    tracer.record_intent(trace_id, intent)
    tracer.emit_started(mission)

    # --- camino corto: tokens de verdad ---
    if intent.is_short_path:
        acc = ""
        task = AgentTask(id=AgentTask.new_id(), instruction=text, channel=channel,
                         tools=intent.requires_tools)
        runtime = get_runtime("null")
        async for chunk in runtime.stream_task(
            task, memory=memory_router, tools=tool_manager, approval_gate=approval_gate
        ):
            if chunk.kind == "text" and chunk.payload:
                acc += chunk.payload
                yield ("text", chunk.payload)
        tracer.record_end(trace_id, outcome=acc[:2000])
        tracer.emit_completed(mission, ok=bool(acc), nodes=0)
        return

    # --- camino complejo ---
    yield ("status", "planificando")
    yield ("mission", trace_id)
    context = prefetched if not intent.memory_types else await _context_for(intent, text)
    try:
        await _complex_path(text, intent, mission, trace_id, context)
    except Exception as e:
        logger.error(f"[tie] handle_stream: pipeline complejo falló: {type(e).__name__}: {e}")
        mission.outcome = "He tenido un problema procesando eso."
    yield ("text", mission.outcome or "(sin respuesta)")


async def submit_mission(
    goal: str,
    *,
    source: str = "automation",
    channel: Optional[str] = None,
    project_id: Optional[int] = None,
) -> Mission:
    """Entrada PROGRAMÁTICA (AE `AgentTaskAction`, WPMS) — ya sabe que es una
    misión, así que NO hay camino corto: siempre planifica y ejecuta. Devuelve la
    Mission con su `outcome`."""
    mission = new_mission(goal=goal, source=source, channel=channel, project_id=project_id)
    intent = await intents.classify(goal, channel=channel)
    intent.requires_planning = True  # una misión explícita nunca es "charla"
    trace_id = tracer.record_start(mission, channel=channel)
    tracer.record_intent(trace_id, intent)
    tracer.emit_started(mission)

    context = await _context_for(intent, goal)
    await _complex_path(goal, intent, mission, trace_id, context)
    return mission


# ---------------------------------------------------------------------------
# El pipeline
# ---------------------------------------------------------------------------
async def _run_pipeline(text: str, *, source: str, channel: Optional[str]) -> str:
    # [1+2] Clasificar y pre-fetch de contexto EN PARALELO (doc 11 B.2): el
    # enricher no sabe todavía qué tipos pedir, así que hace una consulta general;
    # si el intent pide tipos concretos, el planner/nodo la afinará. Coste: una
    # llamada barata + una consulta al MOS con presupuesto duro, a la vez.
    intent_task = asyncio.create_task(intents.classify(text, channel=channel))
    ctx_task = asyncio.create_task(_prefetch_context(text))
    intent = await intent_task
    prefetched = await ctx_task

    mission = new_mission(goal=intent.goal or text, source=source, channel=channel)
    trace_id = tracer.record_start(mission, channel=channel)
    tracer.record_intent(trace_id, intent)
    tracer.emit_started(mission)

    # [3] Camino corto: ~80% de las queries no pagan planner ni grafo (doc 14 §6).
    if intent.is_short_path:
        out = await _short_path(text, intent, channel)
        tracer.record_end(trace_id, outcome=out[:2000])
        tracer.emit_completed(mission, ok=True, nodes=0)
        return out

    # [4] Complejo: contexto afinado por el intent (si pidió tipos concretos) y a planificar.
    context = prefetched if not intent.memory_types else await _context_for(intent, text)
    await _complex_path(text, intent, mission, trace_id, context)
    return mission.outcome or "(sin respuesta)"


async def _complex_path(
    text: str, intent: Intent, mission: Mission, trace_id: str, context: str
) -> None:
    """planner → (gate del plan) → executor → responder. Escribe `mission.outcome`."""
    graph = await planner.plan(
        intent.goal or text, intent, context=context, mission_id=mission.id, trace_id=trace_id
    )
    if graph is None:
        # El planner no logró un grafo válido ni tras el reintento → degradar al
        # camino corto (regla 11-B: nunca romper; el usuario recibe algo).
        logger.info("[tie] sin plan válido — degradando a camino corto")
        out = await _short_path(text, intent, mission.channel)
        mission.outcome = out[:2000]
        mission.state = "done"
        tracer.record_end(trace_id, outcome=mission.outcome)
        tracer.emit_completed(mission, ok=True, nodes=0)
        return

    mission.graph_ids = [graph.id]

    # ¿El plan toca algo sensible? → se aprueba EL PLAN antes de ejecutar nada
    # (transparencia estilo plan-mode; doc 14 §3.3). Nada se ha ejecutado aún:
    # planificar no tiene side effects (regla 11-B).
    if _needs_plan_approval(graph):
        await _open_plan_gate(graph, mission, trace_id)
        mission.outcome = (
            f"He preparado un plan de {len(graph.nodes)} paso(s) para «{mission.goal}». "
            f"Como toca algo sensible, necesito tu visto bueno antes de ejecutarlo:\n\n"
            f"{responder.plan_summary(graph)}"
        )
        tracer.record_end(trace_id, outcome=mission.outcome, state="waiting")
        return

    graph.state = "approved"
    await _execute_and_respond(graph, mission, trace_id)


async def _execute_and_respond(graph: TaskGraph, mission: Mission, trace_id: str) -> None:
    """Ejecuta el grafo y sintetiza la respuesta. Compartido por el camino normal
    y por la reanudación tras aprobar el plan."""
    await executor.run(graph, mission, trace_id=trace_id)

    if mission.state == "waiting":
        # Un nodo abrió su propio gate (T3): la misión sigue viva en disco; el
        # usuario responderá y el evento la reanudará.
        mission.outcome = "He empezado y estoy esperando tu confirmación para un paso."
        tracer.record_end(trace_id, outcome=mission.outcome, state="waiting")
        return

    out = await responder.build(mission, graph)
    ok = mission.state == "done"
    tracer.record_end(trace_id, outcome=out, state=mission.state)
    if mission.state == "cancelled":
        tracer.emit_cancelled(mission)
    elif ok:
        tracer.emit_completed(mission, ok=True, nodes=len(graph.nodes))
    else:
        tracer.emit_failed(mission)


# ---------------------------------------------------------------------------
# Camino corto
# ---------------------------------------------------------------------------
async def _short_path(text: str, intent: Intent, channel: Optional[str]) -> str:
    """NullRuntime → respuesta. Se pasa por la interfaz AgentRuntime (no por
    chat_service directo): el camino corto ya ejercita el MISMO contrato que
    usará HermesRuntime en V1.1."""
    from app.automation import approval_gate
    from app.memory import memory_router
    from app.tools import tool_manager

    runtime = get_runtime("null")  # V1.1: routing por capabilities
    task = AgentTask(
        id=AgentTask.new_id(), instruction=text, channel=channel, tools=intent.requires_tools,
    )
    result = await runtime.execute_task(
        task, memory=memory_router, tools=tool_manager, approval_gate=approval_gate,
    )
    return result.output or "(sin respuesta)"


async def _prefetch_context(text: str) -> str:
    try:
        return await enricher.enrich(text)
    except Exception:
        return ""


async def _context_for(intent: Intent, fallback_query: str) -> str:
    if not intent.requires_memory and not intent.memory_types:
        return ""
    try:
        return await enricher.enrich(
            intent.context_query or intent.goal or fallback_query,
            memory_types=intent.memory_types or None,
        )
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Gate del PLAN (doc 14 §3.3) — transparencia antes de ejecutar
# ---------------------------------------------------------------------------
def _needs_plan_approval(graph: TaskGraph) -> bool:
    """El plan se aprueba entero cuando toca algo sensible. `TIE_PLAN_APPROVAL`
    permite desactivarlo (entonces cada nodo sensible pide su propio permiso —
    el gate de nodo de T3 sigue ahí)."""
    if not settings.TIE_PLAN_APPROVAL:
        return False
    return any(n.approval_required for n in graph.nodes.values())


async def _open_plan_gate(graph: TaskGraph, mission: Mission, trace_id: str) -> None:
    from app.automation import approval_gate

    gate_id = await approval_gate.request_approval(
        kind="tie.plan",
        title=f"Plan de {len(graph.nodes)} paso(s): {mission.goal[:150]}",
        summary=responder.plan_summary(graph),
        action_type=PLAN_ACTION_TYPE,
        action_payload={"trace_id": trace_id, "mission_id": mission.id},
        channel=mission.channel or "hub",
    )
    graph.state = "draft"
    tracer.update_graph(trace_id, graph)
    tracer.set_state(trace_id, "waiting")
    mission.state = "waiting"
    logger.info(f"[tie] plan de la misión {mission.id} esperando aprobación (gate {gate_id})")


async def _apply_plan_verdict(trace_id: str, approved: bool) -> None:
    """Aplica el veredicto del gate del PLAN. Lo invoca el handler del evento
    `approval.resolved` (en background — nunca dentro del resolve() del gate,
    que vive en un request HTTP; mismo criterio que los gates de nodo, T3)."""
    graph = tracer.load_graph(trace_id)
    meta = tracer.get_meta(trace_id)
    if graph is None or meta is None or graph.state != "draft":
        return  # ya aplicado (idempotencia) o traza inexistente

    mission = Mission(
        id=meta.get("mission_id") or graph.mission_id,
        goal=_goal_from_meta(meta),
        channel=meta.get("channel"),
        state="running",
        graph_ids=[graph.id],
    )

    if not approved:
        graph.state = "cancelled"
        for n in graph.nodes.values():
            n.state = NodeState.CANCELLED
        tracer.update_graph(trace_id, graph)
        mission.state = "cancelled"
        mission.outcome = "He descartado el plan, como pediste. No he ejecutado nada."
        tracer.record_end(trace_id, outcome=mission.outcome, state="cancelled")
        tracer.emit_cancelled(mission)
        return

    # Aprobar el PLAN autoriza sus pasos sensibles: el usuario ha visto la lista
    # completa y ha dicho que sí. Se marca cada nodo con el gate del plan para que
    # el executor NO vuelva a preguntar uno por uno (`node.gate_id is None` es su
    # condición para abrir gate, T3). Queda auditado: cada nodo apunta a la
    # aprobación que lo autorizó.
    plan_gate = _find_plan_gate_id(trace_id)
    for n in graph.nodes.values():
        if n.approval_required and n.gate_id is None:
            n.gate_id = plan_gate
    graph.state = "approved"
    tracer.update_graph(trace_id, graph)
    tracer.set_state(trace_id, "running")
    await _execute_and_respond(graph, mission, trace_id)


def _find_plan_gate_id(trace_id: str, *, only_pending: bool = False) -> Optional[str]:
    """El gate del plan cuyo payload apunta a esta traza (para dejar el enlace de
    auditoría en cada nodo autorizado, y para que la API lo resuelva)."""
    from app.automation import Approval
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        q = db.query(Approval).filter(Approval.action_type == PLAN_ACTION_TYPE)
        if only_pending:
            q = q.filter(Approval.status == "pending")
        for r in q.all():
            if (r.action_payload or {}).get("trace_id") == trace_id:
                return r.id
    except Exception:
        return None
    finally:
        db.close()
    return None


async def resolve_plan(trace_id: str, approved: bool, note: str = "") -> Optional[dict]:
    """API pública para aprobar/rechazar el plan de una misión (la usa
    `/api/tie/missions/{id}/approve-plan`). Resuelve el ApprovalGate del plan; la
    ejecución arranca en background (el POST responde al instante). None si no
    hay plan pendiente para esa misión.

    Vive aquí y no en el endpoint para que la API no tenga que conocer los
    internos del TIE (doc 16: se habla con el módulo por su fachada)."""
    gate_id = _find_plan_gate_id(trace_id, only_pending=True)
    if gate_id is None:
        return None

    from app.automation import approval_gate

    result = await approval_gate.resolve(gate_id, approved, note)
    return {"gate_id": gate_id, "status": result.status, "approved": approved}


def _goal_from_meta(meta: dict) -> str:
    """El goal vive en el intent de la traza (la Mission de V1.0 es implícita)."""
    from app.db.database import OrchestratorTrace, SessionLocal

    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, meta["id"])
        if row and row.intent:
            return row.intent.get("goal", "") or ""
        return ""
    except Exception:
        return ""
    finally:
        db.close()


async def _on_approval_resolved(event) -> None:
    """Handler del bus para el gate del PLAN. Los gates de NODO los atiende el
    executor (T3) — cada uno mira su propio `action_type` y se ignoran mutuamente."""
    payload = event.payload or {}
    if payload.get("action") != PLAN_ACTION_TYPE:
        return
    gate_id = payload.get("gate_id")
    approved = payload.get("resolution") == "approved"
    try:
        from app.automation import approval_gate

        appr = approval_gate.get(gate_id)
        if appr is None:
            return
        trace_id = (appr.action_payload or {}).get("trace_id")
        if trace_id:
            await _apply_plan_verdict(trace_id, approved)
    except Exception as e:
        logger.error(f"[tie] fallo aplicando el veredicto del plan (gate {gate_id}): {e!r}")


async def _plan_gate_executor(payload: dict) -> str:
    """Ejecutor de `tie_plan`. NO ejecuta el plan aquí: la ejecución es
    event-driven (ver `_on_approval_resolved`) para no bloquear el request HTTP
    que resuelve la aprobación. Mismo criterio que `tie_resume` (T3)."""
    return f"plan aprobado; ejecución de la misión {payload.get('mission_id')} en curso"


def register_plan_handlers() -> None:
    """Cablea el gate del PLAN con el ApprovalGate + el bus. Idempotente."""
    from app.automation import approval_gate
    from app.core.events import subscribe, unsubscribe

    approval_gate.register_executor(PLAN_ACTION_TYPE, _plan_gate_executor)
    unsubscribe("approval.resolved", _on_approval_resolved)
    subscribe("approval.resolved", _on_approval_resolved)
