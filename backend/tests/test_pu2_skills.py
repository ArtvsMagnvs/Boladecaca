# tests/test_pu2_skills.py — PU2 (doc 35): skills reales en agentes.
#
# Dos fallos reportados por el usuario, cerrados aquí:
# (1) `Agent.skills` aceptaba CUALQUIER string — un agente creado por chat
#     ("créame un agente con skills de X") podía acabar con skills inventadas
#     que no existen en el catálogo real (`skills_catalog.json`, 254 entradas).
# (2) aunque la skill fuera real, nunca llegaba a la ejecución: `_delegate_to_
#     tie` no la pasaba al TIE, así que un agente "con skills de marketing"
#     ejecutaba exactamente igual que uno sin ninguna.
#
# Estilo: mismo patrón que test_agent_execution.py (R4) — lo único fake es la
# FRONTERA DEL LLM; BD, ToolManager, planner, executor y bucle de tool-use son
# reales.
from __future__ import annotations

import json

import pytest

from app.agents import skills_catalog
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


# ---------------------------------------------------------------------------
# Helpers (mismo patrón que test_agent_execution.py)
# ---------------------------------------------------------------------------
def _mk_agent(*, name="Agente", tools=None, skills=None) -> int:
    db = SessionLocal()
    try:
        a = Agent(name=name, agent_type="generic", is_active=True,
                  allowed_tools=json.dumps(tools if tools is not None else []),
                  max_execution_time=60, skills=skills)
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
    """Captura `req.prompt` de cada llamada AGENTIC (ademas del REASON), para
    poder comprobar si el bloque de persona de las skills llegó al prompt
    real que ve el modelo del bucle de tool-use."""
    import app.mel as mel
    from app.mel import Capability, ExecutionResult, ServedBy, Usage

    state = {"agentic_calls": 0, "agentic_prompts": [], "plan_prompts": []}

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
            state["plan_prompts"].append(req.system_prompt or "")
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


# ===========================================================================
# Parte 1 — el catálogo del backend (funciones puras)
# ===========================================================================
def test_skill_by_name_case_insensitive():
    hit = skills_catalog.skill_by_name("anthropologist")
    assert hit is not None
    assert hit["name"] == "Anthropologist"


def test_skill_by_name_desconocida_da_none():
    assert skills_catalog.skill_by_name("Growth Hacking Wizard XYZ") is None


def test_validate_skills_canonicaliza_mayusculas():
    canon = skills_catalog.validate_skills(["anthropologist", "GEOGRAPHER"])
    assert canon == ["Anthropologist", "Geographer"]


def test_validate_skills_rechaza_inventada_con_sugerencia():
    with pytest.raises(ValueError) as exc:
        skills_catalog.validate_skills(["Growth Hacking Expert"])
    msg = str(exc.value)
    assert "Growth Hacking Expert" in msg
    # El catálogo real trae "Growth Hacker" — la sugerencia por substring debe
    # encontrarlo (ambos comparten "growth hack").
    assert "Growth Hacker" in msg


def test_validate_skills_lista_vacia_no_rompe():
    assert skills_catalog.validate_skills([]) == []


def test_descriptions_for_omite_desconocidas_en_silencio():
    entries = skills_catalog.descriptions_for(["Anthropologist", "Skill Que No Existe"])
    assert len(entries) == 1
    assert entries[0]["name"] == "Anthropologist"


# ---------------------------------------------------------------------------
# PU2-ext: términos sueltos ("research y márketing") → candidatos reales, no
# un "no existe" mudo. El usuario no se sabe los 254 nombres de memoria.
# ---------------------------------------------------------------------------
def test_validate_skills_categoria_suelta_da_candidatos_reales():
    """"marketing" es una CATEGORÍA (36 skills), no el nombre de ninguna."""
    with pytest.raises(ValueError) as exc:
        skills_catalog.validate_skills(["marketing"])
    msg = str(exc.value)
    assert "categoría" in msg
    assert "Marketing" in msg
    # Al menos un nombre REAL de esa categoría debe aparecer como candidato.
    assert "Book Co-Author" in msg or "AEO Foundations Architect" in msg


def test_validate_skills_categoria_acento_insensible():
    """El usuario escribe en español con acento: "márketing"."""
    with pytest.raises(ValueError) as exc:
        skills_catalog.validate_skills(["márketing"])
    assert "Marketing" in str(exc.value)


def test_validate_skills_termino_suelto_por_palabra_clave():
    """"research" NO es una de las 17 categorías, pero sí aparece en el
    nombre de varias skills reales (UX Researcher, Investment Researcher,
    Trend Researcher) — debe surgir como candidato, no como "no existe"."""
    with pytest.raises(ValueError) as exc:
        skills_catalog.validate_skills(["research"])
    msg = str(exc.value)
    assert "relacionadas" in msg
    assert "Researcher" in msg


def test_validate_skills_categoria_no_rompe_el_typo_existente():
    """No-regresión: un nombre CASI correcto (no una categoría, no un
    término temático) sigue cayendo en la sugerencia por substring/difflib
    de siempre, no en las dos capas nuevas."""
    with pytest.raises(ValueError) as exc:
        skills_catalog.validate_skills(["Growth Hacking Expert"])
    msg = str(exc.value)
    assert "categoría" not in msg
    assert "relacionadas" not in msg
    assert "Growth Hacker" in msg


def test_validate_skills_termino_corto_no_da_ruido():
    """Un término de 1-2 letras no debe disparar la búsqueda por palabra
    clave (demasiado ruido) — cae en el "no existe" simple de siempre."""
    with pytest.raises(ValueError) as exc:
        skills_catalog.validate_skills(["ai"])
    msg = str(exc.value)
    assert "relacionadas" not in msg


