# tests/test_tie_handle.py — pipeline completo del TIE (V1.0 T4a, doc 21 §3·T4)
#
# Lo que T4a añade sobre T1-T3: el pipeline de verdad (planner → gate del plan →
# executor → responder), los eventos mission.*, y los endpoints /api/tie.
#
# Lo MÁS importante que se blinda aquí: **el camino corto debe seguir siendo
# idéntico** — el switch del Gateway hace que TODO el chat pase por el TIE, y el
# ~80% de las queries no puede notarlo.
import asyncio

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
    handle,
    register_handlers,
    register_runtime,
    submit_mission,
    tracer,
)
from app.tie import pipeline as pipeline_mod


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    register_handlers()
    yield
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(Approval).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


class _Env:
    def __init__(self, text, channel="electron"):
        self.text = text
        self.channel = channel
        self.user_ref = "u1"


class _Rt(AgentRuntime):
    def __init__(self):
        self.calls = []

    @property
    def capabilities(self):
        return {"chat"}

    async def execute_task(self, task, memory, tools, approval_gate):
        self.calls.append(task.instruction)
        return AgentResult(task_id=task.id, success=True, output=f"ok: {task.instruction}", tokens=2)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


def _fake_short_chat(monkeypatch, text="respuesta corta"):
    from app.services import chat_service

    class _A:
        def __init__(self):
            self.text = text
            self.model = "fake"
            self.tokens = 3
    async def _answer(message, *, channel="web", persist_chat_message=True):
        return _A()
    monkeypatch.setattr(chat_service, "answer", _answer)


def _fake_intent(monkeypatch, intent: Intent):
    async def _classify(text, *, channel=None):
        return intent
    monkeypatch.setattr(pipeline_mod.intents, "classify", _classify)


def _fake_plan(monkeypatch, graph):
    async def _plan(goal, intent, *, context="", mission_id=None, trace_id=None):
        if graph is not None:
            graph.mission_id = mission_id or graph.mission_id
            if trace_id:
                tracer.record_plan(trace_id, graph)
        return graph
    monkeypatch.setattr(pipeline_mod.planner, "plan", _plan)


def _fake_responder(monkeypatch):
    async def _build(mission, graph):
        mission.outcome = f"resumen de {len([n for n in graph.nodes.values() if n.state == NodeState.DONE])} paso(s)"
        return mission.outcome
    monkeypatch.setattr(pipeline_mod.responder, "build", _build)


# ---------------------------------------------------------------------------
# El camino corto NO puede cambiar (el switch afecta a todo el chat)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_camino_corto_responde_identico_y_no_planifica(monkeypatch):
    _fake_intent(monkeypatch, Intent(type=IntentType.CONVERSATIONAL, goal="hola", confidence=0.9))
    _fake_short_chat(monkeypatch, "hola, soy Aithera")

    planned = {"n": 0}
    async def _plan(*a, **k):
        planned["n"] += 1
        return None
    monkeypatch.setattr(pipeline_mod.planner, "plan", _plan)

    out = await handle(_Env("hola"))

    assert out == "hola, soy Aithera"
    assert planned["n"] == 0          # el ~80% NUNCA paga el planner (doc 14 §6)


@pytest.mark.anyio
async def test_handle_nunca_lanza_aunque_todo_falle(monkeypatch):
    async def _boom(text, *, channel=None):
        raise RuntimeError("clasificador roto")
    monkeypatch.setattr(pipeline_mod.intents, "classify", _boom)

    out = await handle(_Env("lo que sea"))
    assert isinstance(out, str) and out  # respuesta útil, no una excepción


# ---------------------------------------------------------------------------
# Camino complejo: planner → executor → responder
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_query_compleja_planifica_ejecuta_y_responde(monkeypatch):
    rt = _Rt()
    register_runtime("t4rt", rt)
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="haz A y luego B", confidence=0.9, requires_planning=True,
    ))
    g = TaskGraph(id="g1", mission_id="m1", nodes={
        "n1": TaskNode(id="n1", goal="paso A", runtime="t4rt"),
        "n2": TaskNode(id="n2", goal="paso B", runtime="t4rt", depends_on=["n1"]),
    })
    _fake_plan(monkeypatch, g)
    _fake_responder(monkeypatch)

    out = await handle(_Env("haz A y luego B"))

    assert rt.calls == ["paso A", "paso B"]
    assert "2 paso" in out
    assert all(n.state == NodeState.DONE for n in g.nodes.values())


