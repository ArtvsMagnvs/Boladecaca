# tests/test_automation_isolation.py — motor de reglas (V0.9 A2b, doc 11 §A.5)
#
# Blinda las garantías del engine: aislamiento total (una regla rota no mata al
# motor ni a otras), idempotencia por (rule_id, event_key), condiciones
# composables (And/Or/Not), y que un TRIGGER NUEVO funcione sin tocar engine.py
# (P06 §4) — la prueba real del contrato "trigger nuevo = implementar la
# interfaz".
from datetime import datetime

import pytest

from app.automation import (
    And, Or, Not, Condition, TimeWindowCondition,
    AutomationRule, AutomationExecution,
    Trigger, TriggerContext, TriggerEvent,
    automation_engine,
)
from app.db.database import Base, SessionLocal, engine as db_engine


@pytest.fixture(autouse=True)
def _tables_and_clean():
    Base.metadata.create_all(bind=db_engine)
    automation_engine.disarm_all()  # ninguna regla de un test anterior queda armada
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


def _make_rule(action_type: str, cooldown_s: int = 0, condition_config: dict | None = None) -> AutomationRule:
    s = SessionLocal()
    try:
        rule = AutomationRule(
            name="regla de test", enabled=True, trigger_type="event",
            trigger_config={}, condition_config=condition_config or {},
            action_type=action_type, action_config={}, cooldown_s=cooldown_s,
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
# "Trigger nuevo = implementar la interfaz, CERO cambios en el engine" (P06 §4)
# ---------------------------------------------------------------------------
class _FixedTrigger(Trigger):
    """Un trigger que NO existe en el catálogo de triggers.py — demuestra que
    el engine solo depende del contrato Trigger, nunca de una clase concreta."""

    def __init__(self, event_key: str):
        self._event_key = event_key

    def evaluate(self, ctx: TriggerContext):
        return TriggerEvent(name="fixed", event_key=self._event_key, payload={"ok": True})

    def arm(self, engine, rule_id: int) -> None:
        pass  # este test arma "a mano" (ver abajo) — no necesita fuente real

    def disarm(self) -> None:
        pass


@pytest.mark.anyio
async def test_trigger_nuevo_funciona_sin_tocar_el_engine():
    ran = {"count": 0}

    async def _exec(config, trigger_event):
        ran["count"] += 1
        return "ok"

    automation_engine.register_action_executor("test_fixed_action", _exec)
    rule = _make_rule("test_fixed_action")

    # el engine NO conoce _FixedTrigger — solo el contrato Trigger.evaluate().
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="once")
    await automation_engine.handle_trigger(rule.id, TriggerContext())

    assert ran["count"] == 1
    execs = _executions(rule.id)
    assert len(execs) == 1 and execs[0].status == "ok"


# ---------------------------------------------------------------------------
# Idempotencia — (rule_id, event_key) con ok previo no se re-ejecuta
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_idempotencia_mismo_event_key_no_reejecuta():
    ran = {"count": 0}

    async def _exec(config, trigger_event):
        ran["count"] += 1
        return "ok"

    automation_engine.register_action_executor("test_idem_action", _exec)
    rule = _make_rule("test_idem_action")
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="mismo-hecho")

    await automation_engine.handle_trigger(rule.id, TriggerContext())
    await automation_engine.handle_trigger(rule.id, TriggerContext())
    await automation_engine.handle_trigger(rule.id, TriggerContext())

    assert ran["count"] == 1
    assert len(_executions(rule.id)) == 1


