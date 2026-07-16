# app/tie/planner.py — Task Planner del TIE (doc 11-B §B.1, doc 14 §3.2/§3.4, T2)
#
# Modelo POTENTE (capability "reason", via router). Recibe un goal complejo +
# contexto del MOS y emite un TaskGraph de 2-3 nodos, VALIDADO contra el schema y
# las invariantes de `graph.py` ANTES de que nada se ejecute (planning sin side
# effects, regla 11-B). Toda frontera LLM devuelve JSON validado (patrón 9); un
# grafo inválido se reintenta UNA vez con el error como feedback y, si vuelve a
# fallar, se degrada a None (el caller cae al camino corto — nunca romper).
#
# Registra el plan elegido en la Decision API (best-effort) para que el sistema
# acumule qué planifica y por qué (materia prima del Learner, doc 14 §4.4).
from __future__ import annotations

import uuid
from typing import Optional

from app.ai.reasoning_filter import strip_reasoning
from app.core.logging_config import get_system_logger
from app.tie import graph as graph_mod
from app.tie import router, tracer
from app.tie.contracts import Intent, TaskGraph, TaskNode
from app.tie.intents import _extract_json

logger = get_system_logger("tie.planner")

# Regla de tamaño (doc 14 §3.2): 2-3 nodos por defecto; >5 para una query simple
# es un bug del planner, no una feature. Se pide en el prompt y se avisa si excede.
_MAX_REASONABLE_NODES = 6

_SYSTEM_PROMPT = """Eres el planificador de Aithera. Recibes un OBJETIVO del usuario y su
contexto, y devuelves SOLO un objeto JSON con un plan como grafo de tareas (sin texto
extra, sin markdown).

El plan debe tener entre 2 y 3 nodos (máximo 4 si es realmente necesario). Cada nodo
es un paso VERIFICABLE. Formato:
{
  "nodes": [
    {
      "id": "n1",
      "goal": "objetivo imperativo y verificable de este paso",
      "depends_on": [],
      "tools": [],
      "approval_required": false,
      "model_hint": "fast|smart",
      "context_query": null
    }
  ]
}

Reglas:
- "id" único por nodo (n1, n2, n3...).
- "depends_on": lista de ids de nodos que deben completarse ANTES (define el orden).
  El grafo debe ser acíclico (un nodo no puede depender de sí mismo ni formar ciclos).
- "tools": SOLO herramientas de esta lista disponible: {tools}. Si un paso no usa
  herramientas, deja la lista vacía. NUNCA inventes herramientas.
- "approval_required": true SOLO para acciones sensibles (enviar algo, borrar,
  ejecutar comandos que cambian el sistema). El usuario confirmará esos pasos.
- Prefiere 2-3 nodos. No infles el plan. Devuelve SOLO el JSON."""


def _tools_available() -> list[str]:
    try:
        from app.tools import tool_manager

        return sorted(t["tool_id"] for t in tool_manager.list_tools())
    except Exception:
        return []


def _parse_nodes(data: dict) -> list[TaskNode]:
    """Construye TaskNode desde el JSON del LLM. Tolerante: ignora campos raros,
    exige id + goal. Lanza ValueError si no hay nodos usables (→ reintento)."""
    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("el JSON no trae una lista 'nodes' no vacía")

    nodes: list[TaskNode] = []
    for i, rn in enumerate(raw_nodes):
        if not isinstance(rn, dict):
            continue
        nid = str(rn.get("id") or f"n{i+1}").strip()
        goal = str(rn.get("goal") or "").strip()
        if not goal:
            raise ValueError(f"el nodo {nid!r} no tiene goal")
        depends = rn.get("depends_on")
        depends = [str(d) for d in depends] if isinstance(depends, list) else []
        tools = rn.get("tools")
        tools = [str(t) for t in tools] if isinstance(tools, list) else []
        nodes.append(TaskNode(
            id=nid,
            goal=goal,
            depends_on=depends,
            tools=tools,
            approval_required=bool(rn.get("approval_required")),
            model_hint=(str(rn["model_hint"]) if rn.get("model_hint") else None),
            context_query=(str(rn["context_query"]) if rn.get("context_query") else None),
        ))
    if not nodes:
        raise ValueError("ningún nodo usable en 'nodes'")
    return nodes


