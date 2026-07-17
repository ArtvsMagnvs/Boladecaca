# tests/test_tie_perf.py — presupuestos de rendimiento del TIE (doc 14 §6, T5)
#
# Blinda los 5 presupuestos del diseño + que el camino corto jamás paga el coste
# del planificador. No se mide contra un LLM real (eso ya lo hizo la
# verificación en vivo de cada sprint T1-T4): aquí se mide el propio motor —
# validación, checkpoint, overhead del executor, reanudación, kill-switch — con
# runtimes fake y SQLite de test, deterministas y sin red, para que corra en CI.
from __future__ import annotations

import time

import pytest

from app.automation import Approval, approval_gate
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.tie import (
    AgentResult,
    AgentRuntime,
    Intent,
    IntentType,
    NodeState,
    RuntimeHealth,
    TaskGraph,
    TaskNode,
    executor,
    new_mission,
    register_runtime,
    tracer,
)
from app.tie import graph as graph_mod


@pytest.fixture(autouse=True)
def _tables_and_clean():
    Base.metadata.create_all(bind=db_engine)
    executor._CANCELLED.clear()
    executor._NODE_TASKS.clear()
    yield
    executor._CANCELLED.clear()
    executor._NODE_TASKS.clear()
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(Approval).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


class _InstantRuntime(AgentRuntime):
    """Runtime sin coste propio: lo que se mide es el overhead del ENGINE, no el
    del runtime (el LLM real se midió en vivo en T1-T4)."""

    @property
    def capabilities(self):
        return {"chat"}

    async def execute_task(self, task, memory, tools, approval_gate):
        return AgentResult(task_id=task.id, success=True, output="ok", tokens=1)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


@pytest.fixture
def instant_rt():
    rt = _InstantRuntime()
    register_runtime("instant", rt)
    return rt


def _node(nid, **kw) -> TaskNode:
    return TaskNode(id=nid, goal=f"paso {nid}", runtime="instant", **kw)


