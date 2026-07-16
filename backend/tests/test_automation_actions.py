# tests/test_automation_actions.py — las 5 acciones + stubs (V0.9 A3, doc 20 §A3)
#
# Cada acción cablea sobre una API que YA EXISTE — los tests verifican el
# cableado (llama a lo correcto, con los parámetros correctos), no reimplementan
# la lógica de negocio subyacente (eso ya lo cubren sus propios tests).
from datetime import datetime

import pytest

from app.automation import (
    Approval,
    AutomationExecution,
    AutomationRule,
    AgentTaskAction,
    CalendarBlockAction,
    ChainedRuleAction,
    ChatQueryAction,
    EmailSummaryAction,
    MemoryUpdateAction,
    SkillExecutionAction,
    TelegramMessageAction,
    WorkspaceAction,
    AutomationEngine,
    DEFAULT_ACTIONS,
    register_default_actions,
)
from app.automation.triggers import TriggerEvent
from app.db.database import Base, SessionLocal, engine as db_engine
from app.db.models import Project, Task


@pytest.fixture(autouse=True)
def _tables_and_clean():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(AutomationExecution).delete()
        s.query(AutomationRule).delete()
        s.query(Approval).delete()
        s.query(Task).delete()
        s.query(Project).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def _te(payload: dict | None = None) -> TriggerEvent:
    return TriggerEvent(name="test.event", event_key="k1", payload=payload or {})


# ---------------------------------------------------------------------------
# TelegramMessageAction
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_telegram_action_envia_texto_literal(monkeypatch):
    import app.automation.actions as actions_mod

    sent = {}

    async def _fake_notify(channel, target, message):
        sent["channel"] = channel
        sent["target"] = target
        sent["text"] = message.text
        return True

    monkeypatch.setattr(actions_mod, "_default_telegram_target", lambda: "12345")
    from app.gateway.gateway import gateway

    monkeypatch.setattr(gateway, "notify", _fake_notify)

    action = TelegramMessageAction()
    result = await action.execute({"text": "hola mundo"}, _te())

    assert result.ok is True
    assert sent["text"] == "hola mundo"
    assert sent["target"] == "12345"
    assert sent["channel"] == "telegram"


@pytest.mark.anyio
async def test_telegram_action_sin_target_falla_sin_lanzar(monkeypatch):
    import app.automation.actions as actions_mod

    monkeypatch.setattr(actions_mod, "_default_telegram_target", lambda: None)
    action = TelegramMessageAction()
    result = await action.execute({"text": "x"}, _te())

    assert result.ok is False
    assert "chat_id" in result.detail


@pytest.mark.anyio
async def test_telegram_action_source_daily_briefing_construye_texto(monkeypatch):
    import app.automation.actions as actions_mod

    monkeypatch.setattr(actions_mod, "_default_telegram_target", lambda: "1")

    async def _fake_daily_briefing_text():
        return "briefing de prueba"

    monkeypatch.setattr(actions_mod, "_daily_briefing_text", _fake_daily_briefing_text)

    sent = {}

    async def _fake_notify(channel, target, message):
        sent["text"] = message.text
        return True

    from app.gateway.gateway import gateway
    monkeypatch.setattr(gateway, "notify", _fake_notify)

    action = TelegramMessageAction()
    result = await action.execute({"source": "daily_briefing"}, _te())

    assert result.ok is True
    assert sent["text"] == "briefing de prueba"


# ---------------------------------------------------------------------------
# EmailSummaryAction
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_email_summary_action_formatea_el_digest(monkeypatch):
    import app.automation.actions as actions_mod

    async def _fake_digest(date=None):
        return {
            "date": "2026-07-16",
            "triage_counts": {"trabajo": 3},
            "triaged_total": 3,
            "urgent_pending": 1,
            "drafts_awaiting": 2,
            "meetings": {"today": 1, "pending": 0},
            "rules": {"enabled": 0, "auto": 0, "propose": 0},
        }

    monkeypatch.setattr("app.api.endpoints.email_activity.daily_digest", _fake_digest)

    action = EmailSummaryAction()
    result = await action.execute({}, _te())

    assert result.ok is True
    assert "3 triados" in result.detail
    assert "1 urgentes" in result.detail
    assert result.data["date"] == "2026-07-16"


