# tests/test_tie_executor.py — Graph Execution Engine (V1.0 T3, doc 14 §3.4)
#
# El executor ES el corazón del TIE: si falla, una misión puede quedarse colgada,
# ejecutar algo sin permiso, o perderse en un reinicio. Estos tests blindan las 6
# garantías del diseño: orden del ready-set, checkpoint por transición, gates que
# pausan y reanudan (aprobado Y rechazado), degradación ante fallo, kill-switch, y
# reanudación tras reinicio (incluido el gate resuelto con el backend caído).
#
# Se usa un runtime FAKE registrado en el registro real: demuestra de paso que un
# runtime nuevo funciona sin tocar el executor (doc 10) — el mismo contrato que
# usará HermesRuntime en V1.1.
import asyncio

import pytest

from app.automation import Approval, approval_gate
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


# ---------------------------------------------------------------------------
# Runtime fake — un runtime NUEVO, sin tocar el executor (contrato doc 10)
# ---------------------------------------------------------------------------
class _FakeRuntime(AgentRuntime):
    def __init__(self):
        self.calls: list[str] = []
        self.fail_on: set[str] = set()
        self.slow_on: set[str] = set()

    @property
    def capabilities(self):
        return {"chat", "tool_use_basic"}

    async def execute_task(self, task, memory, tools, approval_gate):
        self.calls.append(task.instruction)
        if task.instruction in self.slow_on:
            await asyncio.sleep(30)  # se cancelará (kill-switch)
        if task.instruction in self.fail_on:
            return AgentResult(task_id=task.id, success=False, error="fallo simulado")
        return AgentResult(task_id=task.id, success=True, output=f"hecho: {task.instruction}", tokens=5)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


@pytest.fixture
def fake_rt():
    rt = _FakeRuntime()
    register_runtime("fake", rt)
    return rt


def _graph(mission_id: str, nodes: list[TaskNode]) -> TaskGraph:
    return TaskGraph(id="g1", mission_id=mission_id, nodes={n.id: n for n in nodes})


def _start(goal="misión de test"):
    """Crea misión + traza + devuelve (mission, trace_id) como en el pipeline real."""
    m = new_mission(goal, source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    return m, trace_id


def _node(nid, goal=None, **kw) -> TaskNode:
    return TaskNode(id=nid, goal=goal or f"paso {nid}", runtime="fake", **kw)


# ---------------------------------------------------------------------------
# Loop de olas + orden + checkpoint
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_grafo_lineal_ejecuta_en_orden(fake_rt):
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "primero"),
        _node("n2", "segundo", depends_on=["n1"]),
        _node("n3", "tercero", depends_on=["n2"]),
    ])
    tracer.record_plan(trace_id, g)

    out = await executor.run(g, m, trace_id=trace_id)

    assert fake_rt.calls == ["primero", "segundo", "tercero"]
    assert all(n.state == NodeState.DONE for n in g.nodes.values())
    assert out.state == "done"


@pytest.mark.anyio
async def test_ready_set_descubre_ramas_independientes(fake_rt):
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("root", "raiz"),
        _node("a", "rama A", depends_on=["root"]),
        _node("b", "rama B", depends_on=["root"]),
        _node("join", "union", depends_on=["a", "b"]),
    ])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert fake_rt.calls[0] == "raiz"
    assert fake_rt.calls[-1] == "union"
    assert set(fake_rt.calls[1:3]) == {"rama A", "rama B"}
    assert all(n.state == NodeState.DONE for n in g.nodes.values())


@pytest.mark.anyio
async def test_checkpoint_persiste_el_grafo_en_cada_transicion(fake_rt):
    m, trace_id = _start()
    g = _graph(m.id, [_node("n1", "unico")])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    # El grafo en DISCO refleja el estado final (no solo el objeto en memoria):
    # es lo que hace posible reanudar tras un reinicio.
    persisted = tracer.load_graph(trace_id)
    assert persisted is not None
    assert persisted.nodes["n1"].state == NodeState.DONE
    assert persisted.nodes["n1"].result == {"output": "hecho: unico"}


@pytest.mark.anyio
async def test_validacion_por_nodo_escribe_veredicto(fake_rt):
    m, trace_id = _start()
    g = _graph(m.id, [_node("n1", "con salida")])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert g.nodes["n1"].validation == {"ok": True, "method": "schema", "notes": ""}


@pytest.mark.anyio
async def test_nodo_sin_salida_no_pasa_la_validacion(fake_rt):
    """Un runtime que dice success=True pero no produce NADA no cuela: la
    validación determinista lo marca como fallo (nunca teatro)."""
    class _EmptyRuntime(_FakeRuntime):
        async def execute_task(self, task, memory, tools, approval_gate):
            return AgentResult(task_id=task.id, success=True, output="")
    register_runtime("empty", _EmptyRuntime())

    m, trace_id = _start()
    g = _graph(m.id, [TaskNode(id="n1", goal="vacio", runtime="empty")])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert g.nodes["n1"].state == NodeState.FAILED
    assert g.nodes["n1"].validation["ok"] is False