def _start(goal="misión de perf"):
    m = new_mission(goal, source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    return m, trace_id


# ---------------------------------------------------------------------------
# 1) validación de grafo < 10 ms (doc 14 §6)
# ---------------------------------------------------------------------------
def test_validacion_de_grafo_bajo_10ms():
    nodes = [_node("n1")] + [_node(f"n{i}", depends_on=[f"n{i-1}"]) for i in range(2, 6)]
    g = graph_mod.build("m1", nodes)

    t0 = time.perf_counter()
    ok, reason = graph_mod.validate(g, tool_catalog=set())
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert ok is True, reason
    assert elapsed_ms < 10, f"validate() tardó {elapsed_ms:.2f} ms (presupuesto: 10 ms)"


# ---------------------------------------------------------------------------
# 2) transición + checkpoint < 20 ms por transición (doc 14 §3.4.3/§6)
# ---------------------------------------------------------------------------
def test_checkpoint_por_transicion_bajo_20ms():
    m, trace_id = _start()
    g = TaskGraph(id="g1", mission_id=m.id, nodes={"n1": _node("n1")})
    tracer.record_plan(trace_id, g)

    # Varias transiciones seguidas (como las que hace el executor en un nodo
    # real: PENDING→RUNNING→DONE) — se mide el peor caso, no el promedio.
    peor_ms = 0.0
    for state in (NodeState.RUNNING, NodeState.DONE):
        g.nodes["n1"].state = state
        t0 = time.perf_counter()
        tracer.update_graph(trace_id, g)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        peor_ms = max(peor_ms, elapsed_ms)

    assert peor_ms < 20, f"checkpoint tardó {peor_ms:.2f} ms (presupuesto: 20 ms)"


# ---------------------------------------------------------------------------
# 3) overhead del engine por nodo < 50 ms (doc 14 §6) — runtime instantáneo, así
#    que el tiempo medido es TODO overhead del executor (contexto/checkpoint/
#    transición/validación), no el coste de un LLM.
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_overhead_del_engine_por_nodo_bajo_50ms(instant_rt):
    m, trace_id = _start()
    g = TaskGraph(id="g2", mission_id=m.id, nodes={"n1": _node("n1")})
    tracer.record_plan(trace_id, g)

    t0 = time.perf_counter()
    await executor.run(g, m, trace_id=trace_id)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert g.nodes["n1"].state == NodeState.DONE
    assert elapsed_ms < 50, f"un nodo tardó {elapsed_ms:.2f} ms de overhead (presupuesto: 50 ms)"


# ---------------------------------------------------------------------------
# 4) reanudación de grafos al arrancar < 500 ms (doc 14 §3.4.3/§6)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_resume_pending_bajo_500ms_con_varias_misiones(instant_rt):
    # Varias misiones "a medias" (como tras un reinicio real): cada una con un
    # nodo pendiente que el runtime instantáneo resuelve.
    for i in range(5):
        m, trace_id = _start(goal=f"misión {i}")
        g = TaskGraph(id=f"g-{i}", mission_id=m.id, nodes={"n1": _node("n1")})
        tracer.record_plan(trace_id, g)
        tracer.set_state(trace_id, "running")

    t0 = time.perf_counter()
    n = await executor.resume_pending()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert n == 5
    assert elapsed_ms < 500, f"resume_pending() tardó {elapsed_ms:.2f} ms (presupuesto: 500 ms)"


# ---------------------------------------------------------------------------
# 5) kill-switch < 2 s incluso con un nodo largo en vuelo (doc 14 §3.4.6/§6)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_kill_switch_interrumpe_bajo_2s(instant_rt):
    import asyncio

    class _SlowRuntime(_InstantRuntime):
        async def execute_task(self, task, memory, tools, approval_gate):
            await asyncio.sleep(5)  # nunca se espera de verdad: se cancela antes
            return AgentResult(task_id=task.id, success=True, output="tarde")

    register_runtime("slow", _SlowRuntime())
    m, trace_id = _start()
    g = TaskGraph(id="g3", mission_id=m.id, nodes={
        "n1": TaskNode(id="n1", goal="lento", runtime="slow"),
    })
    tracer.record_plan(trace_id, g)

    async def _cancel_soon():
        await asyncio.sleep(0.05)
        executor.cancel(m.id)

    t0 = time.perf_counter()
    await asyncio.gather(executor.run(g, m, trace_id=trace_id), _cancel_soon())
    elapsed_s = time.perf_counter() - t0

    assert elapsed_s < 2.0, f"kill-switch tardó {elapsed_s:.2f} s (presupuesto: 2 s)"
    assert g.nodes["n1"].state == NodeState.CANCELLED


# ---------------------------------------------------------------------------
# 6) el camino corto NUNCA paga el coste del planner (doc 14 §6 — el ~80% de
#    las queries no debe notar que el planner existe, ni en tiempo ni en llamadas)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_camino_corto_no_invoca_el_planner(monkeypatch):
    from app.tie import handle
    from app.tie import pipeline as pipeline_mod
    from app.services import chat_service

    class _A:
        text = "hola, soy Aithera"
        model = "fake"
        tokens = 3

    async def _answer(message, *, channel="web", persist_chat_message=True):
        return _A()
    monkeypatch.setattr(chat_service, "answer", _answer)

    async def _classify(text, *, channel=None):
        return Intent(type=IntentType.CONVERSATIONAL, goal=text, confidence=0.9)
    monkeypatch.setattr(pipeline_mod.intents, "classify", _classify)

    calls = {"n": 0}
    async def _plan(*a, **k):
        calls["n"] += 1
        return None
    monkeypatch.setattr(pipeline_mod.planner, "plan", _plan)

    class _Env:
        text = "hola"
        channel = "hub"

    t0 = time.perf_counter()
    out = await handle(_Env())
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert out == "hola, soy Aithera"
    assert calls["n"] == 0, "el camino corto invocó al planner — no debería"
    assert elapsed_ms < 100, f"el camino corto tardó {elapsed_ms:.2f} ms (nada de planner, debe ser trivial)"
