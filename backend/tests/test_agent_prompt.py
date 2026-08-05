# tests/test_agent_prompt.py — [2026-08-02, petición del usuario] el prompt de
# comportamiento del agente (`Agent.system_prompt`) LLEGA a la ejecución.
#
# Antes de esta sesión el campo existía en el schema/BD (desde V0.5) pero
# `_delegate_to_tie`/`Authority` nunca lo leían — exactamente el mismo patrón
# de "código muerto" que PU2 cerró para `skills`. Aquí se cierra para
# `system_prompt`, reusando el MISMO canal (`Authority.agent_prompt` →
# `executor._persona_block`) para no inventar una tubería paralela.
#
# Estilo: mismo patrón que test_pu2_skills.py — lo único fake es la FRONTERA
# DEL LLM; BD, ToolManager, planner, executor y bucle de tool-use son reales.
from __future__ import annotations

import json

import pytest

from app.db.database import Agent, AgentExecution, Base, OrchestratorTrace, SessionLocal
from app.db.database import engine as db_engine


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(AgentExecution).delete()
        s.query(Agent).delete()
        s.query(OrchestratorTrace).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def _mk_agent(*, name="Agente", tools=None, system_prompt=None, role=None) -> int:
    db = SessionLocal()
    try:
        a = Agent(name=name, agent_type="generic", is_active=True,
                  allowed_tools=json.dumps(tools if tools is not None else []),
                  max_execution_time=60, system_prompt=system_prompt, role=role)
        db.add(a)
        db.commit()
        db.refresh(a)
        return a.id
    finally:
        db.close()


def _mk_execution(agent_id: int, task: str) -> int:
    db = SessionLocal()
    try:
        e = AgentExecution(agent_id=agent_id, task_description=task, status="pending")
        db.add(e)
        db.commit()
        db.refresh(e)
        return e.id
    finally:
        db.close()


def _fake_llm(monkeypatch, *, plan_tools, agentic_script):
    import app.mel as mel
    from app.mel import Capability, ExecutionResult, ServedBy, Usage

    state = {"agentic_calls": 0, "agentic_prompts": []}

    def _res(text: str) -> ExecutionResult:
        return ExecutionResult(text=text, ok=True, served_by=ServedBy("fake", "fake"),
                               usage=Usage(tokens=5))

    async def _complete(req):
        cap = req.capability
        if cap == Capability.CLASSIFY:
            return _res(json.dumps({
                "type": "execute", "goal": "hacer la tarea del agente",
                "domain": [], "confidence": 0.9, "requires_planning": True,
                "requires_tools": [], "requires_browser": False, "requires_computer": False,
                "requires_automation": False, "requires_memory": False,
                "memory_types": [], "context_query": None, "model_capability": "reason",
            }))
        if cap == Capability.REASON:
            return _res(json.dumps({"nodes": [
                {"id": "n1", "goal": "hacer la tarea", "depends_on": [],
                 "tools": plan_tools, "approval_required": False},
            ]}))
        if cap == Capability.AGENTIC:
            state["agentic_prompts"].append(req.prompt or "")
            i = state["agentic_calls"]
            state["agentic_calls"] += 1
            return _res(agentic_script[min(i, len(agentic_script) - 1)])
        if cap == Capability.SUMMARIZE:
            return _res("Resumen de la misión.")
        return _res("ok")

    monkeypatch.setattr(mel, "complete", _complete)
    return state


def _no_context(monkeypatch):
    from app.tie import enricher as enricher_mod

    async def _enrich(*a, **k):
        return ""
    monkeypatch.setattr(enricher_mod, "enrich", _enrich)
    enricher_mod._cache.clear()


