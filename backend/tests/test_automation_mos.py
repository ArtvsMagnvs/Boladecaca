# tests/test_automation_mos.py — el AE deja rastro en el MOS (V0.9 A4, doc 11 §A.3 / doc 17 §4)
#
# Blinda lo que A4 añade sobre A2b/A3b:
#   - una regla que se ejecuta con éxito escribe un item en mem_automation.
#   - una acción que falla (excepción o ActionResult.ok=False) escribe en mem_error.
#   - engine.py emite automation.rule_fired al cerrar cada ejecución REAL
#     (nunca en "skipped" — condiciones no cumplidas / sin ejecutor).
#   - una aprobación resuelta ya escribía en `decisions` desde A1; aquí se
#     verifica que decision_service.history() (Δ9, nuevo en A4) la lista.
#
# Requiere ChromaDB sano (conftest hace initialize_sync a nivel de módulo). Si
# no, se salta — mismo criterio que test_lifecycle.py/test_memory_context.py.
from datetime import datetime

import pytest

from app.automation import (
    AutomationRule,
    AutomationExecution,
    ActionResult,
    Trigger,
    TriggerContext,
    TriggerEvent,
    automation_engine,
    approval_gate,
)
from app.core.events import subscribe, unsubscribe
from app.db.database import Base, SessionLocal, engine as db_engine
from app.db.models import Decision
from app.memory.interfaces import MemoryType
from app.memory.memory_manager import memory_manager
from app.memory.stores.local_store import _collection_name
from app.services import decision_service

pytestmark = pytest.mark.skipif(
    not memory_manager.is_healthy(), reason="ChromaDB no disponible en el entorno de test"
)


def _clean_db_and_mos():
    s = SessionLocal()
    try:
        s.query(AutomationExecution).delete()
        s.query(AutomationRule).delete()
        s.query(Decision).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()
    for mt in (MemoryType.AUTOMATION, MemoryType.ERROR, MemoryType.DECISION):
        _wipe(mt)


@pytest.fixture(autouse=True)
def _tables_and_clean():
    Base.metadata.create_all(bind=db_engine)
    automation_engine.disarm_all()
    # Limpieza TAMBIÉN al entrar: otros archivos de test (A2b/A3) ejecutan
    # reglas reales contra engine.py sin conocer el MOS — desde A4 esas
    # ejecuciones YA escriben en mem_automation/mem_error. Como SQLite reutiliza
    # el id 1 en cuanto la tabla queda vacía, un rule_id=1 de OTRO archivo
    # puede colar residuos en el primer test de este archivo si solo se limpia
    # al salir (bug real encontrado corriendo la suite completa, no solo este
    # archivo en aislado).
    _clean_db_and_mos()
    yield
    automation_engine.disarm_all()
    _clean_db_and_mos()


def _col(mt: MemoryType):
    return memory_manager.get_or_create_collection(_collection_name(mt))


def _wipe(mt: MemoryType):
    col = _col(mt)
    if col is None:
        return
    ids = (col.get() or {}).get("ids") or []
    if ids:
        col.delete(ids=ids)


def _items(mt: MemoryType) -> dict:
    return _col(mt).get() or {}


def _make_rule(action_type: str) -> AutomationRule:
    s = SessionLocal()
    try:
        rule = AutomationRule(
            name="regla de test A4", enabled=True, trigger_type="event",
            trigger_config={}, condition_config={},
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


class _FixedTrigger(Trigger):
    """Mismo patrón que test_automation_isolation.py — arma "a mano" un
    trigger de un solo disparo con un event_key fijo."""

    def __init__(self, event_key: str):
        self._event_key = event_key

    def evaluate(self, ctx: TriggerContext):
        return TriggerEvent(name="fixed", event_key=self._event_key, payload={})

    def arm(self, engine, rule_id: int) -> None:
        pass

    def disarm(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Regla OK → mem_automation
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_regla_ok_escribe_mem_automation():
    async def _exec(config, trigger_event):
        return ActionResult(ok=True, detail="enviado correctamente")

    automation_engine.register_action_executor("test_mos_ok", _exec)
    rule = _make_rule("test_mos_ok")
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="mos-ok-1")

    await automation_engine.handle_trigger(rule.id, TriggerContext())

    items = _items(MemoryType.AUTOMATION)
    metadatas = items.get("metadatas") or []
    match = [m for m in metadatas if m.get("rule_id") == rule.id]
    assert len(match) == 1
    assert match[0]["rule_name"] == rule.name
    assert match[0]["trigger"] == "fixed"


# ---------------------------------------------------------------------------
# Acción fallida (ActionResult.ok=False) → mem_error
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_accion_con_fallo_de_negocio_escribe_mem_error():
    async def _exec(config, trigger_event):
        return ActionResult(ok=False, detail="sin chat_id configurado")

    automation_engine.register_action_executor("test_mos_fail_result", _exec)
    rule = _make_rule("test_mos_fail_result")
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="mos-fail-1")

    await automation_engine.handle_trigger(rule.id, TriggerContext())

    items = _items(MemoryType.ERROR)
    metadatas = items.get("metadatas") or []
    match = [m for m in metadatas if m.get("rule_id") == rule.id]
    assert len(match) == 1
    documents = items.get("documents") or []
    doc = documents[metadatas.index(match[0])]
    assert "sin chat_id configurado" in doc

    # una regla fallida NO cuenta como "ok" para idempotencia — no debe haber
    # escrito nada en mem_automation.
    ok_items = _items(MemoryType.AUTOMATION)
    ok_match = [m for m in (ok_items.get("metadatas") or []) if m.get("rule_id") == rule.id]
    assert ok_match == []