@pytest.mark.anyio
async def test_sin_plan_valido_degrada_al_camino_corto(monkeypatch):
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="algo complejo", confidence=0.9, requires_planning=True,
    ))
    _fake_plan(monkeypatch, None)      # el planner no logró un grafo válido
    _fake_short_chat(monkeypatch, "te respondo igualmente")

    out = await handle(_Env("algo complejo"))
    assert out == "te respondo igualmente"   # el usuario recibe algo (regla 11-B)


# ---------------------------------------------------------------------------
# Gate del PLAN — transparencia antes de ejecutar nada
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_plan_sensible_pide_aprobacion_y_no_ejecuta_nada(monkeypatch):
    rt = _Rt()
    register_runtime("t4rt", rt)
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="envía el email", confidence=0.9, requires_planning=True,
    ))
    g = TaskGraph(id="g2", mission_id="m2", nodes={
        "n1": TaskNode(id="n1", goal="redactar", runtime="t4rt"),
        "n2": TaskNode(id="n2", goal="enviar email", runtime="t4rt",
                       depends_on=["n1"], approval_required=True),
    })
    _fake_plan(monkeypatch, g)

    out = await handle(_Env("envía el email"))

    assert "visto bueno" in out and "redactar" in out and "enviar email" in out
    assert rt.calls == []                       # NADA se ejecutó: ni el paso libre
    pending = [a for a in approval_gate.list_pending() if a.kind == "tie.plan"]
    assert len(pending) == 1


@pytest.mark.anyio
async def test_plan_aprobado_ejecuta_sin_volver_a_preguntar(monkeypatch):
    """Aprobar el PLAN autoriza sus pasos sensibles: el usuario ya vio la lista
    entera. No se le pregunta otra vez nodo por nodo (pero queda auditado: cada
    nodo apunta al gate del plan que lo autorizó)."""
    rt = _Rt()
    register_runtime("t4rt", rt)
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="envía el email", confidence=0.9, requires_planning=True,
    ))
    g = TaskGraph(id="g3", mission_id="m3", nodes={
        "n1": TaskNode(id="n1", goal="redactar", runtime="t4rt"),
        "n2": TaskNode(id="n2", goal="enviar email", runtime="t4rt",
                       depends_on=["n1"], approval_required=True),
    })
    _fake_plan(monkeypatch, g)
    _fake_responder(monkeypatch)

    await handle(_Env("envía el email"))
    gate = [a for a in approval_gate.list_pending() if a.kind == "tie.plan"][0]
    trace_id = gate.action_payload["trace_id"]

    await approval_gate.resolve(gate.id, approved=True, note="adelante")
    await asyncio.sleep(0.05)   # reanudación en background

    final = tracer.load_graph(trace_id)
    assert final.nodes["n1"].state == NodeState.DONE
    assert final.nodes["n2"].state == NodeState.DONE
    assert rt.calls == ["redactar", "enviar email"]
    assert final.nodes["n2"].gate_id == gate.id      # rastro de quién lo autorizó
    # y NO se abrió un segundo gate de nodo para lo mismo
    assert [a for a in approval_gate.list_pending() if a.kind == "tie.node"] == []


@pytest.mark.anyio
async def test_plan_rechazado_no_ejecuta_nada(monkeypatch):
    rt = _Rt()
    register_runtime("t4rt", rt)
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="envía el email", confidence=0.9, requires_planning=True,
    ))
    g = TaskGraph(id="g4", mission_id="m4", nodes={
        "n1": TaskNode(id="n1", goal="enviar email", runtime="t4rt", approval_required=True),
    })
    _fake_plan(monkeypatch, g)

    await handle(_Env("envía el email"))
    gate = [a for a in approval_gate.list_pending() if a.kind == "tie.plan"][0]
    trace_id = gate.action_payload["trace_id"]

    await approval_gate.resolve(gate.id, approved=False, note="no")
    await asyncio.sleep(0.05)

    final = tracer.load_graph(trace_id)
    assert final.state == "cancelled"
    assert final.nodes["n1"].state == NodeState.CANCELLED
    assert rt.calls == []
    assert tracer.get_meta(trace_id)["state"] == "cancelled"


