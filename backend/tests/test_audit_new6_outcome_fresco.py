# tests/test_audit_new6_outcome_fresco.py — NEW-6 (doc 34 §12.9): "Completada"
# con texto de espera de aprobación.
#
# EL FALLO REAL (verificación en vivo, 2026-07-28): una misión mostraba
# cabecera "Completada" con el cuerpo *"He empezado y estoy esperando tu
# confirmación para un paso"* — la plantilla `pipeline.waiting_confirmation`.
# Causa: `_finalize()` (T3) solo escribe `mission.state` en la traza, nunca
# `outcome`. Cuando un nodo abre su propio gate, `_execute_and_respond` escribe
# `outcome = "esperando tu confirmación"` + `state="waiting"`. Al resolverse el
# gate, `_apply_gate_verdict`/`_apply_checkpoint_verdict` (executor.py, camino
# EVENT-DRIVEN, no pasa por `pipeline.py`) volvían a llamar `run()` — que sí
# actualiza `state` a "done" vía `_finalize()` — pero NADIE volvía a sintetizar
# el `outcome`: se quedaba con el placeholder de espera para siempre.
from __future__ import annotations

import asyncio

import pytest

from app.automation import Approval, approval_gate
from app.core.strings import t as _t
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.tie import (
    AgentResult,
    AgentRuntime,
    Mission,
    NodeState,
    RuntimeHealth,
    TaskGraph,
    TaskNode,
    executor,
    new_mission,
    register_runtime,
    tracer,
)

_WAITING_PLACEHOLDER = _t("pipeline.waiting_confirmation")


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


@pytest.fixture(autouse=True)
def _mel_rapido(monkeypatch):
    """`responder.build()` ahora se invoca en el camino de reanudación de un
    gate (el punto exacto que arregla este test). Sin mockear, `router.
    complete()` intenta de verdad contra los proveedores configurados y tarda
    ~1.7s en agotar la cadena en este sandbox (sin red) — mucho más que el
    `asyncio.sleep` que usan estos tests para esperar al evento en background.
    Se mockea `app.mel.complete` (la frontera real que usa `router.complete`,
    mismo patrón que `test_audit_new7b_persistencia.py`) para que la síntesis
    sea instantánea y los tests no dependan de la latencia de red real."""
    import app.mel as _mel
    from app.mel.contracts import ExecutionResult

    async def _fake_complete(req):
        return ExecutionResult(text="Listo: la misión terminó correctamente.", ok=True)

    monkeypatch.setattr(_mel, "complete", _fake_complete)


class _FakeRuntime(AgentRuntime):
    def __init__(self):
        self.calls: list[str] = []

    @property
    def capabilities(self):
        return {"chat", "tool_use_basic"}

    async def execute_task(self, task, memory, tools, approval_gate):
        self.calls.append(task.instruction)
        return AgentResult(task_id=task.id, success=True, output=f"hecho: {task.instruction}", tokens=1)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


@pytest.fixture
def fake_rt():
    rt = _FakeRuntime()
    register_runtime("fake6", rt)
    return rt


def _graph(mission_id: str, nodes: list[TaskNode]) -> TaskGraph:
    return TaskGraph(id="g1", mission_id=mission_id, nodes={n.id: n for n in nodes})


