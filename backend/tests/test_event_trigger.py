# tests/test_event_trigger.py — EventTrigger + ScheduleTrigger (V0.9 A2b)
#
# EventTrigger es "reactivo sobre app/core/events.py — NUNCA polling propio"
# (doc 11 §A.1). Prueba real: emitir un evento del bus dispara la regla
# suscrita, incluidos los eventos que el WPMS (V0.87) ya emite (Δ1, doc 20 §1).
# ScheduleTrigger se prueba sin esperar al reloj real: se arma contra el
# `scheduler_service` (ya vivo via el lifespan/`client`) y se dispara a mano.
import asyncio
from datetime import datetime

import pytest

from app.automation import (
    AutomationRule, AutomationExecution,
    ScheduleTrigger, TriggerContext,
    automation_engine, scheduler_service,
)
from app.core.events import emit
from app.db.database import Base, SessionLocal, engine as db_engine


@pytest.fixture(autouse=True)
def _tables_and_clean():
    Base.metadata.create_all(bind=db_engine)
    automation_engine.disarm_all()
    yield
    automation_engine.disarm_all()
    s = SessionLocal()
    try:
        s.query(AutomationExecution).delete()
        s.query(AutomationRule).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def _make_rule(action_type: str, trigger_type: str, trigger_config: dict) -> AutomationRule:
    s = SessionLocal()
    try:
        rule = AutomationRule(
            name="regla evento", enabled=True, trigger_type=trigger_type,
            trigger_config=trigger_config, condition_config={},
            action_type=action_type, action_config={}, cooldown_s=0,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        s.add(rule)
        s.commit()
        s.refresh(rule)
        s.expunge(rule)
        return rule
    finally:
        s.close()


def _executions(rule_id: int) -> list[AutomationExecution]:
    s = SessionLocal()
    try:
        rows = s.query(AutomationExecution).filter(AutomationExecution.rule_id == rule_id).all()
        for r in rows:
            s.expunge(r)
        return rows
    finally:
        s.close()


# ---------------------------------------------------------------------------
# EventTrigger — dispara al emitir el evento del bus
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_event_trigger_dispara_al_emitir_el_evento(client):
    ran = {"payload": None}

    async def _exec(config, trigger_event):
        ran["payload"] = trigger_event.payload
        return "hecho"

    automation_engine.register_action_executor("test_ev_action", _exec)
    rule = _make_rule(
        "test_ev_action", "event",
        {"event_name": "task.closed", "event_key_field": "task_id"},
    )
    automation_engine.arm_rule(rule.id, rule.trigger_type, rule.trigger_config)

    emit("task.closed", source="test", payload={"task_id": 999})
    await asyncio.sleep(0.05)  # emit() programa el handler como task — cede el loop

    assert ran["payload"] == {"task_id": 999}
    execs = _executions(rule.id)
    assert len(execs) == 1 and execs[0].status == "ok"
    assert execs[0].event_key == "task.closed:999"


@pytest.mark.anyio
async def test_event_trigger_wpms_milestone_completed(client):
    """Los eventos que el WPMS (V0.87) YA emite se consumen sin tocar
    app/workspace/ (Δ1, doc 20 §1) — mismo mecanismo, otro nombre de evento."""
    ran = {"count": 0}

    async def _exec(config, trigger_event):
        ran["count"] += 1
        return "ok"

    automation_engine.register_action_executor("test_wpms_action", _exec)
    rule = _make_rule(
        "test_wpms_action", "event",
        {"event_name": "milestone.completed", "event_key_field": "milestone_id"},
    )
    automation_engine.arm_rule(rule.id, rule.trigger_type, rule.trigger_config)

    emit("milestone.completed", source="workspace", payload={"milestone_id": 7, "project_id": 3})
    await asyncio.sleep(0.05)

    assert ran["count"] == 1
    execs = _executions(rule.id)
    assert execs[0].event_key == "milestone.completed:7"


@pytest.mark.anyio
async def test_event_trigger_filtra_por_payload(client):
    ran = {"count": 0}

    async def _exec(config, trigger_event):
        ran["count"] += 1

    automation_engine.register_action_executor("test_filter_action", _exec)
    rule = _make_rule(
        "test_filter_action", "event",
        {"event_name": "email.triaged", "payload_filter": {"category": "urgente"}},
    )
    automation_engine.arm_rule(rule.id, rule.trigger_type, rule.trigger_config)

    emit("email.triaged", source="mos", payload={"email_id": "e1", "category": "trabajo"})
    await asyncio.sleep(0.05)
    assert ran["count"] == 0  # no matchea el filtro -> no dispara

    emit("email.triaged", source="mos", payload={"email_id": "e2", "category": "urgente"})
    await asyncio.sleep(0.05)
    assert ran["count"] == 1  # matchea -> dispara


@pytest.mark.anyio
async def test_disarm_deja_de_escuchar(client):
    ran = {"count": 0}

    async def _exec(config, trigger_event):
        ran["count"] += 1

    automation_engine.register_action_executor("test_disarm_action", _exec)
    rule = _make_rule("test_disarm_action", "event", {"event_name": "task.created"})
    automation_engine.arm_rule(rule.id, rule.trigger_type, rule.trigger_config)

    emit("task.created", source="test", payload={"task_id": 1})
    await asyncio.sleep(0.05)
    assert ran["count"] == 1

    automation_engine.disarm_rule(rule.id)
    emit("task.created", source="test", payload={"task_id": 2})
    await asyncio.sleep(0.05)
    assert ran["count"] == 1  # ya no escucha — no subio


# ---------------------------------------------------------------------------
# ScheduleTrigger — arma un job real en APScheduler; se dispara a mano (sin
# esperar al reloj) para probar el contrato evaluate()+handle_trigger().
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_schedule_trigger_arma_job_y_evaluate_siempre_dispara(client):
    assert scheduler_service.running is True  # ya arrancado por el lifespan

    ran = {"count": 0}

    async def _exec(config, trigger_event):
        ran["count"] += 1

    automation_engine.register_action_executor("test_sched_action", _exec)
    rule = _make_rule("test_sched_action", "schedule", {"interval_minutes": 60})
    automation_engine.arm_rule(rule.id, rule.trigger_type, rule.trigger_config)

    job_id = f"automation_rule_{rule.id}"
    assert job_id in scheduler_service.jobs()

    # el propio disparo del cron ES el hecho: evaluate() siempre da TriggerEvent.
    await automation_engine.handle_trigger(rule.id, TriggerContext())
    assert ran["count"] == 1

    automation_engine.disarm_rule(rule.id)
    assert job_id not in scheduler_service.jobs()


def test_schedule_trigger_necesita_cron_o_interval():
    with pytest.raises(ValueError):
        ScheduleTrigger()