# ---------------------------------------------------------------------------
# Aislamiento total — una regla que revienta no mata al engine ni a otras
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_regla_rota_no_afecta_a_otras_ni_al_engine():
    ran = {"good": 0}

    async def _bad(config, trigger_event):
        raise RuntimeError("esta accion siempre falla")

    async def _good(config, trigger_event):
        ran["good"] += 1
        return "bien"

    automation_engine.register_action_executor("test_bad_action", _bad)
    automation_engine.register_action_executor("test_good_action", _good)

    bad_rule = _make_rule("test_bad_action")
    good_rule = _make_rule("test_good_action")
    automation_engine._armed[bad_rule.id] = _FixedTrigger(event_key="bad-1")
    automation_engine._armed[good_rule.id] = _FixedTrigger(event_key="good-1")

    # la regla rota no debe lanzar hacia el caller (aislamiento en handle_trigger)
    await automation_engine.handle_trigger(bad_rule.id, TriggerContext())
    await automation_engine.handle_trigger(good_rule.id, TriggerContext())

    bad_execs = _executions(bad_rule.id)
    assert len(bad_execs) == 1 and bad_execs[0].status == "failed"
    assert "RuntimeError" in (bad_execs[0].error or "")

    good_execs = _executions(good_rule.id)
    assert len(good_execs) == 1 and good_execs[0].status == "ok"
    assert ran["good"] == 1


@pytest.mark.anyio
async def test_trigger_evaluate_que_lanza_no_propaga():
    class _BrokenTrigger(Trigger):
        def evaluate(self, ctx):
            raise ValueError("trigger roto")

        def arm(self, engine, rule_id):
            pass

        def disarm(self):
            pass

    rule = _make_rule("test_never_called_action")
    automation_engine._armed[rule.id] = _BrokenTrigger()

    # no debe propagar la excepcion — handle_trigger la aisla y loguea.
    await automation_engine.handle_trigger(rule.id, TriggerContext())
    assert _executions(rule.id) == []  # nunca llego a tener un TriggerEvent valido


# ---------------------------------------------------------------------------
# Sin ejecutor registrado -> skipped (nunca peta, A3 lo rellenara)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_sin_ejecutor_registra_skipped():
    rule = _make_rule("test_accion_que_no_existe_todavia")
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="sin-ejecutor")

    await automation_engine.handle_trigger(rule.id, TriggerContext())

    execs = _executions(rule.id)
    assert len(execs) == 1
    assert execs[0].status == "skipped"
    assert "sin ejecutor" in (execs[0].result or "")


# ---------------------------------------------------------------------------
# ActionResult.ok=False (fallo de negocio SIN excepción) -> status="failed"
# (regresión: engine.py solo miraba si el ejecutor lanzaba, no si el propio
# ActionResult reportaba ok=False — encontrado en la verificación en vivo de A3)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_action_result_ok_false_sin_excepcion_se_registra_como_failed():
    from dataclasses import dataclass

    @dataclass
    class _FakeActionResult:
        ok: bool
        detail: str = ""

    async def _exec(config, trigger_event):
        return _FakeActionResult(ok=False, detail="sin chat_id configurado")

    automation_engine.register_action_executor("test_business_fail_action", _exec)
    rule = _make_rule("test_business_fail_action")
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="biz-fail")

    await automation_engine.handle_trigger(rule.id, TriggerContext())

    execs = _executions(rule.id)
    assert len(execs) == 1
    assert execs[0].status == "failed"
    assert execs[0].error == "sin chat_id configurado"


@pytest.mark.anyio
async def test_action_result_ok_true_se_registra_como_ok_con_detail():
    from dataclasses import dataclass

    @dataclass
    class _FakeActionResult:
        ok: bool
        detail: str = ""

    async def _exec(config, trigger_event):
        return _FakeActionResult(ok=True, detail="entregado correctamente")

    automation_engine.register_action_executor("test_business_ok_action", _exec)
    rule = _make_rule("test_business_ok_action")
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="biz-ok")

    await automation_engine.handle_trigger(rule.id, TriggerContext())

    execs = _executions(rule.id)
    assert len(execs) == 1
    assert execs[0].status == "ok"
    assert execs[0].result == "entregado correctamente"


