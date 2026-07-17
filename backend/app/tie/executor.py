# app/tie/executor.py — Graph Execution Engine (doc 14 §3.4, V1.0/T3)
#
# El corazón del TIE: ejecuta un TaskGraph ya validado (T2), nodo a nodo, con
# checkpoint en CADA transición, gates que pausan/reanudan, recuperación por
# degradación, kill-switch y validación determinista por nodo.
#
# Garantías (doc 14 §3.4):
#   - PLANIFICAR NO EJECUTA: aquí llega un grafo ya validado; nada se ejecuta antes.
#   - CHECKPOINT POR TRANSICIÓN: todo el estado vive en `orchestrator_traces.plan`.
#     Reanudar (tras un gate o un reinicio) = cargar el grafo y recomputar ready-set.
#   - GATES: un nodo puede esperar HORAS/DÍAS — el grafo está en disco, no en RAM.
#   - AISLAMIENTO: un nodo que revienta degrada el grafo, nunca tumba el proceso.
#
# V1.0: la "ola" es de tamaño 1 (secuencial, orden determinista). V1.2: toda la
# ola con `asyncio.gather` + semáforo `TIE_MAX_PARALLEL` — MISMO algoritmo, solo
# cambia cuántos nodos del ready-set se lanzan a la vez.
from __future__ import annotations

import asyncio
import time
from typing import Optional

from app.core.logging_config import get_system_logger
from app.tie import graph as graph_mod
from app.tie import tracer
from app.tie.contracts import Mission, NodeState, TaskGraph, TaskNode
from app.tie.runtime import AgentResult, AgentTask, get_runtime

logger = get_system_logger("tie.executor")

# Estados terminales: un nodo aquí ya no se toca.
_TERMINAL = {NodeState.DONE, NodeState.FAILED, NodeState.SKIPPED, NodeState.CANCELLED}

# Kill-switch (doc 14 §3.4.6). `_CANCELLED` sobrevive a la vuelta del loop;
# `_NODE_TASKS` permite cancelación COOPERATIVA del nodo en vuelo (< 2 s) en vez
# de esperar a que termine su LLM/tool.
_CANCELLED: set[str] = set()
_NODE_TASKS: dict[str, asyncio.Task] = {}

# action_type con el que el TIE pide permiso al ApprovalGate de V0.9.
GATE_ACTION_TYPE = "tie_resume"


# ---------------------------------------------------------------------------
# API pública del executor
# ---------------------------------------------------------------------------
async def run(
    graph: TaskGraph, mission: Mission, *, trace_id: str, write_terminal_state: bool = True
) -> Mission:
    """Ejecuta el grafo hasta que no quedan nodos ejecutables, un gate lo pausa,
    o el usuario lo cancela. Reentrante: al reanudar (gate resuelto / reinicio)
    se vuelve a llamar con el grafo recargado y continúa donde estaba.

    Devuelve la Mission con su `state` actualizado:
      running→done   (todo lo ejecutable terminó)
      running→waiting (pausado en un gate; el grafo espera en disco)
      running→failed  (nada útil se pudo entregar)
      running→cancelled (kill-switch)

    `write_terminal_state=False`: no escribas done/failed en la traza al
    terminar — lo hará quien llame junto con el outcome sintetizado (el
    responder tarda varios segundos; escribir el estado antes deja una
    ventana donde `state=done` pero `outcome` aún es el mensaje pre-ejecución
    del gate). Quien pase False es responsable de llamar a `tracer.record_end`
    con el outcome real inmediatamente después. waiting/cancelled no se ven
    afectados: se escriben en su propio punto de origen, no aquí.
    """
    while True:
        if mission.id in _CANCELLED:
            _cancel_remaining(graph)
            _checkpoint(trace_id, graph)
            mission.state = "cancelled"
            tracer.set_state(trace_id, "cancelled")
            _CANCELLED.discard(mission.id)
            return mission

        ready = graph_mod.ready_set(graph)
        if not ready:
            break

        # V1.0: ola de tamaño 1 — el primero del orden determinista (prioridad
        # desc, id asc). V1.2: `asyncio.gather` sobre toda la ola con semáforo.
        node = ready[0]

        # ¿Necesita permiso? → pausa el grafo (el gate es HITL, doc 14 §3.4.4).
        if node.approval_required and node.gate_id is None:
            await _open_gate(node, graph, mission, trace_id)
            mission.state = "waiting"
            return mission

        await _execute_node(node, graph, mission, trace_id)

        if mission.id in _CANCELLED:
            continue  # el kill-switch llegó durante el nodo: la cabecera lo resuelve

    return _finalize(graph, mission, trace_id, write_terminal_state=write_terminal_state)


