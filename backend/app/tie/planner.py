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
from dataclasses import dataclass
from typing import Optional, Union

from app.ai.reasoning_filter import strip_reasoning
from app.core.logging_config import get_system_logger
from app.tie import graph as graph_mod
from app.tie import router, tracer
from app.tie.authority import Authority
from app.tie.contracts import Intent, TaskGraph, TaskNode
from app.tie.intents import _extract_json

logger = get_system_logger("tie.planner")

# [S2, B-1] Techo de tamaño FLEXIBLE (decisión del usuario en el plan de
# corrección, doc 25 §S2): el techo duro de 4-6 nodos era un cuello de botella
# artificial — una misión de tamaño "proyecto" no cabe en 4 nodos y el planner
# acababa prometiendo lo imposible o degradando a nada. Ahora: 2-5 típico,
# hasta 8 si el objetivo lo necesita de verdad; >8 sigue siendo un plan mal
# hecho (reintento con feedback, como siempre).
_MAX_REASONABLE_NODES = 8


@dataclass
class PlanRejection:
    """[S2, B-1] El planner declara HONESTAMENTE que el objetivo excede las
    capacidades reales del sistema (herramientas/acciones disponibles), con el
    motivo. El caller lo convierte en una respuesta clara al usuario — NUNCA en
    una misión fantasma que finge poder y entrega nada. Distinto de None (que
    significa "no logré un plan válido" y degrada a camino corto)."""
    reason: str


_SYSTEM_PROMPT = """Eres el planificador de Aithera. Recibes un OBJETIVO del usuario y su
contexto, y devuelves SOLO un objeto JSON con un plan como grafo de tareas (sin texto
extra, sin markdown).

REGLA DE ORO — FIDELIDAD AL OBJETIVO: el plan trata EXACTAMENTE del OBJETIVO tal
como está escrito. El CONTEXTO (memoria de Aithera) es SOLO REFERENCIA de fondo:
puede ayudarte a concretar CÓMO ejecutar el objetivo, pero NUNCA lo cambia, lo
amplía ni lo sustituye. Si el contexto sugiere temas, proyectos o ideas distintas
de lo pedido, IGNÓRALAS. Planificar otra cosa distinta de lo pedido es el peor
error posible de este sistema.

HONESTIDAD SOBRE CAPACIDADES: dispones del catálogo REAL de herramientas de abajo,
con sus acciones. Si el objetivo requiere capacidades que NO están en el catálogo
(programas concretos que no se pueden ejecutar, hardware, servicios sin
herramienta), NO inventes un plan que fingirá funcionar: devuelve en su lugar
{"cannot": "explicación breve y útil de qué falta y qué SÍ podrías hacer"}.
Decir "no puedo" a tiempo es correcto; prometer y no entregar, no.

El plan típico tiene entre 2 y 5 nodos (hasta 8 solo si el objetivo realmente lo
necesita). Cada nodo es un paso VERIFICABLE. Formato:
{
  "nodes": [
    {
      "id": "n1",
      "goal": "objetivo imperativo y verificable de este paso",
      "depends_on": [],
      "tools": [],
      "approval_required": false,
      "checkpoint": false,
      "model_hint": "fast|smart",
      "context_query": null
    }
  ]
}

Reglas:
- "id" único por nodo (n1, n2, n3...).
- "depends_on": lista de ids de nodos que deben completarse ANTES (define el orden).
  El grafo debe ser acíclico (un nodo no puede depender de sí mismo ni formar ciclos).
- "tools": SOLO herramientas del CATÁLOGO REAL de abajo (usa el tool_id). Si un paso
  no usa herramientas, deja la lista vacía. NUNCA inventes herramientas.

CATÁLOGO REAL (tool_id — qué hace — acciones disponibles):
{tools}
  IMPORTANTE: las herramientas que pongas aquí SE VAN A USAR DE VERDAD — el paso
  las ejecutará contra el sistema real del usuario. Si un paso necesita un dato
  del sistema (archivos, emails, agenda, procesos, web...), DEBES darle la
  herramienta correspondiente: sin ella no podrá obtenerlo y el paso fallará.
  Da a cada nodo solo las que ese paso necesita, no todas por si acaso.
  Para buscar algo en internet y abrirlo (una página, un vídeo, una canción...),
  el nodo necesita AMBAS: "search" (para encontrar la URL) y "browser" (para
  abrirla) — nunca solo "browser" para eso.
- "approval_required": true SOLO para acciones sensibles (enviar algo, borrar,
  ejecutar comandos que cambian el sistema). El usuario confirmará esos pasos.
- "checkpoint": true si al terminar ESE paso queda algo que el usuario PUEDE
  COMPROBAR por su cuenta — un entregable. La misión se parará ahí para que lo
  revise antes de seguir, así que márcalo solo cuando de verdad haya algo que
  mirar, no en cada paso.
  SÍ es checkpoint: "redactar el borrador del email" (puede leerlo), "generar el
  informe" (puede abrirlo), "crear el proyecto con sus tareas" (puede verlo en
  el Workspace).
  NO es checkpoint: "buscar los emails de esta semana", "leer el archivo",
  "consultar la agenda" — son pasos intermedios; pararse ahí solo molesta.
  Si el plan tiene un único paso, no lo marques: no hay nada después que parar.
- Prefiere 2-3 nodos. No infles el plan. Devuelve SOLO el JSON."""