# ---------------------------------------------------------------------------
# ChatQueryAction
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_chat_query_action_reusa_chat_service(monkeypatch):
    from app.services import chat_service

    class _FakeAnswer:
        text = "respuesta del modelo"

    seen = {}

    async def _fake_answer(message, *, channel="web", persist_chat_message=True):
        seen["message"] = message
        seen["channel"] = channel
        seen["persist"] = persist_chat_message
        return _FakeAnswer()

    monkeypatch.setattr(chat_service, "answer", _fake_answer)

    action = ChatQueryAction()
    result = await action.execute({"message": "¿qué tal?"}, _te())

    assert result.ok is True
    assert result.detail == "respuesta del modelo"
    assert seen["message"] == "¿qué tal?"
    assert seen["channel"] == "automation"
    assert seen["persist"] is False


# ---------------------------------------------------------------------------
# AgentTaskAction
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_agent_task_action_sin_agent_id_falla_sin_lanzar():
    action = AgentTaskAction()
    result = await action.execute({}, _te())
    assert result.ok is False
    assert "agent_id" in result.detail


@pytest.mark.anyio
async def test_agent_task_action_delega_en_agent_manager(monkeypatch):
    from app.agents import agent_manager as agent_manager_mod

    class _FakeExecution:
        id = 999

    def _fake_create_execution(agent_id, task):
        assert agent_id == 7
        assert "hola" in task
        return _FakeExecution()

    monkeypatch.setattr(agent_manager_mod.agent_manager, "create_execution", _fake_create_execution)

    action = AgentTaskAction()
    result = await action.execute({"agent_id": 7, "task": "hola agente"}, _te())

    assert result.ok is True
    assert result.data["execution_id"] == 999


@pytest.mark.anyio
async def test_agent_task_action_agente_inexistente_no_lanza(monkeypatch):
    from app.agents import agent_manager as agent_manager_mod

    def _raise(agent_id, task):
        raise ValueError("agente no encontrado")

    monkeypatch.setattr(agent_manager_mod.agent_manager, "create_execution", _raise)

    action = AgentTaskAction()
    result = await action.execute({"agent_id": 404, "task": "x"}, _te())
    assert result.ok is False
    assert "no encontrado" in result.detail


# ---------------------------------------------------------------------------
# WorkspaceAction (Δ2) — usa la BD real de test (SQLite), side effects reales
# ---------------------------------------------------------------------------
def _make_project() -> Project:
    s = SessionLocal()
    try:
        p = Project(name="Proyecto AE", status="active", progress=0.0)
        s.add(p)
        s.commit()
        s.refresh(p)
        s.expunge(p)
        return p
    finally:
        s.close()


@pytest.mark.anyio
async def test_workspace_action_create_task():
    proj = _make_project()
    action = WorkspaceAction()
    result = await action.execute(
        {"op": "create_task", "title": "Tarea desde el AE", "project_id": proj.id}, _te()
    )
    assert result.ok is True
    task_id = result.data["task_id"]

    s = SessionLocal()
    try:
        task = s.get(Task, task_id)
        assert task is not None
        assert task.title == "Tarea desde el AE"
        assert task.project_id == proj.id
        # recompute_project_progress corrió de verdad (0 de 1 tareas cerradas)
        p = s.get(Project, proj.id)
        assert p.progress == 0.0
    finally:
        s.close()


