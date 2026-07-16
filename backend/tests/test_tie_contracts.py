# tests/test_tie_contracts.py — TIE v1 esqueleto (V1.0 T1, doc 21 §3·T1)
#
# Blinda lo que T1 entrega: contratos CONGELADOS (round-trip serializable), el
# clasificador de intención (con ai_manager fake — sin credenciales en CI) que ya
# responde las 7 preguntas, el umbral de confianza, la lógica del camino corto, el
# NullRuntime y el registro de runtimes, y el pipeline `handle`/`submit_mission`
# escribiendo su traza en `orchestrator_traces`.
import pytest

from app.tie import (
    AgentTask,
    Intent,
    IntentType,
    Mission,
    NodeState,
    NullRuntime,
    TaskGraph,
    TaskNode,
    get_runtime,
    list_runtimes,
    register_runtime,
)
from app.tie.contracts import MEL_CAPABILITIES
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Contratos congelados — round-trip serializable
# ---------------------------------------------------------------------------
def test_nodestate_completo():
    assert {s.value for s in NodeState} == {
        "pending", "ready", "running", "waiting_approval", "waiting_event",
        "done", "failed", "skipped", "cancelled",
    }


def test_tasknode_round_trip():
    n = TaskNode(id="n1", goal="hacer algo", depends_on=["n0"], tools=["filesystem"],
                 approval_required=True, priority=5)
    d = n.to_dict()
    assert d["state"] == "pending"
    n2 = TaskNode.from_dict(d)
    assert n2.id == "n1" and n2.goal == "hacer algo"
    assert n2.depends_on == ["n0"] and n2.tools == ["filesystem"]
    assert n2.approval_required is True and n2.priority == 5
    assert n2.state == NodeState.PENDING


def test_taskgraph_round_trip():
    g = TaskGraph(id="g1", mission_id="m1", nodes={
        "n1": TaskNode(id="n1", goal="a"),
        "n2": TaskNode(id="n2", goal="b", depends_on=["n1"]),
    })
    d = g.to_dict()
    g2 = TaskGraph.from_dict(d)
    assert set(g2.nodes) == {"n1", "n2"}
    assert g2.nodes["n2"].depends_on == ["n1"]
    assert g2.mission_id == "m1"


def test_mission_dataclass():
    m = Mission(id=Mission.new_id(), goal="objetivo", source="user", channel="electron")
    assert m.state == "running"
    assert m.to_dict()["goal"] == "objetivo"


# ---------------------------------------------------------------------------
# Intent — las 7 preguntas + is_short_path + serialización
# ---------------------------------------------------------------------------
def test_intent_responde_las_7_preguntas():
    it = Intent(
        type=IntentType.CREATE, goal="crear una tarea del proyecto X",
        domain=["project", "task"], confidence=0.9,
        requires_planning=True, requires_tools=["filesystem"],
        requires_browser=True, requires_automation=False,
        requires_memory=True, memory_types=["mem_project"],
        context_query="proyecto X", model_capability="reason",
    )
    # 1 qué quiere · 2 qué tools · 3 planner · 4 browser · 5 automation · 6 MEL · 7 MOS
    assert it.type == IntentType.CREATE and it.goal
    assert it.requires_tools == ["filesystem"]
    assert it.requires_planning is True
    assert it.requires_browser is True
    assert it.requires_automation is False
    assert it.model_capability == "reason" and it.model_capability in MEL_CAPABILITIES
    assert it.requires_memory is True and it.memory_types == ["mem_project"]
    assert it.to_dict()["type"] == "create"


def test_is_short_path():
    conv = Intent(type=IntentType.CONVERSATIONAL, goal="hola")
    assert conv.is_short_path is True
    simple_q = Intent(type=IntentType.QUERY, goal="qué hora es")
    assert simple_q.is_short_path is True
    planned_q = Intent(type=IntentType.QUERY, goal="analiza mi semana", requires_planning=True)
    assert planned_q.is_short_path is False
    browser_q = Intent(type=IntentType.QUERY, goal="busca en la web", requires_browser=True)
    assert browser_q.is_short_path is False
    create = Intent(type=IntentType.CREATE, goal="crea una tarea")
    assert create.is_short_path is False


def test_conversational_fallback():
    fb = Intent.conversational_fallback("algo")
    assert fb.type == IntentType.CONVERSATIONAL and fb.confidence == 0.0
    assert fb.is_short_path is True


# ---------------------------------------------------------------------------
# Clasificador — con ai_manager fake (sin credenciales)
# ---------------------------------------------------------------------------
def _fake_ai(monkeypatch, response: str, error: bool = False):
    async def _chat(message, system_prompt=None):
        return {"response": response, "model": "fake", "tokens": 10, "error": error}
    import app.ai.ai_manager as aim
    monkeypatch.setattr(aim.ai_manager, "chat", _chat)