async def _generate_graph(goal: str, context: str, mission_id: str,
                          feedback: Optional[str] = None) -> tuple[Optional[TaskGraph], str, Optional[str]]:
    """Una pasada del planner: pide el grafo, lo parsea, lo construye y valida.
    Devuelve (graph|None, motivo, model_used). `feedback` (del intento previo) se
    añade al prompt para que el LLM corrija."""
    tools = _tools_available()
    system = _SYSTEM_PROMPT.replace("{tools}", str(tools))
    user = f"OBJETIVO: {goal}"
    if context:
        user += f"\n\nCONTEXTO (memoria de Aithera):\n{context}"
    if feedback:
        user += f"\n\nEl plan anterior fue INVÁLIDO por: {feedback}\nCorrígelo y devuelve SOLO el JSON válido."

    result = await router.complete(user, system_prompt=system, capability="reason")
    model_used = result.get("model")
    if result.get("error"):
        return None, f"el modelo devolvió error: {result.get('response','')[:120]}", model_used

    raw = strip_reasoning(result.get("response", "") or "")
    data = _extract_json(raw)
    if not data:
        return None, "la respuesta no contenía un JSON parseable", model_used

    try:
        nodes = _parse_nodes(data)
    except ValueError as e:
        return None, str(e), model_used

    if len(nodes) > _MAX_REASONABLE_NODES:
        return None, f"demasiados nodos ({len(nodes)}); un plan debe tener 2-3 (máx 4)", model_used

    g = graph_mod.build(mission_id, nodes, created_by="planner")
    ok, reason = graph_mod.validate(g)
    if not ok:
        return None, reason, model_used
    return g, "ok", model_used


async def plan(
    goal: str,
    intent: Intent,
    *,
    context: str = "",
    mission_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Optional[TaskGraph]:
    """Planifica un objetivo complejo → TaskGraph validado, o None si no se pudo
    (el caller degrada a camino corto). 1 reintento con feedback ante grafo
    inválido (doc 14 §3.4.1). Registra el plan en Decision API + tracer (best-effort).
    """
    mission_id = mission_id or uuid.uuid4().hex

    g, reason, model_used = await _generate_graph(goal, context, mission_id)
    if g is None:
        logger.info(f"[planner] grafo inválido, 1 reintento. Motivo: {reason}")
        g, reason, model_used = await _generate_graph(goal, context, mission_id, feedback=reason)

    if g is None:
        logger.info(f"[planner] plan no válido tras reintento — se degradará a camino corto. Motivo: {reason}")
        return None

    # Registro en Decision API (best-effort) + tracer.
    decision_id = await _record_decision(goal, g, intent, mission_id)
    if trace_id:
        tracer.record_plan(trace_id, g, decision_id=decision_id)
    if model_used:
        logger.info(f"[planner] plan de {len(g.nodes)} nodos generado (modelo={model_used})")
    return g


async def _record_decision(goal: str, g: TaskGraph, intent: Intent, mission_id: str) -> Optional[str]:
    """Escribe el plan en la Decision API (SQL `decisions` + espejo). Best-effort:
    un fallo aquí no invalida el plan ya construido."""
    try:
        from app.services import decision_service

        steps = "; ".join(f"{n.id}: {n.goal}" for n in g.nodes.values())
        decision = await decision_service.store_decision(
            title=f"Plan TIE: {goal[:120]}",
            body=steps[:1500],
            reason=f"intent={intent.type.value}, {len(g.nodes)} nodos",
            impact="med",
            mission_id=mission_id,
        )
        return decision.id
    except Exception as e:
        logger.error(f"[planner] no se pudo registrar la decisión del plan (no crítico): {type(e).__name__}: {e}")
        return None