def _tools_available() -> list[str]:
    """Los tool_ids disponibles (para el recorte determinista de autoridad).
    Incluye las tools INTERNAS (operar la propia Aithera): el Orquestador puede
    hacerlo por definición, no es un permiso que nadie le conceda."""
    try:
        from app.tools import tool_manager

        return sorted(t["tool_id"] for t in tool_manager.tie_catalog())  # [P1] accesor único
    except Exception:
        return []


def _tools_catalog_text(allowed: Optional[set] = None) -> str:
    """[S2, B-1] El catálogo REAL que ve el planner: tool_id + descripción breve
    + ids de acciones. Antes solo veía NOMBRES de tools y prometía pasos que la
    ejecución no podía cumplir (shell sin godot, browser sin instalar programas…).
    Acotado a una línea por tool para no inflar el prompt (~20 líneas)."""
    try:
        from app.tools import tool_manager

        lines = []
        for t in tool_manager.tie_catalog():  # [P1] accesor único
            if allowed is not None and t["tool_id"] not in allowed:
                continue
            desc = (t.get("description") or "").split(".")[0][:110]
            actions = ", ".join(a.get("id", "") for a in t.get("actions", []))
            lines.append(f'- {t["tool_id"]} — {desc} — acciones: {actions}')
        return "\n".join(lines) or "(sin herramientas disponibles)"
    except Exception:
        return "(catálogo no disponible)"


def _internal_tools() -> set:
    try:
        from app.tools import tool_manager

        return tool_manager.internal_tool_ids()
    except Exception:
        return set()


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
            checkpoint=bool(rn.get("checkpoint")),
            model_hint=(str(rn["model_hint"]) if rn.get("model_hint") else None),
            context_query=(str(rn["context_query"]) if rn.get("context_query") else None),
        ))
    if not nodes:
        raise ValueError("ningún nodo usable en 'nodes'")
    return nodes