def cancel(mission_id: str) -> bool:
    """Kill-switch (doc 14 §3.4.6): marca la misión como cancelada y corta el
    nodo en vuelo (cancelación cooperativa — el runtime recibe CancelledError).
    Devuelve True si había algo que cancelar. Objetivo: < 2 s."""
    _CANCELLED.add(mission_id)
    task = _NODE_TASKS.get(mission_id)
    if task is not None and not task.done():
        task.cancel()
        return True
    return True


def is_cancelled(mission_id: str) -> bool:
    return mission_id in _CANCELLED


async def resume_pending() -> int:
    """Reanuda las misiones a medias tras un reinicio (doc 14 §3.4.3). Se llama
    desde el `lifespan` (T4). Para cada traza `running|waiting`:
      - si su nodo en WAITING_APPROVAL ya tiene veredicto (el usuario resolvió
        mientras el backend estaba caído), se aplica y se sigue;
      - si sigue pendiente, se deja esperando (el evento la despertará);
      - si no había gate, se continúa el loop donde se quedó.
    Devuelve cuántas misiones se reanudaron. Best-effort: una traza corrupta no
    impide reanudar el resto."""
    resumed = 0
    for trace_id in tracer.pending_trace_ids():
        try:
            if await _resume_trace(trace_id):
                resumed += 1
        except Exception as e:
            logger.error(f"[executor] no se pudo reanudar la traza {trace_id} (se omite): {e!r}")
    if resumed:
        logger.info(f"[executor] {resumed} misión(es) reanudada(s) tras el arranque")
    return resumed


# ---------------------------------------------------------------------------
# Ejecución de un nodo
# ---------------------------------------------------------------------------
async def _execute_node(node: TaskNode, graph: TaskGraph, mission: Mission, trace_id: str) -> None:
    """Ejecuta UN nodo con el runtime que pida (memoria/tools/gate inyectados) y
    escribe su estado/resultado. Cada transición hace checkpoint."""
    from app.automation import approval_gate
    from app.memory import memory_router
    from app.tools import tool_manager

    _transition(node, NodeState.RUNNING, graph, trace_id)
    t0 = time.monotonic()

    # Contexto del nodo: el enricher con presupuesto de latencia duro (T2).
    context = ""
    if node.context_query:
        from app.tie import enricher

        context = await enricher.enrich(node.context_query, memory_types=node.memory_types)

    task = AgentTask(
        id=AgentTask.new_id(),
        instruction=node.goal,
        context=context,
        node_id=node.id,
        tools=node.tools,
        model_hint=node.model_hint,
        channel=mission.channel,
    )
    runtime = get_runtime(node.runtime)

    inner = asyncio.create_task(
        runtime.execute_task(task, memory=memory_router, tools=tool_manager, approval_gate=approval_gate)
    )
    _NODE_TASKS[mission.id] = inner
    try:
        result: AgentResult = await inner
    except asyncio.CancelledError:
        # Kill-switch durante el nodo: cancelación cooperativa (el runtime fue
        # interrumpido). El nodo queda CANCELLED; la cabecera del loop hace el resto.
        node.duration_ms = int((time.monotonic() - t0) * 1000)
        _transition(node, NodeState.CANCELLED, graph, trace_id)
        return
    except Exception as e:
        # Un runtime que revienta NO tumba el grafo: se degrada (§3.4.5).
        node.error = f"{type(e).__name__}: {e}"
        node.duration_ms = int((time.monotonic() - t0) * 1000)
        _fail_node(node, graph, mission, trace_id)
        return
    finally:
        _NODE_TASKS.pop(mission.id, None)

    node.duration_ms = int((time.monotonic() - t0) * 1000)
    node.tokens = result.tokens
    node.result = result.result if result.result is not None else ({"output": result.output} if result.output else None)
    node.validation = _validate_result(node, result)

    if result.success and node.validation.get("ok"):
        if result.tokens:
            mission.spent_tokens += result.tokens
        _transition(node, NodeState.DONE, graph, trace_id)
    else:
        node.error = result.error or node.validation.get("notes") or "el nodo no produjo un resultado válido"
        _fail_node(node, graph, mission, trace_id)