@pytest.mark.anyio
async def test_agente_con_system_prompt_lo_recibe_el_bucle_de_tool_use(monkeypatch, tmp_path):
    """El prompt de comportamiento libre del agente llega al contexto REAL que
    ve el modelo — antes este campo se guardaba y nunca lo leía nadie."""
    _no_context(monkeypatch)
    (tmp_path / "archivo.txt").write_text("x", encoding="utf-8")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    state = _fake_llm(
        monkeypatch,
        plan_tools=["filesystem"],
        agentic_script=[
            json.dumps({"tool": {"tool_id": "filesystem", "action": "list_dir",
                                 "params": {"path": str(tmp_path)}}}),
            json.dumps({"answer": "hecho"}),
        ],
    )

    agent_id = _mk_agent(
        name="Con instrucciones", tools=["filesystem"],
        system_prompt="Responde siempre en un tono formal y nunca uses emojis.",
    )
    exec_id = _mk_execution(agent_id, "haz algo")

    from app.agents.agent_manager import agent_manager
    await agent_manager._run_execution(exec_id)

    db = SessionLocal()
    try:
        row = db.get(AgentExecution, exec_id)
        assert row.status == "completed", row.error_message
    finally:
        db.close()

    assert state["agentic_prompts"], "el bucle de tool-use no llegó a llamarse"
    prompt = state["agentic_prompts"][0]
    assert "tono formal" in prompt
    assert "instrucciones de comportamiento" in prompt.lower()


@pytest.mark.anyio
async def test_agente_sin_system_prompt_no_lleva_bloque_nuevo(monkeypatch, tmp_path):
    """No-regresión: un agente SIN prompt de comportamiento (el caso de
    siempre) no gana texto nuevo — cero impacto en los agentes ya existentes."""
    _no_context(monkeypatch)
    (tmp_path / "archivo.txt").write_text("x", encoding="utf-8")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    state = _fake_llm(
        monkeypatch,
        plan_tools=["filesystem"],
        agentic_script=[
            json.dumps({"tool": {"tool_id": "filesystem", "action": "list_dir",
                                 "params": {"path": str(tmp_path)}}}),
            json.dumps({"answer": "hecho"}),
        ],
    )

    agent_id = _mk_agent(name="Genérico", tools=["filesystem"], system_prompt=None)
    exec_id = _mk_execution(agent_id, "haz algo")

    from app.agents.agent_manager import agent_manager
    await agent_manager._run_execution(exec_id)

    db = SessionLocal()
    try:
        row = db.get(AgentExecution, exec_id)
        assert row.status == "completed", row.error_message
    finally:
        db.close()

    assert state["agentic_prompts"]
    assert "instrucciones de comportamiento" not in state["agentic_prompts"][0].lower()


def test_authority_agent_prompt_sobrevive_al_round_trip_del_checkpoint():
    """Igual que `skills`: tiene que sobrevivir a to_dict/from_dict (lo que
    persiste `orchestrator_traces.plan` en cada transición, T3) para que una
    misión reanudada tras un reinicio conserve el prompt del agente."""
    from app.tie.authority import Authority

    a = Authority(allowed_tools=["git"], agent_prompt="sé breve")
    revivida = Authority.from_dict(json.loads(json.dumps(a.to_dict())))
    assert revivida.agent_prompt == "sé breve"
    # Y sigue sin ser una restricción de seguridad: no afecta a is_unrestricted.
    solo_prompt = Authority(agent_prompt="sé breve")
    assert solo_prompt.is_unrestricted
    assert solo_prompt.check("filesystem", "read_file", {"path": "/x"}) is None


def test_persona_block_combina_skills_y_agent_prompt():
    """Cuando un agente tiene AMBOS (skills + prompt de comportamiento), el
    bloque de persona los incluye a los dos, no solo el primero que se mire."""
    from app.tie.contracts import TaskGraph
    from app.tie.executor import _persona_block

    graph = TaskGraph(id="g1", mission_id="m1", nodes={}, authority={
        "skills": ["Anthropologist"],
        "agent_prompt": "sé muy conciso",
    })
    block = _persona_block(graph)
    assert "Anthropologist" in block
    assert "sé muy conciso" in block
    assert "especialidades" in block.lower()
    assert "instrucciones de comportamiento" in block.lower()


def test_persona_block_vacio_sin_skills_ni_prompt():
    from app.tie.contracts import TaskGraph
    from app.tie.executor import _persona_block

    graph = TaskGraph(id="g2", mission_id="m2", nodes={}, authority={})
    assert _persona_block(graph) == ""