def _start(goal="misión de test NEW-6"):
    m = new_mission(goal, source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    return m, trace_id


def _node(nid, goal=None, **kw) -> TaskNode:
    return TaskNode(id=nid, goal=goal or f"paso {nid}", runtime="fake6", **kw)


# ===========================================================================
# finish_and_record — función pura de comportamiento (sin gates de por medio)
# ===========================================================================
@pytest.mark.anyio
async def test_finish_and_record_estado_waiting_escribe_el_placeholder(fake_rt):
    m, trace_id = _start()
    g = _graph(m.id, [_node("n1", "libre")])
    tracer.record_plan(trace_id, g)
    m.state = "waiting"  # simula que executor.run() acaba de pausar

    out = await executor.finish_and_record(g, m, trace_id)

    assert out == _WAITING_PLACEHOLDER
    assert m.outcome == _WAITING_PLACEHOLDER
    assert tracer.get_outcome(trace_id) == _WAITING_PLACEHOLDER
    assert tracer.get_meta(trace_id)["state"] == "waiting"


@pytest.mark.anyio
async def test_finish_and_record_estado_done_sintetiza_y_no_es_el_placeholder(fake_rt):
    m, trace_id = _start()
    g = _graph(m.id, [_node("n1", "libre")])
    g.nodes["n1"].state = NodeState.DONE
    g.nodes["n1"].result = {"output": "resultado real del paso"}
    tracer.record_plan(trace_id, g)
    m.state = "done"

    out = await executor.finish_and_record(g, m, trace_id)

    assert out != _WAITING_PLACEHOLDER
    assert tracer.get_outcome(trace_id) != _WAITING_PLACEHOLDER
    assert tracer.get_meta(trace_id)["state"] == "done"


# ===========================================================================
# LA REGRESIÓN EXACTA: gate de nodo resuelto → el outcome deja de ser el
# placeholder de espera aunque la síntesis del responder no tenga LLM real
# disponible en este entorno (cae a la plantilla determinista, que tampoco es
# el placeholder de espera — eso es justo lo que se verifica).
# ===========================================================================
@pytest.mark.anyio
async def test_gate_de_nodo_aprobado_actualiza_el_outcome_no_deja_el_placeholder(fake_rt):
    executor.register_gate_handlers()
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "libre"),
        _node("n2", "sensible", depends_on=["n1"], approval_required=True),
    ])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)
    # Mismo paso que hacía `pipeline._execute_and_respond` al pausar: el
    # outcome queda con el placeholder mientras el gate está abierto.
    await executor.finish_and_record(g, m, trace_id)
    assert tracer.get_outcome(trace_id) == _WAITING_PLACEHOLDER
    assert tracer.get_meta(trace_id)["state"] == "waiting"

    gate_id = g.nodes["n2"].gate_id
    await approval_gate.resolve(gate_id, approved=True, note="adelante")
    await asyncio.sleep(0.05)  # el evento reanuda en background

    # LA COMPROBACIÓN CLAVE: el estado avanzó a done Y el outcome se
    # actualizó — antes del fix, `state` avanzaba pero `outcome` se quedaba
    # exactamente en `_WAITING_PLACEHOLDER` para siempre.
    assert tracer.get_meta(trace_id)["state"] == "done"
    assert tracer.get_outcome(trace_id) != _WAITING_PLACEHOLDER


@pytest.mark.anyio
async def test_gate_de_nodo_rechazado_tambien_actualiza_el_outcome(fake_rt):
    """No solo el camino aprobado: un rechazo que termina la misión (failed)
    también debe dejar un outcome fresco, no el placeholder de espera."""
    executor.register_gate_handlers()
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "libre"),
        _node("n2", "sensible", depends_on=["n1"], approval_required=True),
    ])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)
    await executor.finish_and_record(g, m, trace_id)

    gate_id = g.nodes["n2"].gate_id
    await approval_gate.resolve(gate_id, approved=False, note="no, gracias")
    await asyncio.sleep(0.05)

    assert tracer.get_meta(trace_id)["state"] == "done"  # n1 sí se completó → done, no failed
    assert tracer.get_outcome(trace_id) != _WAITING_PLACEHOLDER


@pytest.mark.anyio
async def test_checkpoint_aprobado_actualiza_el_outcome_no_deja_el_placeholder(fake_rt):
    """Mismo bug, mismo fix, otro gate: el CHECKPOINT (R5) reanuda por
    `_apply_checkpoint_verdict`, que también pasaba por alto el outcome."""
    executor.register_gate_handlers()
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "entregable", checkpoint=True),
        _node("n2", "despues del checkpoint", depends_on=["n1"]),
    ])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)
    await executor.finish_and_record(g, m, trace_id)
    assert tracer.get_meta(trace_id)["state"] == "waiting"

    gate_id = g.nodes["n1"].checkpoint_gate_id
    assert gate_id is not None
    await approval_gate.resolve(gate_id, approved=True, note="adelante")
    await asyncio.sleep(0.05)

    assert tracer.get_meta(trace_id)["state"] == "done"
    assert tracer.get_outcome(trace_id) != _WAITING_PLACEHOLDER


# ===========================================================================
# No-regresión: el camino normal (sin gates) sigue funcionando igual
# ===========================================================================
@pytest.mark.anyio
async def test_mision_sin_gates_sigue_terminando_normal(fake_rt):
    m, trace_id = _start()
    g = _graph(m.id, [_node("n1", "libre")])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)
    await executor.finish_and_record(g, m, trace_id)

    assert tracer.get_meta(trace_id)["state"] == "done"
    assert tracer.get_outcome(trace_id) != _WAITING_PLACEHOLDER
    assert "libre" in fake_rt.calls