def _validate_result(node: TaskNode, result: AgentResult) -> dict:
    """Validación por nodo (doc 14 §3.4.7). V1.0: DETERMINISTA y barata — ¿la
    ejecución fue bien? ¿hay salida con forma? Nada de LLM aquí (eso es V1.2, y
    solo si el nodo lo declara). El veredicto es materia prima del Learner —
    jamás teatro: si no se puede afirmar que está bien, se dice."""
    if not result.success:
        return {"ok": False, "method": "schema", "notes": result.error or "la ejecución falló"}
    has_output = bool(result.output) or bool(result.result)
    if not has_output:
        return {"ok": False, "method": "schema", "notes": "el nodo terminó sin producir salida"}
    return {"ok": True, "method": "schema", "notes": ""}


# ---------------------------------------------------------------------------
# Gates (doc 14 §3.4.4) — HITL como ESTADO de primera clase
# ---------------------------------------------------------------------------
async def _open_gate(node: TaskNode, graph: TaskGraph, mission: Mission, trace_id: str) -> None:
    """Pide permiso y PAUSA el grafo. El nodo queda WAITING_APPROVAL en disco: si
    el usuario tarda dos días, da igual. Reusa el ApprovalGate de V0.9 tal cual —
    incluida la auto-resolución por permiso pre-autorizado (A3b), que el TIE
    hereda gratis: si el usuario ya autorizó ese `kind`, el gate se resuelve solo
    (con rastro) y el evento reanuda de inmediato."""
    from app.automation import approval_gate

    gate_id = await approval_gate.request_approval(
        kind="tie.node",
        title=node.goal[:200],
        summary=f"Paso de la misión: {mission.goal[:300]}",
        action_type=GATE_ACTION_TYPE,
        action_payload={"trace_id": trace_id, "node_id": node.id, "mission_id": mission.id},
        channel=mission.channel or "hub",
    )
    node.gate_id = gate_id
    _transition(node, NodeState.WAITING_APPROVAL, graph, trace_id)
    tracer.set_state(trace_id, "waiting")
    logger.info(f"[executor] nodo {node.id} esperando aprobación (gate {gate_id})")


async def _apply_gate_verdict(trace_id: str, node_id: str, approved: bool) -> None:
    """Aplica el veredicto de un gate y sigue. Se invoca desde el handler del
    evento `approval.resolved` (en background — NUNCA dentro del resolve() del
    gate, que vive en el camino de un request HTTP)."""
    graph = tracer.load_graph(trace_id)
    meta = tracer.get_meta(trace_id)
    if graph is None or meta is None:
        logger.error(f"[executor] veredicto para una traza inexistente: {trace_id}")
        return
    node = graph.nodes.get(node_id)
    if node is None or node.state != NodeState.WAITING_APPROVAL:
        return  # ya aplicado (idempotencia) o el nodo cambió

    mission = _mission_from_meta(meta, graph)

    if approved:
        # El permiso era PREVIO a ejecutar: ahora sí corre.
        node.state = NodeState.PENDING  # vuelve al ready-set con el gate ya concedido
        _checkpoint(trace_id, graph)
        tracer.set_state(trace_id, "running")
        await run(graph, mission, trace_id=trace_id)
    else:
        node.error = "el usuario rechazó este paso"
        _fail_node(node, graph, mission, trace_id)
        tracer.set_state(trace_id, "running")
        await run(graph, mission, trace_id=trace_id)


