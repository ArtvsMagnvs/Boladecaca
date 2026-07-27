# tests/test_voz4_background.py — misiones en segundo plano (A·VOZ-4, doc 32)
#
# El contrato que se blinda: en MODO CONVERSACIÓN una misión no bloquea el turno
# —se acusa recibo al instante y se ejecuta detrás—, y al terminar (o al pausar
# en un gate) se avisa por el canal. En MODO TEXTO, comportamiento clásico intacto.
import asyncio

import pytest

from app.automation import Approval, approval_gate
from app.core import notify as notify_mod
from app.db.database import (
    Base, ChatMessage, OrchestratorTrace, SessionLocal, engine as db_engine,
)
from app.tie import (
    AgentResult, AgentRuntime, Intent, IntentType, NodeState, RuntimeHealth,
    TaskGraph, TaskNode, conversation, register_handlers, register_runtime, tracer,
)
from app.tie import pipeline as pipeline_mod


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    register_handlers()               # incluye conversation.register_handlers() (A·VOZ-4)
    conversation._reset_for_tests()
    yield
    conversation._reset_for_tests()
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(Approval).delete()
        s.query(ChatMessage).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


# --- fakes ------------------------------------------------------------------
class _Rt(AgentRuntime):
    def __init__(self, gate: asyncio.Event | None = None):
        self.calls = []
        self.gate = gate

    @property
    def capabilities(self):
        return {"chat"}

    async def execute_task(self, task, memory, tools, approval_gate):
        if self.gate is not None:
            await self.gate.wait()     # bloquea hasta que el test lo libere
        self.calls.append(task.instruction)
        return AgentResult(task_id=task.id, success=True, output=f"ok: {task.instruction}", tokens=1)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


def _fake_intent(monkeypatch, intent: Intent):
    async def _classify(text, *, channel=None):
        return intent
    monkeypatch.setattr(pipeline_mod.intents, "classify", _classify)


def _fake_plan(monkeypatch, graph):
    async def _plan(goal, intent, *, context="", mission_id=None, trace_id=None, authority=None):
        if graph is not None:
            graph.mission_id = mission_id or graph.mission_id
            if trace_id:
                tracer.record_plan(trace_id, graph)
        return graph
    monkeypatch.setattr(pipeline_mod.planner, "plan", _plan)


def _fake_responder(monkeypatch, text="misión terminada"):
    async def _build(mission, graph):
        mission.outcome = text
        return text
    monkeypatch.setattr(pipeline_mod.responder, "build", _build)


def _capture_notify(monkeypatch):
    got = []
    async def _nu(text, *, channel=None):
        got.append((text, channel))
        return False
    monkeypatch.setattr(notify_mod, "notify_user", _nu)
    return got


async def _drain(gen):
    evs = []
    async for ev in gen:
        evs.append(ev)
    return evs


async def _settle():
    """Deja correr las tasks de fondo (ejecución + handler del bus)."""
    for _ in range(40):
        await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# 1) Modo conversación: acuse inmediato, la ejecución NO bloquea el turno
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_conversacion_acusa_recibo_sin_esperar_a_la_mision(monkeypatch):
    gate = asyncio.Event()             # la ejecución se queda bloqueada aquí
    rt = _Rt(gate=gate)
    register_runtime("voz4rt", rt)
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="haz algo largo", confidence=0.9, requires_planning=True))
    _fake_plan(monkeypatch, TaskGraph(id="g1", mission_id="m1", nodes={
        "n1": TaskNode(id="n1", goal="paso largo", runtime="voz4rt")}))
    _fake_responder(monkeypatch)

    evs = await _drain(pipeline_mod.handle_stream(
        "haz algo largo", channel="electron", conversational=True, session_id="s1"))

    # El turno se cierra con el acuse AUNQUE la ejecución siga bloqueada.
    kinds = [k for k, _ in evs]
    assert "mission" in kinds                       # el usuario puede abrir la misión
    text = [p for k, p in evs if k == "text"][-1]
    assert text == conversation.acuse_text()
    assert rt.calls == []                            # NADA se ejecutó todavía

    gate.set()                                       # ahora que termine
    await _settle()
    assert rt.calls == ["paso largo"]                # corrió en segundo plano