# ---------------------------------------------------------------------------
# submit_mission (la entrada del AE/WPMS) — nunca camino corto
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_submit_mission_siempre_planifica(monkeypatch):
    rt = _Rt()
    register_runtime("t4rt", rt)
    # aunque el clasificador diga "charla", una misión explícita se planifica
    _fake_intent(monkeypatch, Intent(type=IntentType.CONVERSATIONAL, goal="tarea del AE", confidence=0.9))
    g = TaskGraph(id="g5", mission_id="m5", nodes={
        "n1": TaskNode(id="n1", goal="hacer la tarea", runtime="t4rt"),
    })
    _fake_plan(monkeypatch, g)
    _fake_responder(monkeypatch)

    m = await submit_mission("tarea del AE", source="automation", channel="hub")

    assert m.state == "done" and m.source == "automation"
    assert rt.calls == ["hacer la tarea"]


# ---------------------------------------------------------------------------
# Eventos mission.*
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_eventos_mission_started_y_completed(monkeypatch):
    from app.core.events import subscribe, unsubscribe

    got = []
    async def _h(ev):
        got.append(ev.name)
    for name in ("mission.started", "mission.completed"):
        subscribe(name, _h)
    try:
        _fake_intent(monkeypatch, Intent(type=IntentType.CONVERSATIONAL, goal="hola", confidence=0.9))
        _fake_short_chat(monkeypatch)
        await handle(_Env("hola"))
        await asyncio.sleep(0.05)
        assert "mission.started" in got and "mission.completed" in got
    finally:
        for name in ("mission.started", "mission.completed"):
            unsubscribe(name, _h)