async def _on_approval_resolved(event) -> None:
    """Handler del bus (doc 17). Reanuda el grafo cuando SU gate se resuelve —
    aprobado o rechazado, por el mismo camino. `emit` lo despacha con
    `create_task`, así que el POST /approvals/{id}/resolve responde al instante
    aunque el resto del grafo tarde minutos."""
    payload = event.payload or {}
    if payload.get("action") != GATE_ACTION_TYPE:
        return  # no es un gate del TIE (p.ej. un email_send del AE)
    gate_id = payload.get("gate_id")
    approved = payload.get("resolution") == "approved"
    try:
        from app.automation import approval_gate

        appr = approval_gate.get(gate_id)
        if appr is None:
            return
        data = dict(appr.action_payload or {})
        trace_id, node_id = data.get("trace_id"), data.get("node_id")
        if not trace_id or not node_id:
            return
        await _apply_gate_verdict(trace_id, node_id, approved)
    except Exception as e:
        logger.error(f"[executor] fallo aplicando el veredicto del gate {gate_id}: {e!r}")


async def _gate_executor(payload: dict) -> str:
    """Ejecutor registrado para `tie_resume`. NO reanuda aquí: la reanudación es
    event-driven (`_on_approval_resolved`) para no bloquear el request HTTP que
    resuelve la aprobación. Existe para honrar el contrato del registro del gate
    (sin él, `resolve()` reportaría 'sin ejecutor' y ensuciaría la auditoría)."""
    return f"aprobación registrada; reanudación del nodo {payload.get('node_id')} en curso"


def register_gate_handlers() -> None:
    """Cablea el TIE con el ApprovalGate + el bus. Idempotente. Lo llama el
    `lifespan` (T4); los tests lo invocan directamente."""
    from app.automation import approval_gate
    from app.core.events import subscribe, unsubscribe

    approval_gate.register_executor(GATE_ACTION_TYPE, _gate_executor)
    unsubscribe("approval.resolved", _on_approval_resolved)  # evita duplicar al re-registrar
    subscribe("approval.resolved", _on_approval_resolved)


# ---------------------------------------------------------------------------
# Recovery (doc 14 §3.4.5) — degradación graciosa
# ---------------------------------------------------------------------------
def _fail_node(node: TaskNode, graph: TaskGraph, mission: Mission, trace_id: str) -> None:
    """Nodo FAILED → sus dependientes TRANSITIVOS quedan SKIPPED. El grafo sigue
    con lo que sí puede hacer; el responder (T4) entrega lo conseguido + la
    explicación. V1.2 añadirá retry con backoff y replan de subárbol."""
    _transition(node, NodeState.FAILED, graph, trace_id)
    for dep_id in _transitive_dependents(graph, node.id):
        dep = graph.nodes[dep_id]
        if dep.state not in _TERMINAL:
            dep.error = f"omitido: depende de {node.id}, que falló"
            _transition(dep, NodeState.SKIPPED, graph, trace_id)
    _remember_error(node, mission)


def _transitive_dependents(graph: TaskGraph, node_id: str) -> list[str]:
    """Todos los nodos que dependen (directa o indirectamente) de `node_id`."""
    out: list[str] = []
    frontier = [node_id]
    seen = {node_id}
    while frontier:
        current = frontier.pop()
        for nid, n in graph.nodes.items():
            if current in n.depends_on and nid not in seen:
                seen.add(nid)
                out.append(nid)
                frontier.append(nid)
    return out


