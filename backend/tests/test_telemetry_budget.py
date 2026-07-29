# tests/test_telemetry_budget.py — S3 (doc 34 §10): presupuesto de llamadas, MEDIDO
#
# Dos cosas se blindan aquí:
#   1. `telemetry.record("path", name=...)` se dispara en la bifurcación real
#      (chat/direct/planned/multi) del pipeline — hoy "no queda en ningún sitio
#      estructurado" (doc 34), así que sin esto nadie puede saber qué camino
#      tomó un turno salvo reconstruyéndolo del log a mano.
#   2. `mission_timeline()` resume ese camino contra el presupuesto declarado
#      en Settings (`BUDGET_LLM_*`) de forma ADITIVA — el resto del dict que ya
#      devolvía (total_ms, llm_by_model, tools, event_count) no cambia; eso es
#      lo que hace que `GET /api/telemetry/missions/{id}` no tenga que tocarse.
from __future__ import annotations

import asyncio

import pytest

from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.telemetry.models import MissionEvent
from app.tie import (
    AgentResult, AgentRuntime, Intent, IntentType, RuntimeHealth, TaskGraph,
    TaskNode, handle, register_handlers, register_runtime, tracer,
)
from app.tie import pipeline as pipeline_mod
from app.automation import Approval


def _purge() -> None:
    """[LOG-1] Limpia tanto al ENTRAR como al SALIR — otros archivos de test
    (p.ej. orquestador multi-objetivo) escriben en la misma tabla global
    `mission_events` y no la conocen para limpiarla; limpiar solo al salir deja
    que su residuo se cuele en el PRIMER test de este archivo que corra después
    (mismo patrón que el bug real de A4, doc 34 §10 / CLAUDE.md §26)."""
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(Approval).delete()
        s.query(MissionEvent).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    register_handlers()
    _purge()
    yield
    _purge()


def _path_events() -> list[MissionEvent]:
    s = SessionLocal()
    try:
        return s.query(MissionEvent).filter(MissionEvent.stage == "path").all()
    finally:
        s.close()


async def _wait_for_path_events(n: int = 1, timeout_s: float = 1.0) -> list[MissionEvent]:
    """`telemetry.record()` es fire-and-forget (`loop.create_task`, doc 31): la
    fila puede tardar un ciclo del event loop en escribirse. Mismo patrón de
    sondeo que ya usa test_tie_handle.py para los eventos `mission.*` (allí con
    un sleep fijo; aquí con sondeo porque el número de ciclos necesarios varía
    según cuántos awaits internos tenga cada camino)."""
    elapsed = 0.0
    step = 0.02
    while elapsed < timeout_s:
        events = _path_events()
        if len(events) >= n:
            return events
        await asyncio.sleep(step)
        elapsed += step
    return _path_events()


# ---------------------------------------------------------------------------
# Fakes — mismo patrón que test_tie_handle.py (el pipeline real, LLM/planner
# sustituidos en la frontera)
# ---------------------------------------------------------------------------
class _Env:
    def __init__(self, text, channel="electron"):
        self.text = text
        self.channel = channel
        self.user_ref = "u1"


class _Rt(AgentRuntime):
    @property
    def capabilities(self):
        return {"chat"}

    async def execute_task(self, task, memory, tools, approval_gate):
        return AgentResult(task_id=task.id, success=True, output="hecho", tokens=1)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


def _fake_intent(monkeypatch, intent: Intent):
    async def _classify(text, *, channel=None):
        return intent
    monkeypatch.setattr(pipeline_mod.intents, "classify", _classify)


def _fake_short_chat(monkeypatch, text="respuesta corta"):
    from app.services import chat_service

    class _A:
        def __init__(self):
            self.text = text
            self.model = "fake"
            self.tokens = 3

    async def _answer(message, *, channel="web", persist_chat_message=True, **kwargs):
        return _A()
    monkeypatch.setattr(chat_service, "answer", _answer)


def _fake_plan(monkeypatch, graph):
    async def _plan(goal, intent, *, context="", mission_id=None, trace_id=None, authority=None):
        if graph is not None:
            graph.mission_id = mission_id or graph.mission_id
            if trace_id:
                tracer.record_plan(trace_id, graph)
        return graph
    monkeypatch.setattr(pipeline_mod.planner, "plan", _plan)


def _fake_responder(monkeypatch):
    async def _build(mission, graph):
        mission.outcome = "listo"
        return mission.outcome
    monkeypatch.setattr(pipeline_mod.responder, "build", _build)


# ===========================================================================
# 1) El stage "path" se registra en cada bifurcación real
# ===========================================================================
@pytest.mark.anyio
async def test_camino_corto_registra_path_chat(monkeypatch):
    _fake_intent(monkeypatch, Intent(type=IntentType.CONVERSATIONAL, goal="hola", confidence=0.9))
    _fake_short_chat(monkeypatch, "hola de vuelta")

    await handle(_Env("hola"))

    names = [e.name for e in await _wait_for_path_events()]
    assert names == ["chat"]


@pytest.mark.anyio
async def test_accion_directa_registra_path_direct(monkeypatch):
    rt = _Rt()
    register_runtime("s3rt", rt)
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="abre algo", confidence=0.9,
        requires_tools=["filesystem"],
    ))

    from app.tie.runtime import NullRuntime
    async def _execute_task(self, task, memory, tools, approval_gate):
        return AgentResult(task_id=task.id, success=True, output="hecho", tokens=1)
    monkeypatch.setattr(NullRuntime, "execute_task", _execute_task)

    await handle(_Env("abre algo"))

    names = [e.name for e in await _wait_for_path_events()]
    assert names == ["direct"]


