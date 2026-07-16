# app/tie/pipeline.py — el pipeline del TIE: handle() y submit_mission() (doc 14 §3.3)
#
# Es LA interfaz de orquestación: el punto único de entrada que en T4 sustituirá
# al chat handler del Gateway (`gateway.set_handler(tie.handle)`), y que el AE
# (V1.0) / el WPMS usarán vía `submit_mission`. En T1 el flujo está completo para
# el CAMINO CORTO (intent → NullRuntime → respuesta) y deja la rama compleja como
# una degradación honesta hasta que existan planner (T2) y executor (T3/T4).
#
# Firma de `handle` alineada con `MessageHandler` del Gateway (envelope → str) —
# el switch de T4 no necesitará adaptar nada.
from __future__ import annotations

from typing import Optional

from app.core.logging_config import get_system_logger
from app.tie import intents, tracer
from app.tie.contracts import Intent, Mission
from app.tie.missions import new_mission
from app.tie.runtime import AgentTask, get_runtime

logger = get_system_logger("tie.pipeline")


async def handle(envelope) -> str:
    """Entrada channel-agnostic (equivalente del chat handler, con TIE por debajo).
    T1: clasifica y sirve el camino corto; la rama compleja degrada al camino
    corto (planner/executor son T2-T4). Nunca lanza — siempre devuelve texto."""
    text = getattr(envelope, "text", "") or ""
    channel = getattr(envelope, "channel", None)

    intent = await intents.classify(text, channel=channel)
    mission = new_mission(goal=intent.goal or text, source="user", channel=channel)
    trace_id = tracer.record_start(mission, channel=channel)
    tracer.record_intent(trace_id, intent)

    if intent.is_short_path:
        out = await _short_path(text, intent, channel)
        tracer.record_end(trace_id, outcome=out[:2000])
        return out

    # T1: aún no hay planner/executor. Degradación honesta: se responde por el
    # camino corto (el usuario obtiene algo útil) y se deja rastro de que se
    # habría planificado. T4 reemplaza esta rama por planner→graph→executor→responder.
    logger.info(f"[tie] intent complejo (type={intent.type.value}, planning={intent.requires_planning}) "
                f"— T1 degrada a camino corto")
    out = await _short_path(text, intent, channel)
    tracer.record_end(trace_id, outcome=out[:2000], state="done")
    return out


async def submit_mission(
    goal: str,
    *,
    source: str = "automation",
    channel: Optional[str] = None,
    project_id: Optional[int] = None,
) -> Mission:
    """Entrada PROGRAMÁTICA (AE V1.0, WPMS) que ya sabe que es una misión — salta
    el intent classifier. T1: clasifica el goal para poblar el Intent (útil para
    el trace) y responde por el camino corto; T4 planifica y ejecuta de verdad.
    Devuelve la Mission con su `outcome`."""
    mission = new_mission(goal=goal, source=source, channel=channel, project_id=project_id)
    intent = await intents.classify(goal, channel=channel)
    trace_id = tracer.record_start(mission, channel=channel)
    tracer.record_intent(trace_id, intent)

    out = await _short_path(goal, intent, channel)
    tracer.record_end(trace_id, outcome=out[:2000], state="done")
    mission.outcome = out[:2000]
    mission.state = "done"
    return mission


async def _short_path(text: str, intent: Intent, channel: Optional[str]) -> str:
    """El camino corto: NullRuntime → respuesta. Se construye un AgentTask y se
    ejecuta a través de la interfaz AgentRuntime (no se llama a chat_service
    directo) — así el camino corto ya ejercita la MISMA interfaz que usará
    HermesRuntime en V1.1, sin acoplarse a una implementación concreta."""
    from app.automation import approval_gate
    from app.memory import memory_router
    from app.tools import tool_manager

    runtime = get_runtime("null")  # V1.1: routing por capabilities elegirá otro
    task = AgentTask(
        id=AgentTask.new_id(),
        instruction=text,
        channel=channel,
        tools=intent.requires_tools,
    )
    result = await runtime.execute_task(
        task, memory=memory_router, tools=tool_manager, approval_gate=approval_gate,
    )
    return result.output or "(sin respuesta)"
