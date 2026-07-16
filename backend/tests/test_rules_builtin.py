# tests/test_rules_builtin.py — 5 reglas predefinidas (V0.9 A3, doc 11 §A.4)
#
# Todas nacen enabled=False (HITL) y la siembra es idempotente: llamar dos
# veces no duplica (arranques sucesivos del backend).
import pytest

from app.automation import AutomationRule, BUILTIN_RULES, seed_builtin_rules
from app.db.database import Base, SessionLocal, engine as db_engine


@pytest.fixture(autouse=True)
def _tables_and_clean():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(AutomationRule).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def test_seed_crea_las_5_reglas_todas_desactivadas():
    created = seed_builtin_rules()
    assert created == 5

    s = SessionLocal()
    try:
        rows = s.query(AutomationRule).all()
        assert len(rows) == 5
        assert all(r.enabled is False for r in rows)
        names = {r.name for r in rows}
        assert names == {spec["name"] for spec in BUILTIN_RULES}
    finally:
        s.close()


def test_seed_es_idempotente():
    first = seed_builtin_rules()
    second = seed_builtin_rules()
    assert first == 5
    assert second == 0  # nada nuevo en la segunda pasada

    s = SessionLocal()
    try:
        assert s.query(AutomationRule).count() == 5
    finally:
        s.close()


def test_seed_no_duplica_si_el_usuario_ya_creo_una_regla_con_ese_nombre():
    """Si por lo que sea ya existe una regla llamada igual (creada a mano), la
    siembra la respeta — nunca sobreescribe ni duplica."""
    from datetime import datetime

    s = SessionLocal()
    try:
        s.add(AutomationRule(
            name="daily_briefing", enabled=True, trigger_type="event",
            trigger_config={}, condition_config={}, action_type="chat_query",
            action_config={}, cooldown_s=0,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        ))
        s.commit()
    finally:
        s.close()

    created = seed_builtin_rules()
    assert created == 4  # las otras 4, no daily_briefing

    s = SessionLocal()
    try:
        custom = s.query(AutomationRule).filter(AutomationRule.name == "daily_briefing").first()
        assert custom.enabled is True  # intacta, no la pisó la siembra
        assert s.query(AutomationRule).count() == 5
    finally:
        s.close()


def test_rules_builtin_action_types_conocidos_por_el_engine():
    """Cada regla predefinida apunta a un action_type real (de las 5 acciones,
    nunca a un stub) — si no, el motor la marcaría 'failed' nada más activarla."""
    real_actions = {"telegram_message", "email_summary", "chat_query", "agent_task", "workspace"}
    for spec in BUILTIN_RULES:
        assert spec["action_type"] in real_actions, spec["name"]


def test_agent_task_rule_es_plantilla_inofensiva_por_defecto():
    """agent_id=None: si alguien la activa sin configurarla, AgentTaskAction
    falla con un detail claro — nunca ejecuta un agente al azar (doc 20 A3)."""
    spec = next(s for s in BUILTIN_RULES if s["name"] == "agent_task")
    assert spec["action_config"].get("agent_id") is None


# ---------------------------------------------------------------------------
# Endpoints HTTP: GET /rules, PATCH /rules/{id} (toggle EN CALIENTE), GET /executions
# ---------------------------------------------------------------------------
def _create_rule_row(project_id=None) -> int:
    from datetime import datetime

    s = SessionLocal()
    try:
        rule = AutomationRule(
            name="regla http", enabled=False, trigger_type="event",
            trigger_config={"event_name": "task.created"}, condition_config={},
            action_type="chat_query", action_config={}, project_id=project_id,
            cooldown_s=0, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        s.add(rule)
        s.commit()
        s.refresh(rule)
        return rule.id
    finally:
        s.close()


def test_endpoint_list_rules_y_filtro_por_proyecto(client):
    _create_rule_row(project_id=None)
    _create_rule_row(project_id=42)

    all_rules = client.get("/api/automation/rules").json()
    assert len(all_rules) >= 2

    scoped = client.get("/api/automation/rules?project_id=42").json()
    assert len(scoped) == 1
    assert scoped[0]["project_id"] == 42


def test_endpoint_toggle_arma_y_desarma_en_caliente(client):
    from app.automation import automation_engine

    rule_id = _create_rule_row()
    assert rule_id not in automation_engine.armed_rule_ids()

    r = client.patch(f"/api/automation/rules/{rule_id}", json={"enabled": True})
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    assert rule_id in automation_engine.armed_rule_ids()

    r = client.patch(f"/api/automation/rules/{rule_id}", json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False
    assert rule_id not in automation_engine.armed_rule_ids()


def test_endpoint_toggle_404_en_regla_inexistente(client):
    r = client.patch("/api/automation/rules/999999", json={"enabled": True})
    assert r.status_code == 404


def test_endpoint_list_executions(client):
    from datetime import datetime

    rule_id = _create_rule_row()
    s = SessionLocal()
    try:
        from app.automation import AutomationExecution

        s.add(AutomationExecution(
            rule_id=rule_id, trigger_source="test", event_key="k1", status="ok",
            result="hecho", created_at=datetime.utcnow(),
        ))
        s.commit()
    finally:
        s.close()

    r = client.get(f"/api/automation/executions?rule_id={rule_id}")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["status"] == "ok"