@pytest.mark.anyio
async def test_classify_intent_complejo(monkeypatch):
    from app.tie import classify
    _fake_ai(monkeypatch, """{"type":"create","goal":"crear tarea","domain":["task"],
        "confidence":0.9,"requires_planning":true,"requires_tools":["filesystem"],
        "requires_browser":false,"requires_computer":false,"requires_automation":false,
        "requires_memory":true,"memory_types":["mem_project"],"context_query":"proyecto",
        "model_capability":"reason"}""")
    it = await classify("crea una tarea en el proyecto")
    assert it.type == IntentType.CREATE
    assert it.requires_planning is True
    assert it.model_capability == "reason"
    assert it.is_short_path is False


@pytest.mark.anyio
async def test_classify_umbral_fuerza_conversational(monkeypatch):
    from app.tie import classify
    # confianza < 0.55 → se fuerza conversational aunque diga "create"
    _fake_ai(monkeypatch, '{"type":"create","goal":"x","confidence":0.3,"requires_planning":true}')
    it = await classify("mensaje ambiguo")
    assert it.type == IntentType.CONVERSATIONAL
    assert it.requires_planning is False
    assert it.is_short_path is True


@pytest.mark.anyio
async def test_classify_json_basura_fallback(monkeypatch):
    from app.tie import classify
    _fake_ai(monkeypatch, "esto no es json en absoluto")
    it = await classify("hola")
    assert it.type == IntentType.CONVERSATIONAL and it.confidence == 0.0


@pytest.mark.anyio
async def test_classify_error_del_proveedor_fallback(monkeypatch):
    from app.tie import classify
    _fake_ai(monkeypatch, "boom", error=True)
    it = await classify("hola")
    assert it.type == IntentType.CONVERSATIONAL


@pytest.mark.anyio
async def test_classify_extrae_json_en_bloque_markdown(monkeypatch):
    from app.tie import classify
    _fake_ai(monkeypatch, 'Claro:\n```json\n{"type":"conversational","goal":"saludo","confidence":0.8}\n```\n')
    it = await classify("hola")
    assert it.type == IntentType.CONVERSATIONAL and it.goal == "saludo"


# ---------------------------------------------------------------------------
# Runtime — NullRuntime + registro
# ---------------------------------------------------------------------------
def test_registro_runtimes():
    assert "null" in list_runtimes()
    assert get_runtime("null").__class__ is NullRuntime
    assert get_runtime(None).__class__ is NullRuntime          # fallback
    assert get_runtime("inexistente").__class__ is NullRuntime  # fallback


def test_register_runtime_valida_tipo():
    with pytest.raises(TypeError):
        register_runtime("malo", object())  # no es AgentRuntime


@pytest.mark.anyio
async def test_nullruntime_ejecuta_chat(monkeypatch):
    from app.services import chat_service

    class _Ans:
        text = "respuesta del chat"
        model = "fake"
        tokens = 7
    async def _answer(message, *, channel="web", persist_chat_message=True):
        return _Ans()
    monkeypatch.setattr(chat_service, "answer", _answer)

    rt = NullRuntime()
    task = AgentTask(id=AgentTask.new_id(), instruction="hola")
    res = await rt.execute_task(task, memory=None, tools=None, approval_gate=None)
    assert res.success is True and res.output == "respuesta del chat"
    assert "chat" in rt.capabilities


# ---------------------------------------------------------------------------
# Pipeline — handle/submit_mission camino corto + traza
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_handle_camino_corto_responde_y_deja_traza(monkeypatch):
    from app.tie import handle
    import app.tie.intents as intents_mod
    from app.services import chat_service

    async def _classify(text, *, channel=None):
        return Intent(type=IntentType.CONVERSATIONAL, goal=text, confidence=0.9)
    monkeypatch.setattr(intents_mod, "classify", _classify)

    class _Ans:
        text = "hola, soy Aithera"
        model = "fake"
        tokens = 5
    async def _answer(message, *, channel="web", persist_chat_message=True):
        return _Ans()
    monkeypatch.setattr(chat_service, "answer", _answer)

    class _Env:
        text = "hola"
        channel = "electron"
        user_ref = "u1"

    out = await handle(_Env())
    assert out == "hola, soy Aithera"

    s = SessionLocal()
    try:
        traces = s.query(OrchestratorTrace).all()
        assert len(traces) == 1
        assert traces[0].state == "done"
        assert traces[0].intent is not None and traces[0].intent["type"] == "conversational"
        assert traces[0].channel == "electron"
    finally:
        s.close()


@pytest.mark.anyio
async def test_submit_mission_camino_corto(monkeypatch):
    from app.tie import submit_mission
    import app.tie.intents as intents_mod
    from app.services import chat_service

    async def _classify(text, *, channel=None):
        return Intent(type=IntentType.CONVERSATIONAL, goal=text, confidence=0.9)
    monkeypatch.setattr(intents_mod, "classify", _classify)

    class _Ans:
        text = "misión atendida"
        model = "fake"
        tokens = 5
    async def _answer(message, *, channel="web", persist_chat_message=True):
        return _Ans()
    monkeypatch.setattr(chat_service, "answer", _answer)

    m = await submit_mission("haz algo", source="automation", channel="hub")
    assert m.state == "done" and m.outcome == "misión atendida"
    assert m.source == "automation"