# ---------------------------------------------------------------------------
# Condiciones no cumplidas -> skipped, sin ejecutar la accion
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_condicion_no_cumplida_no_ejecuta_la_accion():
    ran = {"count": 0}

    async def _exec(config, trigger_event):
        ran["count"] += 1
        return "no deberia correr"

    automation_engine.register_action_executor("test_condicion_action", _exec)
    # start_hour == end_hour: ventana vacia por diseño, NUNCA es verdadera.
    rule = _make_rule("test_condicion_action", condition_config={"time_window": {"start_hour": 5, "end_hour": 5}})
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="cond-1")

    await automation_engine.handle_trigger(rule.id, TriggerContext())

    assert ran["count"] == 0
    execs = _executions(rule.id)
    assert len(execs) == 1 and execs[0].status == "skipped"


# ---------------------------------------------------------------------------
# Condiciones composables (And/Or/Not) — unidad, sin pasar por el engine
# ---------------------------------------------------------------------------
class _Always(Condition):
    """True/False fijo — para probar la composicion sin depender de BD/reloj."""
    def __init__(self, value: bool):
        self._value = value

    def check(self, trigger_event, ctx) -> bool:
        return self._value


def test_and_or_not_componen_correctamente():
    te = TriggerEvent(name="x", event_key="x")
    ctx = TriggerContext()

    assert And(_Always(True), _Always(True)).check(te, ctx) is True
    assert And(_Always(True), _Always(False)).check(te, ctx) is False
    assert Or(_Always(False), _Always(True)).check(te, ctx) is True
    assert Or(_Always(False), _Always(False)).check(te, ctx) is False
    assert Not(_Always(False)).check(te, ctx) is True
    assert Not(_Always(True)).check(te, ctx) is False


class _FixedHour:
    """Reemplaza app.automation.conditions.datetime para fijar la hora LOCAL
    que lee TimeWindowCondition.check() (via datetime.now().hour)."""
    def __init__(self, hour: int):
        self._hour = hour

    def now(self):
        return datetime.utcnow().replace(hour=self._hour)


def test_time_window_cruza_medianoche(monkeypatch):
    import app.automation.conditions as cond_mod

    cond = TimeWindowCondition(start_hour=22, end_hour=6)
    te = TriggerEvent(name="x", event_key="x")
    ctx = TriggerContext()

    monkeypatch.setattr(cond_mod, "datetime", _FixedHour(23))
    assert cond.check(te, ctx) is True   # 23h -> dentro (22-6 cruzando medianoche)
    monkeypatch.setattr(cond_mod, "datetime", _FixedHour(2))
    assert cond.check(te, ctx) is True   # 02h -> dentro
    monkeypatch.setattr(cond_mod, "datetime", _FixedHour(12))
    assert cond.check(te, ctx) is False  # 12h -> fuera


def test_time_window_normal_sin_cruzar_medianoche(monkeypatch):
    import app.automation.conditions as cond_mod

    cond = TimeWindowCondition(start_hour=9, end_hour=17)
    te = TriggerEvent(name="x", event_key="x")
    ctx = TriggerContext()

    monkeypatch.setattr(cond_mod, "datetime", _FixedHour(10))
    assert cond.check(te, ctx) is True
    monkeypatch.setattr(cond_mod, "datetime", _FixedHour(20))
    assert cond.check(te, ctx) is False


# ---------------------------------------------------------------------------
# CooldownCondition — lee automation_executions (sin estado en memoria)
# ---------------------------------------------------------------------------
def test_cooldown_bloquea_dentro_de_la_ventana_y_deja_pasar_fuera():
    from app.automation.conditions import CooldownCondition

    rule = _make_rule("test_cooldown_action")
    te = TriggerEvent(name="x", event_key="x")
    ctx = TriggerContext()

    # sin ejecuciones previas -> pasa
    cond = CooldownCondition(rule.id, cooldown_s=3600)
    assert cond.check(te, ctx) is True

    # una ejecucion 'ok' MUY reciente -> bloquea
    s = SessionLocal()
    try:
        s.add(AutomationExecution(
            rule_id=rule.id, trigger_source="x", event_key="anterior",
            status="ok", created_at=datetime.utcnow(),
        ))
        s.commit()
    finally:
        s.close()
    assert cond.check(te, ctx) is False

    # cooldown=0 -> siempre pasa (sin ventana)
    assert CooldownCondition(rule.id, cooldown_s=0).check(te, ctx) is True
