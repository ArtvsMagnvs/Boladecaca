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


from app.ai.reasoning_filter import strip_reasoning
from app.core import grounding
from app.core.logging_config import get_system_logger
from app.core.strings import t as _t
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
        text = _t("responder.stopped_no_steps")
    elif not done:
        text = _template_failure(mission, failed)
    else:
        text = await _synthesize(mission, done, failed, skipped, cancelled, graph)
        # [S11, doc 34 §S11] Cubre TANTO la síntesis del LLM como su respaldo
        # (`_template_success`, que `_synthesize` usa internamente si el LLM
        # falla o no está fundamentado) — un solo punto en vez de duplicar la
        # nota en las dos funciones.
        text = _with_limitations_note(text, done)

    mission.outcome = text[:2000]
    return mission.outcome


def _gate_really_open(graph: TaskGraph) -> bool:
    """¿Hay de verdad un paso esperando el visto bueno del usuario?

    La fuente es el GRAFO, que el executor persiste en cada transición (T3): si
    un nodo espera aprobación, está ahí. No se consulta la tabla `approvals`
    a propósito — sería una query extra en el camino de respuesta para saber lo
    que el grafo ya sabe."""
    return any(n.state == NodeState.WAITING_APPROVAL for n in graph.nodes.values())


async def _synthesize(mission, done, failed, skipped, cancelled, graph) -> str:
    """Redacta con el modelo (capacidad `summarize` — barata: resumir sin
    inventar, doc 19 §3). Si el modelo falla o devuelve vacío → plantilla.

    [S2·S6, doc 34] El texto del modelo pasa por una COMPROBACIÓN antes de
    salir. El prompt ya pedía "no inventes nada que no esté en los resultados"
    y aun así el 25-jul esta capa escribió "necesito tu confirmación" sobre un
    email YA ENVIADO: leyó la etiqueta "pide permiso" del plan y la interpretó
    como estado pendiente. Una instrucción no es una comprobación."""
    results = "\n".join(f"- {n.goal}: {_node_output(n)}" for n in done)
    problems = ""
    if failed or skipped or cancelled:
        lines = [f"- {n.goal}: {n.error or 'no se completó'}" for n in failed]
        lines += [f"- {n.goal}: no se intentó (dependía de un paso que falló)" for n in skipped]
        lines += [f"- {n.goal}: cancelado" for n in cancelled]
        problems = "\n\nLo que NO se pudo hacer:\n" + "\n".join(lines)

    prompt = f"Objetivo del usuario: {mission.goal}\n\nResultados:\n{results}{problems}"
    # [I18N-9] El resumen de la misión sale en el idioma de interfaz elegido (si
    # lo hay). Si no hay idioma elegido, se mantiene el default histórico
    # (español, el idioma del propio _SYSTEM_PROMPT). Best-effort.
    system = _SYSTEM_PROMPT
    try:
        from app.core.language import language_directive

        directive = language_directive()
        if directive:
            system = f"{_SYSTEM_PROMPT}\n\n{directive}"
    except Exception as e:
        logger.info(f"[responder] no se pudo resolver el idioma (uso el default): {e!r}")
    try:
        res = await router.complete(prompt, system_prompt=system, capability="summarize")
        if not res.get("error"):
            text = strip_reasoning(res.get("response", "") or "").strip()
            if text and _is_grounded(text, graph):
                return text
    except Exception as e:
        logger.error(f"[responder] síntesis falló, se usa plantilla: {type(e).__name__}: {e}")

    return _template_success(mission, done, failed, skipped, cancelled)


def _is_grounded(text: str, graph) -> bool:
    """¿El texto del modelo se sostiene sobre lo que de verdad pasó? Si no, se
    descarta y sale la plantilla determinista — fea, pero incapaz de mentir.

    UNA comprobación: que no diga que falta el visto bueno del usuario si
    ningún paso lo está esperando (el email del 25-jul). No hace falta una
    segunda para "afirma una acción sin ningún paso hecho": `build()` ya desvía
    a `_template_failure` cuando no hay nodos DONE, así que aquí siempre hay al
    menos un paso completado de verdad detrás del texto."""
    if grounding.claims_pending_approval(text) and not _gate_really_open(graph):
        logger.info("[responder] descartado: el texto dice que falta aprobación y no hay "
                    f"ningún paso esperándola — se usa la plantilla. Texto: {text[:200]!r}")
        return False
    return True


def _limitations_of(done) -> list[str]:
    """[S11, doc 34 §S11] tool_ids que algún paso COMPLETADO pidió pero no se
    le concedieron (`node.result['limitations']`, escrito por el executor
    desde `AgentResult.limitations`/`ToolLoopResult.limitations`). Dedup
    preservando el orden de aparición — puede repetirse entre nodos."""
    vistas: list[str] = []
    for n in done:
        if isinstance(n.result, dict):
            for tool_id in n.result.get("limitations") or []:
                if tool_id not in vistas:
                    vistas.append(tool_id)
    return vistas


def _with_limitations_note(text: str, done) -> str:
    """[S11, doc 34 §S11] Línea final DETERMINISTA (nunca la escribe el LLM):
    si algún paso completado tuvo que seguir sin una herramienta que pidió y
    no se le concedió, el usuario se entera SIEMPRE — aunque la síntesis
    suene a éxito completo. El caso de Cordyceps: un documento entregado sin
    ninguna nota de que se hizo sin poder leer la fuente real."""
    tools = _limitations_of(done)
    if not tools:
        return text
    nota = _t("responder.limitations_note", tools=", ".join(tools))
    return f"{text}\n\n{nota}"


def _node_output(n) -> str:
    if n.result and isinstance(n.result, dict):
        out = n.result.get("output")
        if out:
            return str(out)[:600]
        return str(n.result)[:600]
    return _t("responder.node_done_fallback")


def _template_success(mission, done, failed, skipped, cancelled) -> str:
    """Plantilla determinista (sin LLM). Fea pero honesta: nunca deja al usuario
    sin respuesta porque el modelo esté caído. [I18N-10] En el idioma de
    interfaz elegido — es texto de puro código, no pasa por ningún LLM."""
    parts = [_t("responder.completed_header", n=len(done), goal=mission.goal)]
    parts += [f"• {n.goal}: {_node_output(n)}" for n in done]
    if failed:
        items = "; ".join(f"{n.goal} ({n.error or 'error'})" for n in failed)
        parts.append(_t("responder.could_not_complete", items=items))
    if skipped:
        parts.append(_t("responder.left_untried", items="; ".join(n.goal for n in skipped)))
    if cancelled:
        parts.append(_t("responder.you_cancelled", items="; ".join(n.goal for n in cancelled)))
    return "\n".join(parts)


def _template_failure(mission, failed) -> str:
    if not failed:
        return _t("responder.no_progress", goal=mission.goal)
    reasons = "; ".join(f"{n.goal} ({n.error or 'error'})" for n in failed)
    return _t("responder.failed_with_reasons", goal=mission.goal, reasons=reasons)


def plan_summary(graph: TaskGraph) -> str:
    """Resumen legible del plan para la UI de aprobación (T4b) y para el gate
    del plan: los pasos en orden topológico aproximado, marcando los sensibles."""
    lines = []
    for i, node in enumerate(graph.nodes.values(), 1):
        mark = _t("responder.plan_step_permission_mark") if node.approval_required else ""
        lines.append(f"{i}. {node.goal}{mark}")
    return "\n".join(lines)