def _remember_error(node: TaskNode, mission: Mission) -> None:
    """Deja el fallo en `mem_error` — materia prima del LLL (doc 09 §2.2 análisis
    2). Best-effort y NO bloqueante: el nodo ya quedó auditado en el grafo."""
    async def _store() -> None:
        try:
            from app.memory import MemoryType, memory_router

            await memory_router.store(
                content=f'Nodo "{node.goal}" falló en la misión "{mission.goal}": {node.error}'[:2000],
                memory_type=MemoryType.ERROR,
                source="tie",
                metadata={"mission_id": mission.id, "node_id": node.id, "goal": node.goal[:200]},
            )
        except Exception as e:
            logger.error(f"[executor] no se pudo escribir mem_error (no crítico): {e!r}")

    try:
        asyncio.get_running_loop().create_task(_store())
    except RuntimeError:
        pass  # sin loop (contexto sync): se omite, el grafo ya tiene el error


# ---------------------------------------------------------------------------
# internos
# ---------------------------------------------------------------------------
def _transition(node: TaskNode, state: NodeState, graph: TaskGraph, trace_id: str) -> None:
    """CADA transición de estado persiste el grafo (checkpoint, doc 14 §3.4.3).
    Decenas de UPDATEs por misión — coste trivial (< 20 ms) a cambio de que todo
    sea reanudable."""
    node.state = state
    _checkpoint(trace_id, graph)


def _checkpoint(trace_id: str, graph: TaskGraph) -> None:
    tracer.update_graph(trace_id, graph)


def _cancel_remaining(graph: TaskGraph) -> None:
    for node in graph.nodes.values():
        if node.state not in _TERMINAL:
            node.state = NodeState.CANCELLED


def _finalize(
    graph: TaskGraph, mission: Mission, trace_id: str, *, write_terminal_state: bool = True
) -> Mission:
    """Cierra la misión cuando no quedan nodos ejecutables. `done` si algo útil
    se completó (aunque haya habido fallos — degradación graciosa); `failed` solo
    si NADA salió bien."""
    states = [n.state for n in graph.nodes.values()]
    any_done = any(s == NodeState.DONE for s in states)
    waiting = any(s in (NodeState.WAITING_APPROVAL, NodeState.WAITING_EVENT) for s in states)

    if waiting:
        mission.state = "waiting"
        graph.state = "running"
    elif any_done:
        mission.state = "done"
        graph.state = "done" if all(s == NodeState.DONE for s in states) else "failed"
    else:
        mission.state = "failed"
        graph.state = "failed"

    _checkpoint(trace_id, graph)
    if not waiting and write_terminal_state:
        tracer.set_state(trace_id, mission.state)
    return mission


def _mission_from_meta(meta: dict, graph: TaskGraph) -> Mission:
    """Reconstruye la Mission implícita de V1.0 desde la traza (§3.6: la misión
    no tiene tabla propia todavía; su identidad vive en `orchestrator_traces`)."""
    return Mission(
        id=meta.get("mission_id") or graph.mission_id,
        goal="",  # el goal real vive en la traza/intent; el executor no lo necesita
        channel=meta.get("channel"),
        state="running",
        graph_ids=[graph.id],
    )


async def _resume_trace(trace_id: str) -> bool:
    """Reanuda UNA traza. Devuelve True si se reactivó el loop."""
    graph = tracer.load_graph(trace_id)
    meta = tracer.get_meta(trace_id)
    if graph is None or meta is None:
        return False

    # ¿Hay un nodo esperando un gate que YA se resolvió mientras el backend
    # estaba caído? El evento se perdió (el bus es in-process, sin persistencia
    # — doc 17): aquí se recupera consultando el veredicto en disco.
    for node in graph.nodes.values():
        if node.state == NodeState.WAITING_APPROVAL and node.gate_id:
            from app.automation import approval_gate

            appr = approval_gate.get(node.gate_id)
            if appr is None or appr.status == "pending":
                return False  # sigue esperando al usuario: nada que reanudar
            await _apply_gate_verdict(trace_id, node.id, appr.status == "approved")
            return True

    mission = _mission_from_meta(meta, graph)
    await run(graph, mission, trace_id=trace_id)
    return True