# ---------------------------------------------------------------------------
# Excepción real del ejecutor → también mem_error (mismo camino que ok=False)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_accion_que_lanza_excepcion_escribe_mem_error():
    async def _exec(config, trigger_event):
        raise RuntimeError("boom")

    automation_engine.register_action_executor("test_mos_exception", _exec)
    rule = _make_rule("test_mos_exception")
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="mos-exc-1")

    await automation_engine.handle_trigger(rule.id, TriggerContext())

    items = _items(MemoryType.ERROR)
    metadatas = items.get("metadatas") or []
    match = [m for m in metadatas if m.get("rule_id") == rule.id]
    assert len(match) == 1


# ---------------------------------------------------------------------------
# "skipped" (sin ejecutor / condiciones no cumplidas) NUNCA deja rastro en MOS
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_regla_skipped_no_deja_rastro_en_mos():
    rule = _make_rule("test_mos_sin_ejecutor_action_type")  # nadie registró este action_type
    automation_engine._armed[rule.id] = _FixedTrigger(event_key="mos-skip-1")

    await automation_engine.handle_trigger(rule.id, TriggerContext())

    auto_items = _items(MemoryType.AUTOMATION)
    err_items = _items(MemoryType.ERROR)
    assert [m for m in (auto_items.get("metadatas") or []) if m.get("rule_id") == rule.id] == []
    assert [m for m in (err_items.get("metadatas") or []) if m.get("rule_id") == rule.id] == []


# ---------------------------------------------------------------------------
# Evento automation.rule_fired — se emite en ok/failed, no en skipped
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_evento_rule_fired_se_emite_al_ejecutar():
    received = []

    async def _handler(event):
        received.append(event)

    subscribe("automation.rule_fired", _handler)
    try:
        async def _exec(config, trigger_event):
            return ActionResult(ok=True, detail="hecho")

        automation_engine.register_action_executor("test_mos_event", _exec)
        rule = _make_rule("test_mos_event")
        automation_engine._armed[rule.id] = _FixedTrigger(event_key="mos-event-1")

        await automation_engine.handle_trigger(rule.id, TriggerContext())
        # emit() programa el handler como task — cede el control para que corra.
        import asyncio
        await asyncio.sleep(0)

        assert len(received) == 1
        assert received[0].payload["rule_id"] == rule.id
        assert received[0].payload["ok"] is True
        assert received[0].payload["trigger"] == "fixed"
    finally:
        unsubscribe("automation.rule_fired", _handler)


# ---------------------------------------------------------------------------
# Decision API completa (Δ9) — una aprobación resuelta aparece en history()
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_aprobacion_resuelta_aparece_en_decision_history():
    async def _exec(payload):
        return "ejecutado"

    approval_gate.register_executor("test_mos_history", _exec)
    gate_id = await approval_gate.request_approval(
        kind="test.mos.history", title="Prueba historial", action_type="test_mos_history"
    )
    result = await approval_gate.resolve(gate_id, approved=True, note="aprobado en test")
    assert result.status == "approved"

    rows = await decision_service.history(limit=50)
    match = [r for r in rows if r.title == "Aprobación concedida: Prueba historial"]
    assert len(match) == 1
    assert match[0].body == "aprobado en test"
    assert match[0].created_at is not None

    # filtro por status también funciona (Δ9: history() acepta filtros
    # estructurados, no solo "todo lo reciente").
    active_rows = await decision_service.history(status="active", limit=50)
    assert any(r.id == match[0].id for r in active_rows)