@pytest.mark.anyio
async def test_mision_compleja_registra_path_planned(monkeypatch):
    rt = _Rt()
    register_runtime("s3rt2", rt)
    _fake_intent(monkeypatch, Intent(
        type=IntentType.EXECUTE, goal="haz A y B", confidence=0.9, requires_planning=True,
    ))
    g = TaskGraph(id="g-s3", mission_id="m-s3", nodes={
        "n1": TaskNode(id="n1", goal="paso A", runtime="s3rt2"),
    })
    _fake_plan(monkeypatch, g)
    _fake_responder(monkeypatch)

    await handle(_Env("haz A y B"))

    names = [e.name for e in await _wait_for_path_events()]
    assert names == ["planned"]


@pytest.mark.anyio
async def test_submit_mission_tambien_registra_planned(monkeypatch):
    """`submit_mission` (la entrada del AE/WPMS) siempre planifica — también
    debe quedar marcada como "planned", mismo camino que el chat complejo."""
    from app.tie import submit_mission

    rt = _Rt()
    register_runtime("s3rt3", rt)
    _fake_intent(monkeypatch, Intent(type=IntentType.CONVERSATIONAL, goal="tarea AE", confidence=0.9))
    g = TaskGraph(id="g-s3b", mission_id="m-s3b", nodes={
        "n1": TaskNode(id="n1", goal="hacer la tarea", runtime="s3rt3"),
    })
    _fake_plan(monkeypatch, g)
    _fake_responder(monkeypatch)

    await submit_mission("tarea AE", source="automation", channel="hub")

    names = [e.name for e in await _wait_for_path_events()]
    assert names == ["planned"]


# ===========================================================================
# 2) mission_timeline() — resumen con eventos sintéticos, clave aditiva
# ===========================================================================
def _seed(mission_id: str, *, path: str | None, llm_calls: int, durations: list[int]) -> None:
    s = SessionLocal()
    try:
        if path is not None:
            s.add(MissionEvent(mission_id=mission_id, stage="path", name=path))
        for d in durations[:llm_calls]:
            s.add(MissionEvent(mission_id=mission_id, stage="llm_call", provider="p",
                               model="m", duration_ms=d, ok=True))
        s.add(MissionEvent(mission_id=mission_id, stage="tool_call", name="filesystem.read",
                           duration_ms=50, ok=True))
        s.commit()
    finally:
        s.close()


def test_summary_cuenta_llm_calls_y_dentro_de_presupuesto():
    from app.telemetry import mission_timeline

    _seed("mid-1", path="direct", llm_calls=3, durations=[100, 200, 150])

    data = mission_timeline("mid-1")
    s = data["summary"]

    assert s["path"] == "direct"
    assert s["llm_calls"] == 3
    assert s["budget"] == 6            # BUDGET_LLM_DIRECT por defecto
    assert s["within_budget"] is True
    assert s["slowest_llm_ms"] == 200


def test_within_budget_false_cuando_se_pasa():
    from app.telemetry import mission_timeline

    # BUDGET_LLM_DIRECT por defecto es 6 — 7 llamadas se pasa.
    _seed("mid-2", path="direct", llm_calls=7, durations=[10] * 7)

    data = mission_timeline("mid-2")
    s = data["summary"]

    assert s["llm_calls"] == 7
    assert s["within_budget"] is False


def test_sin_evento_path_es_desconocido_y_no_falla():
    """Una misión de antes de S3 (o sin bifurcación registrada) no tiene con qué
    comparar — se informa como "desconocido" y NUNCA se marca en rojo."""
    from app.telemetry import mission_timeline

    _seed("mid-3", path=None, llm_calls=20, durations=[10] * 20)

    data = mission_timeline("mid-3")
    s = data["summary"]

    assert s["path"] == "desconocido"
    assert s["budget"] is None
    assert s["within_budget"] is True   # sin presupuesto, no se puede fallar


def test_summary_sigue_siendo_aditivo_contrato_congelado():
    """El resto del dict que `mission_timeline()` ya devolvía NO cambia de
    forma — es lo que permite que `GET /api/telemetry/missions/{id}` no se
    toque."""
    from app.telemetry import mission_timeline

    _seed("mid-4", path="planned", llm_calls=2, durations=[100, 100])

    data = mission_timeline("mid-4")
    assert set(data.keys()) == {"mission_id", "events", "summary"}
    s = data["summary"]
    # Los campos de siempre siguen ahí, con su forma de siempre.
    assert isinstance(s["total_ms"], int)
    assert isinstance(s["llm_by_model"], dict)
    assert isinstance(s["tools"], dict)
    assert isinstance(s["event_count"], int)
    assert s["tools"]  # el tool_call sembrado sigue contando igual que antes
    # Y los campos nuevos de S3, además.
    for k in ("llm_calls", "path", "budget", "within_budget", "slowest_llm_ms"):
        assert k in s


def test_presupuesto_multi_usa_el_setting_per_objective():
    from app.telemetry import mission_timeline

    _seed("mid-5", path="multi", llm_calls=5, durations=[10] * 5)

    data = mission_timeline("mid-5")
    assert data["summary"]["budget"] == 8   # BUDGET_LLM_MULTI_PER_OBJECTIVE
    assert data["summary"]["within_budget"] is True
