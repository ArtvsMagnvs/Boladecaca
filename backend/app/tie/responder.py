# app/tie/responder.py — Response Builder (doc 11-B §B.1 #5, doc 14 §3.3, T4)
#
# La última etapa: convierte el estado final del grafo en UNA respuesta para el
# usuario, por el canal que sea (channel-agnostic — el Gateway la entrega).
#
# Regla de oro heredada del summarizer (V0.85 M3): **nunca se rompe**. Si el LLM
# falla, hay una plantilla determinista. El usuario SIEMPRE recibe algo útil.
#
# Degradación graciosa (doc 14 §3.4.5): si parte del grafo falló, se entrega lo
# conseguido Y se explica lo que no — jamás se finge éxito total.
from __future__ import annotations

from typing import Optional

from app.ai.reasoning_filter import strip_reasoning
from app.core.logging_config import get_system_logger
from app.tie import router
from app.tie.contracts import Mission, NodeState, TaskGraph

logger = get_system_logger("tie.responder")

_SYSTEM_PROMPT = """Eres Aithera respondiendo al usuario tras completar una tarea.
Recibes el objetivo y los resultados de cada paso ejecutado. Redacta UNA respuesta
natural, directa y breve (2-4 frases) que le cuente al usuario QUÉ se ha conseguido.

Reglas: habla en primera persona, sin tecnicismos internos (no menciones "nodos",
"grafo" ni "pasos del plan"); no inventes nada que no esté en los resultados; si
algo no se pudo hacer, dilo con naturalidad. No uses markdown."""


async def build(mission: Mission, graph: TaskGraph) -> str:
    """Sintetiza el `outcome` de la misión. Escribe `mission.outcome` y lo devuelve."""
    done = [n for n in graph.nodes.values() if n.state == NodeState.DONE]
    failed = [n for n in graph.nodes.values() if n.state == NodeState.FAILED]
    skipped = [n for n in graph.nodes.values() if n.state == NodeState.SKIPPED]
    cancelled = [n for n in graph.nodes.values() if n.state == NodeState.CANCELLED]

    if cancelled and not done:
        text = "He parado la tarea antes de completar ningún paso, como pediste."
    elif not done:
        text = _template_failure(mission, failed)
    else:
        text = await _synthesize(mission, done, failed, skipped, cancelled)

    mission.outcome = text[:2000]
    return mission.outcome


async def _synthesize(mission, done, failed, skipped, cancelled) -> str:
    """Redacta con el modelo (capacidad `summarize` — barata: resumir sin
    inventar, doc 19 §3). Si el modelo falla o devuelve vacío → plantilla."""
    results = "\n".join(f"- {n.goal}: {_node_output(n)}" for n in done)
    problems = ""
    if failed or skipped or cancelled:
        lines = [f"- {n.goal}: {n.error or 'no se completó'}" for n in failed]
        lines += [f"- {n.goal}: no se intentó (dependía de un paso que falló)" for n in skipped]
        lines += [f"- {n.goal}: cancelado" for n in cancelled]
        problems = "\n\nLo que NO se pudo hacer:\n" + "\n".join(lines)

    prompt = f"Objetivo del usuario: {mission.goal}\n\nResultados:\n{results}{problems}"
    try:
        res = await router.complete(prompt, system_prompt=_SYSTEM_PROMPT, capability="summarize")
        if not res.get("error"):
            text = strip_reasoning(res.get("response", "") or "").strip()
            if text:
                return text
    except Exception as e:
        logger.error(f"[responder] síntesis falló, se usa plantilla: {type(e).__name__}: {e}")

    return _template_success(mission, done, failed, skipped, cancelled)


def _node_output(n) -> str:
    if n.result and isinstance(n.result, dict):
        out = n.result.get("output")
        if out:
            return str(out)[:600]
        return str(n.result)[:600]
    return "hecho"


def _template_success(mission, done, failed, skipped, cancelled) -> str:
    """Plantilla determinista (sin LLM). Fea pero honesta: nunca deja al usuario
    sin respuesta porque el modelo esté caído."""
    parts = [f"He completado {len(done)} paso(s) de «{mission.goal}»:"]
    parts += [f"• {n.goal}: {_node_output(n)}" for n in done]
    if failed:
        parts.append("No pude completar: " + "; ".join(f"{n.goal} ({n.error or 'error'})" for n in failed))
    if skipped:
        parts.append("Y quedaron sin intentar: " + "; ".join(n.goal for n in skipped))
    if cancelled:
        parts.append("Cancelaste: " + "; ".join(n.goal for n in cancelled))
    return "\n".join(parts)


def _template_failure(mission, failed) -> str:
    if not failed:
        return f"No he podido avanzar con «{mission.goal}»."
    reasons = "; ".join(f"{n.goal} ({n.error or 'error'})" for n in failed)
    return f"No he podido completar «{mission.goal}». Falló: {reasons}"


def plan_summary(graph: TaskGraph) -> str:
    """Resumen legible del plan para la UI de aprobación (T4b) y para el gate
    del plan: los pasos en orden topológico aproximado, marcando los sensibles."""
    lines = []
    for i, node in enumerate(graph.nodes.values(), 1):
        mark = " (pide permiso)" if node.approval_required else ""
        lines.append(f"{i}. {node.goal}{mark}")
    return "\n".join(lines)