# ---------------------------------------------------------------------------
# Endpoints /api/tie
# ---------------------------------------------------------------------------
def test_endpoint_list_y_get_mission(client, monkeypatch):
    from app.tie import new_mission

    m = new_mission("misión de test", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = TaskGraph(id="ge", mission_id=m.id, nodes={"n1": TaskNode(id="n1", goal="paso")})
    tracer.record_plan(trace_id, g)

    r = client.get("/api/tie/missions")
    assert r.status_code == 200
    assert any(x["trace_id"] == trace_id for x in r.json())

    r2 = client.get(f"/api/tie/missions/{trace_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["graph"]["nodes"]["n1"]["goal"] == "paso"
    assert body["node_count"] == 1


def test_endpoint_get_mission_404(client):
    assert client.get("/api/tie/missions/no-existe").status_code == 404


def test_endpoint_cancel_mission(client):
    from app.tie import new_mission

    m = new_mission("cancelable", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")

    r = client.post(f"/api/tie/missions/{trace_id}/cancel")
    assert r.status_code == 200 and r.json()["cancelled"] is True

    from app.tie import executor
    assert executor.is_cancelled(m.id)
    executor._CANCELLED.discard(m.id)


def test_endpoint_approve_plan_sin_plan_pendiente_404(client):
    from app.tie import new_mission

    m = new_mission("sin plan", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    r = client.post(f"/api/tie/missions/{trace_id}/approve-plan", json={"approved": True})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Borrado + limpieza automática de misiones (fix real, 2026-07-17)
# ---------------------------------------------------------------------------
def test_endpoint_delete_mission_terminada(client):
    from app.tie import new_mission

    m = new_mission("terminada", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    tracer.record_end(trace_id, outcome="listo", state="done")

    r = client.delete(f"/api/tie/missions/{trace_id}")
    assert r.status_code == 200 and r.json()["deleted"] is True
    assert client.get(f"/api/tie/missions/{trace_id}").status_code == 404


def test_endpoint_delete_mission_viva_409():
    from app.tie import new_mission

    m = new_mission("en curso", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")  # nace en state="running"

    ok, reason = tracer.delete_trace(trace_id)
    assert ok is False and reason == "live"
    # sigue existiendo tras el intento fallido
    assert tracer.get_meta(trace_id) is not None


def test_endpoint_delete_mission_inexistente_404(client):
    r = client.delete("/api/tie/missions/no-existe")
    assert r.status_code == 404


def test_endpoint_delete_mission_viva_devuelve_409(client):
    from app.tie import new_mission

    m = new_mission("en curso via http", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    r = client.delete(f"/api/tie/missions/{trace_id}")
    assert r.status_code == 409


def test_purge_old_borra_solo_terminadas_y_viejas():
    from datetime import datetime, timedelta

    from app.db.database import OrchestratorTrace, SessionLocal
    from app.tie import new_mission

    # terminada y vieja -> debe borrarse
    m_old = new_mission("vieja terminada", source="user", channel="hub")
    old_id = tracer.record_start(m_old, channel="hub")
    tracer.record_end(old_id, outcome="x", state="done")

    # terminada pero reciente -> NO debe borrarse
    m_recent = new_mission("reciente terminada", source="user", channel="hub")
    recent_id = tracer.record_start(m_recent, channel="hub")
    tracer.record_end(recent_id, outcome="x", state="done")

    # viva y vieja -> NUNCA se borra, por vieja que sea
    m_live = new_mission("vieja pero viva", source="user", channel="hub")
    live_id = tracer.record_start(m_live, channel="hub")

    # retrasamos artificialmente `updated_at` de la vieja y de la viva
    s = SessionLocal()
    try:
        old_ts = datetime.utcnow() - timedelta(days=60)
        s.query(OrchestratorTrace).filter(OrchestratorTrace.id == old_id).update({"updated_at": old_ts})
        s.query(OrchestratorTrace).filter(OrchestratorTrace.id == live_id).update({"updated_at": old_ts})
        s.commit()
    finally:
        s.close()

    n = tracer.purge_old(retention_days=30)

    assert n == 1
    assert tracer.get_meta(old_id) is None       # borrada
    assert tracer.get_meta(recent_id) is not None  # conservada (reciente)
    assert tracer.get_meta(live_id) is not None    # conservada (viva, aunque vieja)


def test_purge_old_desactivado_con_cero():
    from app.tie import new_mission

    m = new_mission("terminada", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    tracer.record_end(trace_id, outcome="x", state="done")

    assert tracer.purge_old(retention_days=0) == 0
    assert tracer.get_meta(trace_id) is not None


# ---------------------------------------------------------------------------
# Streaming (T4b) — lo que ve el chat de Electron
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_handle_stream_camino_corto_emite_status_y_tokens(monkeypatch):
    """El camino corto debe seguir streameando TOKENS (el UX de siempre), con un
    'analizando' delante para que el primer feedback sea inmediato (doc 11 B.5)."""
    from app.tie import handle_stream
    from app.tie.runtime import AgentChunk

    _fake_intent(monkeypatch, Intent(type=IntentType.CONVERSATIONAL, goal="hola", confidence=0.9))

    async def _stream(self, task, memory, tools, approval_gate):
        for tok in ("Hola", ", ", "soy Aithera"):
            yield AgentChunk(task_id=task.id, kind="text", payload=tok)
    from app.tie.runtime import NullRuntime
    monkeypatch.setattr(NullRuntime, "stream_task", _stream)

    kinds, texts = [], ""
    async for kind, payload in handle_stream("hola", channel="web"):
        kinds.append(kind)
        if kind == "text":
            texts += payload

    assert kinds[0] == "status" and kinds.count("text") == 3
    assert texts == "Hola, soy Aithera"
    assert "mission" not in kinds          # el camino corto no crea misión que seguir


@pytest.mark.anyio
async def test_handle_stream_complejo_emite_mission_y_respuesta(monkeypatch):
    """El camino complejo avisa de que hay una misión (para poder verla/aprobarla)
    y entrega la respuesta del responder."""
    from app.tie import handle_stream

    rt = _Rt()
    register_runtime("t4rt", rt)
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="haz A", confidence=0.9, requires_planning=True,
    ))
    g = TaskGraph(id="gs", mission_id="ms", nodes={
        "n1": TaskNode(id="n1", goal="paso A", runtime="t4rt"),
    })
    _fake_plan(monkeypatch, g)
    _fake_responder(monkeypatch)

    events = [(k, p) async for k, p in handle_stream("haz A", channel="web")]
    kinds = [k for k, _ in events]

    assert kinds[0] == "status"                     # "analizando"
    assert "planificando" in [p for k, p in events if k == "status"]
    assert "mission" in kinds                       # hay misión que seguir
    assert any(k == "text" and "1 paso" in p for k, p in events)


@pytest.mark.anyio
async def test_handle_stream_nunca_lanza(monkeypatch):
    from app.tie import handle_stream

    async def _boom(text, *, channel=None):
        raise RuntimeError("clasificador roto")
    monkeypatch.setattr(pipeline_mod.intents, "classify", _boom)
    _fake_short_chat(monkeypatch, "igualmente respondo")

    from app.tie.runtime import AgentChunk, NullRuntime
    async def _stream(self, task, memory, tools, approval_gate):
        yield AgentChunk(task_id=task.id, kind="text", payload="igualmente respondo")
    monkeypatch.setattr(NullRuntime, "stream_task", _stream)

    out = "".join([p async for k, p in handle_stream("x", channel="web") if k == "text"])
    assert out == "igualmente respondo"   # degradó a conversational y respondió