# ---------------------------------------------------------------------------
# Recovery — degradación graciosa
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_nodo_fallido_salta_sus_dependientes_transitivos(fake_rt):
    fake_rt.fail_on = {"rompe"}
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("ok1", "va bien"),
        _node("bad", "rompe", depends_on=["ok1"]),
        _node("dep1", "depende del roto", depends_on=["bad"]),
        _node("dep2", "depende del anterior", depends_on=["dep1"]),
    ])
    tracer.record_plan(trace_id, g)

    out = await executor.run(g, m, trace_id=trace_id)

    assert g.nodes["ok1"].state == NodeState.DONE
    assert g.nodes["bad"].state == NodeState.FAILED
    assert g.nodes["dep1"].state == NodeState.SKIPPED   # directo
    assert g.nodes["dep2"].state == NodeState.SKIPPED   # transitivo
    assert "depende de bad" in (g.nodes["dep1"].error or "")
    # degradación graciosa: algo útil se hizo → la misión NO es un fracaso total
    assert out.state == "done"
    assert "rompe" not in [c for c in fake_rt.calls if c in ("depende del roto",)]


@pytest.mark.anyio
async def test_mision_sin_nada_util_es_failed(fake_rt):
    fake_rt.fail_on = {"unico paso"}
    m, trace_id = _start()
    g = _graph(m.id, [_node("n1", "unico paso")])
    tracer.record_plan(trace_id, g)

    out = await executor.run(g, m, trace_id=trace_id)
    assert out.state == "failed"


# ---------------------------------------------------------------------------
# Gates — HITL como estado de primera clase
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_gate_pausa_el_grafo_y_no_ejecuta_el_nodo(fake_rt):
    executor.register_gate_handlers()
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "libre"),
        _node("n2", "sensible", depends_on=["n1"], approval_required=True),
    ])
    tracer.record_plan(trace_id, g)

    out = await executor.run(g, m, trace_id=trace_id)

    assert out.state == "waiting"
    assert g.nodes["n2"].state == NodeState.WAITING_APPROVAL
    assert g.nodes["n2"].gate_id is not None
    assert "sensible" not in fake_rt.calls          # NO se ejecutó sin permiso
    assert tracer.get_meta(trace_id)["state"] == "waiting"
    # hay una aprobación pendiente real esperando al usuario
    pending = [a for a in approval_gate.list_pending() if a.id == g.nodes["n2"].gate_id]
    assert len(pending) == 1 and pending[0].kind == "tie.node"


@pytest.mark.anyio
async def test_gate_aprobado_reanuda_y_termina(fake_rt):
    executor.register_gate_handlers()
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "libre"),
        _node("n2", "sensible", depends_on=["n1"], approval_required=True),
        _node("n3", "despues del gate", depends_on=["n2"]),
    ])
    tracer.record_plan(trace_id, g)
    await executor.run(g, m, trace_id=trace_id)
    gate_id = g.nodes["n2"].gate_id

    # el usuario aprueba (como haría POST /api/automation/approvals/{id}/resolve)
    await approval_gate.resolve(gate_id, approved=True, note="adelante")
    await asyncio.sleep(0.05)  # el evento reanuda en background (emit → create_task)

    final = tracer.load_graph(trace_id)
    assert final.nodes["n2"].state == NodeState.DONE
    assert final.nodes["n3"].state == NodeState.DONE
    assert "sensible" in fake_rt.calls and "despues del gate" in fake_rt.calls


@pytest.mark.anyio
async def test_gate_rechazado_degrada_sin_ejecutar(fake_rt):
    executor.register_gate_handlers()
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "libre"),
        _node("n2", "sensible", depends_on=["n1"], approval_required=True),
        _node("n3", "despues del gate", depends_on=["n2"]),
    ])
    tracer.record_plan(trace_id, g)
    await executor.run(g, m, trace_id=trace_id)
    gate_id = g.nodes["n2"].gate_id

    await approval_gate.resolve(gate_id, approved=False, note="no, gracias")
    await asyncio.sleep(0.05)

    final = tracer.load_graph(trace_id)
    assert final.nodes["n2"].state == NodeState.FAILED
    assert "rechazó" in (final.nodes["n2"].error or "")
    assert final.nodes["n3"].state == NodeState.SKIPPED
    assert "sensible" not in fake_rt.calls          # jamás se ejecutó
    assert "despues del gate" not in fake_rt.calls


@pytest.mark.anyio
async def test_gate_no_interfiere_con_aprobaciones_de_otros(fake_rt):
    """El handler del TIE ignora los gates que no son suyos (p.ej. un email_send
    del AE) — no puede romper el ApprovalGate compartido."""
    executor.register_gate_handlers()
    ran = {"n": 0}

    async def _other(payload):
        ran["n"] += 1
        return "ok"
    approval_gate.register_executor("otro_action", _other)

    gid = await approval_gate.request_approval(
        kind="otro.kind", title="ajeno al TIE", action_type="otro_action"
    )
    res = await approval_gate.resolve(gid, approved=True)
    await asyncio.sleep(0.05)
    assert res.executed is True and ran["n"] == 1