async def _generate_graph(goal: str, context: str, mission_id: str,
                          feedback: Optional[str] = None,
                          authority: Optional[Authority] = None,
                          ) -> tuple[Union[TaskGraph, PlanRejection, None], str, Optional[str]]:
    """Una pasada del planner: pide el grafo, lo parsea, lo construye y valida.
    Devuelve (graph|PlanRejection|None, motivo, model_used). `feedback` (del
    intento previo) se añade al prompt para que el LLM corrija."""
    tools = _tools_available()
    # [R4] Si la misión tiene frontera (viene de un agente), el modelo solo ve
    # SUS herramientas. Esto es calidad del plan, no seguridad: la seguridad es
    # el recorte determinista de más abajo, que no depende de que el LLM haga caso.
    permitidas: Optional[set] = None
    if authority is not None and authority.allowed_tools is not None:
        # Las internas NO se recortan: no son capacidades que el agente tenga o
        # deje de tener, son de Aithera. Lo que sí las acota es la frontera de
        # PROYECTO (R4), que se comprueba en cada llamada.
        permitidas = set(authority.allowed_tools) | _internal_tools()
        tools = [t for t in tools if t in permitidas]
    # [S2, B-1] El planner ve el catálogo REAL (acciones incluidas), no solo nombres.
    system = _SYSTEM_PROMPT.replace("{tools}", _tools_catalog_text(permitidas))
    # [I18N-9] Los `goal` de cada nodo se muestran al usuario en la vista de
    # Misiones — deben salir en el idioma de interfaz elegido. Se localiza SOLO
    # ese campo: las claves del JSON, ids (n1, n2…) y tool_ids NO se traducen, o
    # el plan dejaría de parsear/validar. Si no hay idioma elegido, no se añade
    # nada (comportamiento histórico: goals en el idioma que decida el modelo).
    try:
        from app.core.language import ui_language_name

        lang_name = ui_language_name()
        if lang_name:
            system += (
                f"\n\nIDIOMA: escribe el campo \"goal\" de cada nodo en {lang_name} "
                f"(es lo que el usuario leerá). NO traduzcas las claves del JSON, "
                f"los ids de nodo ni los tool_ids del catálogo."
            )
    except Exception:
        pass  # best-effort: sin idioma, goals en el idioma que elija el modelo
    # [S2, C-1] Etiquetado anti-contaminación: el OBJETIVO es la petición
    # literal; el CONTEXTO va explícitamente marcado como solo-referencia.
    user = f"OBJETIVO (la petición del usuario, tal cual — la ÚNICA fuente del plan):\n{goal}"
    if context:
        user += f"\n\nCONTEXTO (memoria de Aithera — SOLO REFERENCIA, nunca cambia el objetivo):\n{context}"
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

    # [S2, B-1] Rechazo honesto: el objetivo excede las capacidades reales.
    if isinstance(data.get("cannot"), str) and data["cannot"].strip():
        return PlanRejection(reason=data["cannot"].strip()), "rechazo honesto", model_used

    try:
        nodes = _parse_nodes(data)
    except ValueError as e:
        return None, str(e), model_used

    if len(nodes) > _MAX_REASONABLE_NODES:
        return None, (f"demasiados nodos ({len(nodes)}); un plan típico tiene 2-5 "
                      f"(máx {_MAX_REASONABLE_NODES})"), model_used

    # [R4] EL RECORTE DE SEGURIDAD. Determinista, por código, nunca confiado al
    # LLM: aunque el prompt ya le enseñó solo sus tools, un modelo puede pedir
    # otra igualmente. Se recorta ANTES de construir el grafo, así que lo que se
    # persiste en el checkpoint ya viene acotado y una reanudación tras reinicio
    # no puede recuperar permisos que la misión nunca tuvo.
    if authority is not None and authority.allowed_tools is not None:
        permitidas = set(authority.allowed_tools) | _internal_tools()
        for n in nodes:
            n.tools = [t for t in n.tools if t in permitidas]

    g = graph_mod.build(mission_id, nodes, created_by="planner")
    if authority is not None:
        g.authority = authority.to_dict()
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
    authority: Optional[Authority] = None,
) -> Union[TaskGraph, PlanRejection, None]:
    """Planifica un objetivo complejo → TaskGraph validado; PlanRejection si el
    objetivo excede las capacidades reales (el caller responde ESO al usuario);
    None si no se logró un plan válido (el caller degrada a camino corto).
    1 reintento con feedback ante grafo inválido (doc 14 §3.4.1). Registra el
    plan en Decision API + tracer (best-effort).

    `goal` [S2, C-1] debe ser el TEXTO ORIGINAL del usuario (`intent.raw_text`),
    no el goal reescrito por el clasificador.

    `authority` (R4) acota la misión: el plan solo puede usar las herramientas
    del agente, y la frontera queda grabada en el propio grafo para que
    sobreviva al checkpoint.
    """
    mission_id = mission_id or uuid.uuid4().hex

    g, reason, model_used = await _generate_graph(goal, context, mission_id, authority=authority)
    if isinstance(g, PlanRejection):
        logger.info(f"[planner] rechazo honesto: {g.reason[:150]}")
        return g
    if g is None:
        logger.info(f"[planner] grafo inválido, 1 reintento. Motivo: {reason}")
        g, reason, model_used = await _generate_graph(goal, context, mission_id, feedback=reason,
                                                      authority=authority)

    if isinstance(g, PlanRejection):
        logger.info(f"[planner] rechazo honesto (2.ª pasada): {g.reason[:150]}")
        return g
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
