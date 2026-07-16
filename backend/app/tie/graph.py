# app/tie/graph.py — Graph Execution Engine: construcción + validación (doc 14 §1.5/§3.4.1, T2)
#
# El corazón propio inspirado en LangGraph, PERO grafo-como-DATOS: el TaskGraph es
# una estructura serializable que produce el Planner; aquí se VALIDA antes de que
# nada se ejecute (planning sin side effects, regla 11-B). El loop de ejecución
# (olas + checkpoint + gates) es el executor (T3); aquí solo la estructura y sus
# invariantes + el ready-set que el executor consumirá.
#
# Sin dependencias (ni NetworkX): Kahn/topological en ~30 líneas (dict + in-degree).
from __future__ import annotations

from typing import Iterable

from app.core.logging_config import get_system_logger
from app.tie.contracts import NodeState, TaskGraph, TaskNode

logger = get_system_logger("tie.graph")


def build(mission_id: str, nodes: Iterable[TaskNode], *, created_by: str = "planner",
          graph_id: str | None = None) -> TaskGraph:
    """Construye un TaskGraph a partir de una lista de nodos. NO valida (eso es
    `validate`); solo ensambla la estructura."""
    import uuid

    node_map = {n.id: n for n in nodes}
    return TaskGraph(
        id=graph_id or uuid.uuid4().hex,
        mission_id=mission_id,
        nodes=node_map,
        created_by=created_by,
        state="draft",
    )


def validate(graph: TaskGraph, *, tool_catalog: set[str] | None = None) -> tuple[bool, str]:
    """Valida las invariantes del grafo ANTES de ejecutar (doc 14 §3.4.1):
      1. hay al menos un nodo y todos tienen id/goal.
      2. `depends_on` referencia solo a ids existentes (sin aristas colgantes).
      3. no hay ciclos (Kahn/topological).
      4. `tools` de cada nodo ⊆ catálogo del ToolManager.
    Devuelve (ok, motivo). El motivo se usa como feedback al reintentar el
    planner (doc 14 §3.4.1). Presupuesto: < 10 ms (doc 14 §6).
    """
    nodes = graph.nodes
    if not nodes:
        return False, "el grafo no tiene nodos"

    # 1) ids/goals
    for nid, node in nodes.items():
        if not node.id or node.id != nid:
            return False, f"nodo con id inconsistente: clave={nid!r} id={node.id!r}"
        if not (node.goal or "").strip():
            return False, f"el nodo {nid!r} no tiene goal"

    # 2) aristas a ids existentes
    for nid, node in nodes.items():
        for dep in node.depends_on:
            if dep not in nodes:
                return False, f"el nodo {nid!r} depende de un id inexistente: {dep!r}"
            if dep == nid:
                return False, f"el nodo {nid!r} depende de sí mismo"

    # 3) sin ciclos (Kahn)
    if _has_cycle(nodes):
        return False, "el grafo tiene un ciclo (debe ser un DAG)"

    # 4) tools ⊆ catálogo
    if tool_catalog is None:
        tool_catalog = _tool_catalog()
    for nid, node in nodes.items():
        for tool in node.tools:
            if tool not in tool_catalog:
                return False, (
                    f"el nodo {nid!r} pide una herramienta inexistente: {tool!r} "
                    f"(disponibles: {sorted(tool_catalog)})"
                )

    return True, "ok"


def ready_set(graph: TaskGraph) -> list[TaskNode]:
    """Nodos elegibles para ejecutar: PENDING con TODAS sus `depends_on` en DONE.
    Orden determinista (prioridad desc, id asc) — el executor (T3) toma el primero
    en V1.0 (ola de tamaño 1); en V1.2 toda la lista con semáforo."""
    ready: list[TaskNode] = []
    for node in graph.nodes.values():
        if node.state != NodeState.PENDING:
            continue
        deps = [graph.nodes.get(d) for d in node.depends_on]
        if all(d is not None and d.state == NodeState.DONE for d in deps):
            ready.append(node)
    ready.sort(key=lambda n: (-n.priority, n.id))
    return ready


# ---------------------------------------------------------------------------
# internos
# ---------------------------------------------------------------------------
def _has_cycle(nodes: dict[str, TaskNode]) -> bool:
    """Kahn: si tras procesar todos los nodos de in-degree 0 (en cascada) queda
    alguno sin procesar, hay un ciclo. O(V+E), sin recursión, sin dependencias."""
    in_degree = {nid: 0 for nid in nodes}
    for node in nodes.values():
        for dep in node.depends_on:
            # arista dep -> node ; node "entra" desde dep, así que node gana in-degree
            if dep in in_degree:
                in_degree[node.id] += 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    processed = 0
    while queue:
        current = queue.pop()
        processed += 1
        # los nodos que dependían de `current` pierden una arista entrante
        for node in nodes.values():
            if current in node.depends_on:
                in_degree[node.id] -= 1
                if in_degree[node.id] == 0:
                    queue.append(node.id)
    return processed < len(nodes)


def _tool_catalog() -> set[str]:
    """Set de tool_ids registrados en el ToolManager (para validar node.tools)."""
    try:
        from app.tools import tool_manager

        return {t["tool_id"] for t in tool_manager.list_tools()}
    except Exception as e:
        logger.error(f"[graph] no se pudo leer el catálogo de tools: {e!r}")
        return set()