# ===========================================================================
# Parte 2 — validación al crear/editar un agente (cubre HTTP + aithera_tool,
# los dos convergen en AgentManager)
# ===========================================================================
def test_crear_agente_con_skill_inventada_falla():
    from app.agents.agent_manager import agent_manager

    with pytest.raises(ValueError, match="Skills inválidas"):
        agent_manager.create_agent(name="Bot", skills=["Skill Totalmente Inventada"])


def test_crear_agente_con_skill_real_normaliza_mayusculas():
    from app.agents.agent_manager import agent_manager

    agent = agent_manager.create_agent(name="Bot2", skills=["anthropologist"])
    assert agent.skills == ["Anthropologist"]


def test_actualizar_agente_valida_skills():
    from app.agents.agent_manager import agent_manager

    agent_id = _mk_agent(name="Bot3")
    with pytest.raises(ValueError, match="Skills inválidas"):
        agent_manager.update_agent(agent_id, skills=["Otra Skill Falsa"])

    # Con una real, sí se aplica (y se canonicaliza).
    updated = agent_manager.update_agent(agent_id, skills=["geographer"])
    assert updated.skills == ["Geographer"]


@pytest.mark.anyio
async def test_aithera_tool_create_agent_categoria_suelta_ofrece_candidatos_reales():
    """[PU2-ext] "créame un agente con skills de marketing" — el chat manda
    la CATEGORÍA suelta, no nombres exactos. `aithera_tool` debe devolver
    candidatos reales (no un simple "no existe") para que el modelo pueda
    reintentar solo en la siguiente vuelta del bucle de tool-use, sin que el
    usuario tenga que saberse ningún nombre de memoria."""
    from app.tools.aithera_tool import AitheraTool

    tool = AitheraTool()
    res = await tool.execute("create_agent", {
        "name": "Chat-Marketing-Bot", "skills": ["marketing"],
    })
    assert res["success"] is False
    assert "categoría" in res["error"]
    # Al menos un nombre real de la categoría llega hasta el toolloop.
    assert "Book Co-Author" in res["error"] or "AEO Foundations Architect" in res["error"]

    # El "reintento" real es del modelo, no de este test — pero probamos que
    # con un nombre REAL de esos candidatos, la creación SÍ funciona: cierra
    # el círculo completo "categoría suelta -> candidatos -> nombre real -> agente".
    res2 = await tool.execute("create_agent", {
        "name": "Chat-Marketing-Bot", "skills": ["Book Co-Author"],
    })
    assert res2["success"] is True

    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.name == "Chat-Marketing-Bot").first()
        assert agent is not None
        assert agent.skills == ["Book Co-Author"]
    finally:
        db.close()


@pytest.mark.anyio
async def test_aithera_tool_create_agent_propaga_el_rechazo():
    """El chat pidiendo 'créame un agente con skills de X' donde X no existe:
    `aithera_tool` debe devolver un error accionable, no crear el agente."""
    from app.tools.aithera_tool import AitheraTool

    tool = AitheraTool()
    res = await tool.execute("create_agent", {
        "name": "Chat-Bot", "skills": ["Skill Que Nadie Tiene"],
    })
    assert res["success"] is False
    assert "Skills inválidas" in (res["error"] or "")

    db = SessionLocal()
    try:
        assert db.query(Agent).filter(Agent.name == "Chat-Bot").first() is None
    finally:
        db.close()


# ===========================================================================
# Parte 3 — las skills asignadas LLEGAN a la ejecución (antes: código muerto)
# ===========================================================================
@pytest.mark.anyio
async def test_agente_con_skills_recibe_el_contexto_de_persona(monkeypatch, tmp_path):
    _no_context(monkeypatch)
    # [A-1, doc 34 §S1] Un "answer" sin ninguna tool ejecutada con éxito se
    # rechaza como sin fundamento — igual que test_agent_execution.py, hace
    # falta un paso real (list_dir) antes de la respuesta final.
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

    agent_id = _mk_agent(name="Especialista", tools=["filesystem"],
                         skills=["Anthropologist", "Geographer"])
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
    assert "Anthropologist" in prompt
    assert "Geographer" in prompt
    assert "cultural" in prompt.lower()  # fragmento real de la descripción del catálogo


@pytest.mark.anyio
async def test_agente_sin_skills_no_lleva_bloque_de_persona(monkeypatch, tmp_path):
    """No-regresión: un agente SIN skills (el caso de siempre) no debe ganar
    texto nuevo en el prompt — cero impacto en los agentes ya existentes."""
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

    agent_id = _mk_agent(name="Genérico", tools=["filesystem"], skills=None)
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
    assert "especialidades" not in state["agentic_prompts"][0].lower()


def test_authority_skills_sobrevive_al_round_trip_del_checkpoint():
    """Igual que `allowed_tools`/`repo_path`: tiene que sobrevivir a
    to_dict/from_dict (lo que persiste `orchestrator_traces.plan` en cada
    transición, T3) para que una misión reanudada tras un reinicio conserve
    las skills del agente."""
    from app.tie.authority import Authority

    a = Authority(allowed_tools=["git"], skills=["Anthropologist"])
    revivida = Authority.from_dict(json.loads(json.dumps(a.to_dict())))
    assert revivida.skills == ["Anthropologist"]
    # Y sigue sin ser una restricción de seguridad: no afecta a is_unrestricted.
    solo_skills = Authority(skills=["Anthropologist"])
    assert solo_skills.is_unrestricted
    assert solo_skills.check("filesystem", "read_file", {"path": "/x"}) is None