@pytest.mark.anyio
async def test_workspace_action_close_task_recalcula_progreso():
    proj = _make_project()
    create = await WorkspaceAction().execute({"op": "create_task", "project_id": proj.id}, _te())
    task_id = create.data["task_id"]

    result = await WorkspaceAction().execute({"op": "close_task", "task_id": task_id}, _te())
    assert result.ok is True

    s = SessionLocal()
    try:
        task = s.get(Task, task_id)
        assert task.status == "done"
        assert task.closed_at is not None
        p = s.get(Project, proj.id)
        assert p.progress == 1.0  # 1 de 1 tareas cerradas
    finally:
        s.close()


@pytest.mark.anyio
async def test_workspace_action_move_task_recalcula_ambos_proyectos():
    proj_a = _make_project()
    proj_b = _make_project()
    create = await WorkspaceAction().execute({"op": "create_task", "project_id": proj_a.id}, _te())
    task_id = create.data["task_id"]

    result = await WorkspaceAction().execute(
        {"op": "move_task", "task_id": task_id, "project_id": proj_b.id}, _te()
    )
    assert result.ok is True

    s = SessionLocal()
    try:
        task = s.get(Task, task_id)
        assert task.project_id == proj_b.id
    finally:
        s.close()


@pytest.mark.anyio
async def test_workspace_action_tarea_inexistente_no_lanza():
    result = await WorkspaceAction().execute({"op": "close_task", "task_id": 999999}, _te())
    assert result.ok is False
    assert "no encontrada" in result.detail


@pytest.mark.anyio
async def test_workspace_action_op_desconocida():
    result = await WorkspaceAction().execute({"op": "volar_a_la_luna"}, _te())
    assert result.ok is False
    assert "op desconocida" in result.detail


# ---------------------------------------------------------------------------
# Stubs — interfaz definida, NotImplementedError deliberado (no silencioso)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
@pytest.mark.parametrize(
    "action_cls,expected_note",
    [
        (SkillExecutionAction, "V1.1"),
        (CalendarBlockAction, "V1.x"),
        (ChainedRuleAction, "V1.x"),
        (MemoryUpdateAction, "V1.x"),
    ],
)
async def test_stub_actions_lanzan_notimplementederror(action_cls, expected_note):
    with pytest.raises(NotImplementedError) as exc:
        await action_cls().execute({}, _te())
    assert expected_note in str(exc.value)


@pytest.mark.anyio
async def test_stub_action_via_engine_se_registra_como_failed():
    """Una regla mal configurada apuntando a un stub falla CLARO (doc 20 A3),
    no con el generico 'sin ejecutor'."""
    fresh = AutomationEngine()
    register_default_actions(fresh)

    s = SessionLocal()
    try:
        rule = AutomationRule(
            name="usa un stub", enabled=True, trigger_type="event", trigger_config={},
            condition_config={}, action_type="calendar_block", action_config={},
            cooldown_s=0, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        s.add(rule)
        s.commit()
        s.refresh(rule)
        rule_id = rule.id
    finally:
        s.close()

    from app.automation.triggers import Trigger, TriggerContext

    class _Fixed(Trigger):
        def evaluate(self, ctx):
            return TriggerEvent(name="x", event_key="x")

        def arm(self, engine, rule_id):
            pass

        def disarm(self):
            pass

    fresh._armed[rule_id] = _Fixed()
    await fresh.handle_trigger(rule_id, TriggerContext())

    s = SessionLocal()
    try:
        execs = s.query(AutomationExecution).filter(AutomationExecution.rule_id == rule_id).all()
        assert len(execs) == 1
        assert execs[0].status == "failed"
        assert "V1.x" in (execs[0].error or "")
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Registro por defecto
# ---------------------------------------------------------------------------
def test_register_default_actions_registra_las_9():
    fresh = AutomationEngine()
    register_default_actions(fresh)
    for action_type in DEFAULT_ACTIONS:
        assert fresh.has_action_executor(action_type)
    assert len(DEFAULT_ACTIONS) == 9