# ---------------------------------------------------------------------------
# Kill-switch
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_kill_switch_cancela_los_nodos_pendientes(fake_rt):
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "primero"),
        _node("n2", "segundo", depends_on=["n1"]),
    ])
    tracer.record_plan(trace_id, g)

    executor.cancel(m.id)  # el usuario pulsa "parar" antes de empezar
    out = await executor.run(g, m, trace_id=trace_id)

    assert out.state == "cancelled"
    assert g.nodes["n1"].state == NodeState.CANCELLED
    assert g.nodes["n2"].state == NodeState.CANCELLED
    assert fake_rt.calls == []
    assert tracer.get_meta(trace_id)["state"] == "cancelled"


@pytest.mark.anyio
async def test_kill_switch_corta_el_nodo_en_vuelo(fake_rt):
    """Cancelación COOPERATIVA: no se espera a que el nodo lento termine (30s),
    se le interrumpe (< 2 s, doc 14 §6)."""
    fake_rt.slow_on = {"tarda muchisimo"}
    m, trace_id = _start()
    g = _graph(m.id, [_node("n1", "tarda muchisimo")])
    tracer.record_plan(trace_id, g)

    async def _cancel_soon():
        await asyncio.sleep(0.05)
        executor.cancel(m.id)

    t0 = asyncio.get_event_loop().time()
    await asyncio.gather(executor.run(g, m, trace_id=trace_id), _cancel_soon())
    elapsed = asyncio.get_event_loop().time() - t0

    assert elapsed < 2.0                              # no esperó los 30 s
    assert g.nodes["n1"].state == NodeState.CANCELLED


# ---------------------------------------------------------------------------
# Reanudación tras reinicio (doc 14 §3.4.3)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_resume_pending_continua_un_grafo_a_medias(fake_rt):
    """Simula un reinicio: la traza queda `running` con un nodo hecho y otro
    pendiente; un executor "nuevo" (sin estado en RAM) la termina leyendo disco."""
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "ya hecho"),
        _node("n2", "pendiente tras reinicio", depends_on=["n1"]),
    ])
    g.nodes["n1"].state = NodeState.DONE
    tracer.record_plan(trace_id, g)
    tracer.set_state(trace_id, "running")

    n = await executor.resume_pending()   # <- el "arranque" del backend

    assert n == 1
    final = tracer.load_graph(trace_id)
    assert final.nodes["n2"].state == NodeState.DONE
    assert "pendiente tras reinicio" in fake_rt.calls


@pytest.mark.anyio
async def test_resume_pending_respeta_un_gate_aun_sin_resolver(fake_rt):
    executor.register_gate_handlers()
    m, trace_id = _start()
    g = _graph(m.id, [_node("n1", "sensible", approval_required=True)])
    tracer.record_plan(trace_id, g)
    await executor.run(g, m, trace_id=trace_id)   # se queda esperando

    n = await executor.resume_pending()

    assert n == 0                                  # no hay nada que reanudar aún
    assert tracer.load_graph(trace_id).nodes["n1"].state == NodeState.WAITING_APPROVAL
    assert "sensible" not in fake_rt.calls


@pytest.mark.anyio
async def test_resume_pending_aplica_un_gate_resuelto_con_el_backend_caido(fake_rt):
    """El caso feo: el usuario aprueba mientras el backend está apagado. El bus es
    in-process y sin persistencia (doc 17) → ese evento SE PIERDE. La reanudación
    lo recupera consultando el veredicto en disco."""
    executor.register_gate_handlers()
    m, trace_id = _start()
    g = _graph(m.id, [
        _node("n1", "sensible", approval_required=True),
        _node("n2", "el siguiente", depends_on=["n1"]),
    ])
    tracer.record_plan(trace_id, g)
    await executor.run(g, m, trace_id=trace_id)
    gate_id = g.nodes["n1"].gate_id

    # Se resuelve la aprobación "sin que el TIE escuche" (backend caído):
    from app.core.events import unsubscribe
    unsubscribe("approval.resolved", executor._on_approval_resolved)
    await approval_gate.resolve(gate_id, approved=True, note="aprobado offline")
    await asyncio.sleep(0.05)
    assert tracer.load_graph(trace_id).nodes["n1"].state == NodeState.WAITING_APPROVAL  # nadie reanudó

    # Arranca el backend: resume_pending ve el veredicto y sigue.
    executor.register_gate_handlers()
    n = await executor.resume_pending()

    assert n == 1
    final = tracer.load_graph(trace_id)
    assert final.nodes["n1"].state == NodeState.DONE
    assert final.nodes["n2"].state == NodeState.DONE