# ---------------------------------------------------------------------------
# 2) Al terminar, reporta por el canal (cola web + notify)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_conversacion_reporta_al_terminar(monkeypatch):
    notes = _capture_notify(monkeypatch)
    register_runtime("voz4rt2", _Rt())
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="tarea", confidence=0.9, requires_planning=True))
    _fake_plan(monkeypatch, TaskGraph(id="g2", mission_id="m2", nodes={
        "n1": TaskNode(id="n1", goal="p", runtime="voz4rt2")}))
    _fake_responder(monkeypatch, "he hecho la tarea")

    await _drain(pipeline_mod.handle_stream(
        "tarea", channel="electron", conversational=True, session_id="s2"))
    await _settle()

    reports = conversation.pending_reports("s2")
    assert len(reports) == 1
    assert "he hecho la tarea" in reports[0]["text"]
    # También se intentó el push por canal y se persistió en el historial.
    assert notes and "he hecho la tarea" in notes[0][0]
    db = SessionLocal()
    try:
        rows = db.query(ChatMessage).filter(ChatMessage.session_id == "s2",
                                            ChatMessage.role == "assistant").all()
        assert any("he hecho la tarea" in (r.content or "") for r in rows)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3) Modo texto (default): comportamiento clásico, sin acuse ni fondo
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_modo_texto_es_clasico_inline(monkeypatch):
    register_runtime("voz4rt3", _Rt())
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="tarea", confidence=0.9, requires_planning=True))
    _fake_plan(monkeypatch, TaskGraph(id="g3", mission_id="m3", nodes={
        "n1": TaskNode(id="n1", goal="p", runtime="voz4rt3")}))
    _fake_responder(monkeypatch, "resultado inline")

    evs = await _drain(pipeline_mod.handle_stream(
        "tarea", channel="electron", conversational=False, session_id="s3"))

    text = [p for k, p in evs if k == "text"][-1]
    assert text == "resultado inline"                # la respuesta REAL, no un acuse
    assert text != conversation.acuse_text()
    assert conversation.pending_reports("s3") == []  # nada de reporte async


# ---------------------------------------------------------------------------
# 4) Charla en conversación: responde ya, sin misión ni reporte
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_charla_en_conversacion_no_crea_mision(monkeypatch):
    _fake_intent(monkeypatch, Intent(type=IntentType.CONVERSATIONAL, goal="hola", confidence=0.9))

    class _NullRt(AgentRuntime):
        @property
        def capabilities(self): return {"chat"}
        async def execute_task(self, task, memory, tools, approval_gate):
            return AgentResult(task_id=task.id, success=True, output="hola")
        async def stream_task(self, task, memory, tools, approval_gate):
            yield type("C", (), {"kind": "text", "payload": "hola, dime"})()
        async def health_check(self):
            return RuntimeHealth(available=True)
    register_runtime("null", _NullRt())   # el camino corto usa get_runtime("null")

    before = SessionLocal(); n0 = before.query(OrchestratorTrace).count(); before.close()
    evs = await _drain(pipeline_mod.handle_stream(
        "hola", channel="electron", conversational=True, session_id="s4"))
    after = SessionLocal(); n1 = after.query(OrchestratorTrace).count(); after.close()

    assert [p for k, p in evs if k == "text"] == ["hola, dime"]
    assert "mission" not in [k for k, _ in evs]      # una charla no es una misión
    assert n1 == n0                                  # ni siquiera abre traza
    assert conversation.pending_reports("s4") == []


# ---------------------------------------------------------------------------
# 5) El bus ignora misiones que no son de fondo (no registradas)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_bus_ignora_misiones_no_registradas():
    from app.core.events import emit

    emit("mission.completed", source="test", payload={"mission_id": "desconocida", "ok": True})
    await _settle()
    assert conversation.pending_reports(None) == []   # nada que reportar


# ---------------------------------------------------------------------------
# 6) Gate del plan en conversación: avisa "necesito permiso" sin bloquear
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_gate_del_plan_avisa_por_el_canal(monkeypatch):
    monkeypatch.setattr(pipeline_mod.settings, "TIE_PLAN_APPROVAL", True)
    register_runtime("voz4rt6", _Rt())
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="envía un email", confidence=0.9, requires_planning=True))
    # nodo sensible → el plan pide aprobación antes de ejecutar nada
    _fake_plan(monkeypatch, TaskGraph(id="g6", mission_id="m6", nodes={
        "n1": TaskNode(id="n1", goal="enviar", runtime="voz4rt6", approval_required=True)}))

    evs = await _drain(pipeline_mod.handle_stream(
        "envía un email", channel="electron", conversational=True, session_id="s6"))
    assert [p for k, p in evs if k == "text"][-1] == conversation.acuse_text()
    await _settle()

    reports = conversation.pending_reports("s6")
    assert len(reports) == 1
    assert "permiso" in reports[0]["text"].lower()    # aviso de gate pendiente
    # y la aprobación quedó pendiente de verdad (no se ejecutó nada)
    pend = approval_gate.list_pending()
    assert any(a.action_type == "tie_plan" for a in pend)
