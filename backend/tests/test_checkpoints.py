# tests/test_checkpoints.py — R5: checkpoints verificables, avisos y cron
# (doc 23 §3·R5)
#
# EL FLUJO QUE PIDIÓ EL USUARIO: el Orquestador planifica, ejecuta, y cada vez
# que completa algo que él PUEDE COMPROBAR, para y avisa por su canal.
#
# Los 4 criterios de éxito del sprint, más los casos límite que los rodean. Lo
# único fake es el LLM y la entrega del canal; el ApprovalGate, el executor, el
# grafo, el scheduler y la BD son REALES.
from __future__ import annotations

import asyncio
import json

import pytest

from app.automation import Approval, approval_gate
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.tie import (
    AgentResult,
    AgentRuntime,
    NodeState,
    RuntimeHealth,
    TaskGraph,
    TaskNode,
    executor,
    new_mission,
    register_runtime,
    tracer,
)


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    executor.register_gate_handlers()
    executor._CANCELLED.clear()
    executor._NODE_TASKS.clear()
    yield
    executor._CANCELLED.clear()
    executor._NODE_TASKS.clear()
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(Approval).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


class _Rt(AgentRuntime):
    """Runtime determinista: devuelve un texto reconocible por nodo."""

    def __init__(self):
        self.calls: list[str] = []

    @property
    def capabilities(self):
        return {"chat"}

    async def execute_task(self, task, memory, tools, approval_gate):
        self.calls.append(task.instruction)
        return AgentResult(task_id=task.id, success=True,
                           output=f"resultado de {task.instruction}", tokens=1)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


@pytest.fixture
def rt():
    r = _Rt()
    register_runtime("cprt", r)
    return r


async def _true(*a, **k):
    return True


def _capture_notifications(monkeypatch) -> list[str]:
    """Intercepta el push del canal. Se mockea la ENTREGA, no la decisión: así
    se comprueba que el aviso se dispara y con el contenido correcto."""
    import app.core.notify as notify_mod

    enviados: list[str] = []

    async def _fake(text, *, channel=None):
        enviados.append(text)
        return True

    monkeypatch.setattr(notify_mod, "notify_user", _fake)
    return enviados


def _graph_con_checkpoint(mission_id: str) -> TaskGraph:
    """n1 (entregable) → n2. La misión debe pararse al terminar n1."""
    return TaskGraph(id="g-cp", mission_id=mission_id, nodes={
        "n1": TaskNode(id="n1", goal="redactar el borrador", runtime="cprt", checkpoint=True),
        "n2": TaskNode(id="n2", goal="enviar el borrador", runtime="cprt", depends_on=["n1"]),
    })


# ===========================================================================
# Criterio 1 — un plan con checkpoint PARA ahí y avisa
# ===========================================================================
@pytest.mark.anyio
async def test_la_mision_para_en_el_checkpoint_y_avisa(monkeypatch, rt):
    avisos = _capture_notifications(monkeypatch)

    m = new_mission("preparar y enviar el borrador", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = _graph_con_checkpoint(m.id)
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    # El entregable SE HIZO (no se pide permiso antes: eso es approval_required).
    assert g.nodes["n1"].state == NodeState.DONE
    assert rt.calls == ["redactar el borrador"], "n2 no debía ejecutarse todavía"
    # Y la misión está esperando.
    assert m.state == "waiting"
    assert g.nodes["n1"].checkpoint_gate_id
    pendientes = [a for a in approval_gate.list_pending() if a.kind == "tie.checkpoint"]
    assert len(pendientes) == 1
    # El aviso salió, y lleva lo que el paso produjo DE VERDAD.
    assert avisos, "no se avisó al usuario"
    assert "resultado de redactar el borrador" in avisos[0]


# ===========================================================================
# Criterio 2 — al aprobar, continúa donde estaba (reanudación de T3)
# ===========================================================================
@pytest.mark.anyio
async def test_al_aprobar_el_checkpoint_la_mision_sigue(monkeypatch, rt):
    import app.core.notify as notify_mod
    monkeypatch.setattr(notify_mod, "notify_user", _true)

    m = new_mission("preparar y enviar", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = _graph_con_checkpoint(m.id)
    tracer.record_plan(trace_id, g)
    await executor.run(g, m, trace_id=trace_id)

    gate = [a for a in approval_gate.list_pending() if a.kind == "tie.checkpoint"][0]
    await approval_gate.resolve(gate.id, approved=True, note="me vale")
    await asyncio.sleep(0.1)   # la reanudación es event-driven, en background

    final = tracer.load_graph(trace_id)
    assert final.nodes["n1"].state == NodeState.DONE
    assert final.nodes["n2"].state == NodeState.DONE, "no continuó tras aprobar"
    assert rt.calls == ["redactar el borrador", "enviar el borrador"]


# ===========================================================================
# Rechazar un entregable: no vale, y lo que dependía de él se salta
# ===========================================================================
@pytest.mark.anyio
async def test_si_el_entregable_no_vale_no_se_sigue_con_lo_que_dependia(monkeypatch, rt):
    import app.core.notify as notify_mod
    monkeypatch.setattr(notify_mod, "notify_user", _true)

    m = new_mission("preparar y enviar", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = _graph_con_checkpoint(m.id)
    tracer.record_plan(trace_id, g)
    await executor.run(g, m, trace_id=trace_id)

    gate = [a for a in approval_gate.list_pending() if a.kind == "tie.checkpoint"][0]
    await approval_gate.resolve(gate.id, approved=False, note="no me vale")
    await asyncio.sleep(0.1)

    final = tracer.load_graph(trace_id)
    assert final.nodes["n1"].state == NodeState.FAILED
    assert final.nodes["n2"].state == NodeState.SKIPPED, "no debía enviarse un borrador rechazado"
    assert rt.calls == ["redactar el borrador"]


# ===========================================================================
# Casos límite del diseño
# ===========================================================================
@pytest.mark.anyio
async def test_un_checkpoint_al_final_no_para_por_nada(monkeypatch, rt):
    """Si no queda trabajo, pararse sería pedir permiso para seguir con nada: el
    responder le entrega el resultado igualmente."""
    import app.core.notify as notify_mod
    avisos = []
    async def _n(text, *, channel=None):
        avisos.append(text); return True
    monkeypatch.setattr(notify_mod, "notify_user", _n)

    m = new_mission("solo un paso", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = TaskGraph(id="g-solo", mission_id=m.id, nodes={
        "n1": TaskNode(id="n1", goal="generar el informe", runtime="cprt", checkpoint=True),
    })
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert m.state == "done", "no debía quedarse esperando: no hay nada después"
    assert not [a for a in approval_gate.list_pending() if a.kind == "tie.checkpoint"]
    assert not avisos


@pytest.mark.anyio
async def test_un_paso_que_falla_no_pide_que_lo_revises(monkeypatch):
    """Sólo se para en entregables que SALIERON BIEN. De un fallo ya se encarga
    la degradación de T3 — pedir que revises algo roto sería ruido."""
    import app.core.notify as notify_mod
    monkeypatch.setattr(notify_mod, "notify_user", _true)

    class _Roto(_Rt):
        async def execute_task(self, task, memory, tools, approval_gate):
            self.calls.append(task.instruction)
            return AgentResult(task_id=task.id, success=False, output="", error="reventó")

    register_runtime("cprt_roto", _Roto())
    m = new_mission("x", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = TaskGraph(id="g-roto", mission_id=m.id, nodes={
        "n1": TaskNode(id="n1", goal="paso que falla", runtime="cprt_roto", checkpoint=True),
        "n2": TaskNode(id="n2", goal="siguiente", runtime="cprt_roto", depends_on=["n1"]),
    })
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert g.nodes["n1"].state == NodeState.FAILED
    assert not [a for a in approval_gate.list_pending() if a.kind == "tie.checkpoint"]


@pytest.mark.anyio
async def test_el_checkpoint_sobrevive_a_un_reinicio(monkeypatch, rt):
    """El usuario aprueba con el backend caído: el evento se pierde (el bus es
    in-process), así que al arrancar hay que leer el veredicto del disco."""
    import app.core.notify as notify_mod
    monkeypatch.setattr(notify_mod, "notify_user", _true)

    m = new_mission("preparar y enviar", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = _graph_con_checkpoint(m.id)
    tracer.record_plan(trace_id, g)
    await executor.run(g, m, trace_id=trace_id)

    gate = [a for a in approval_gate.list_pending() if a.kind == "tie.checkpoint"][0]

    # "Backend caído": se desengancha el handler del bus antes de resolver.
    from app.core import events
    events.unsubscribe("approval.resolved", executor._on_approval_resolved)
    try:
        await approval_gate.resolve(gate.id, approved=True, note="ok offline")
        await asyncio.sleep(0.05)
        assert tracer.load_graph(trace_id).nodes["n2"].state == NodeState.PENDING
    finally:
        executor.register_gate_handlers()

    # "Arranque": resume_pending lo recupera leyendo el veredicto persistido.
    reanudadas = await executor.resume_pending()
    assert reanudadas >= 1
    assert tracer.load_graph(trace_id).nodes["n2"].state == NodeState.DONE


@pytest.mark.anyio
async def test_un_canal_de_avisos_roto_no_rompe_la_mision(monkeypatch, rt):
    """Fail-soft de doc 23 R5: el aviso es un extra; la aprobación ya está en la
    UI. Si el canal revienta, la misión debe quedar igualmente en espera."""
    import app.core.notify as notify_mod

    async def _revienta(text, *, channel=None):
        raise RuntimeError("Telegram caído")
    monkeypatch.setattr(notify_mod, "notify_user", _revienta)

    m = new_mission("x", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = _graph_con_checkpoint(m.id)
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert m.state == "waiting"
    assert len([a for a in approval_gate.list_pending() if a.kind == "tie.checkpoint"]) == 1


# ===========================================================================
# El canal preferido
# ===========================================================================
def test_el_canal_por_defecto_es_la_ui_y_se_puede_cambiar():
    from app.core.notify import get_preferred_channel, set_preferred_channel

    assert get_preferred_channel() == "ui"
    assert set_preferred_channel("telegram") == "telegram"
    assert get_preferred_channel() == "telegram"
    set_preferred_channel("ui")


@pytest.mark.anyio
async def test_con_canal_ui_no_se_empuja_nada():
    """"ui" significa "lo veo al abrir Aithera": no hay push, y eso NO es un
    error — por eso devuelve False sin quejarse."""
    from app.core.notify import notify_user

    assert await notify_user("hola", channel="ui") is False


@pytest.mark.anyio
async def test_telegram_sin_chat_id_no_promete_un_aviso_que_no_llega():
    from app.core.notify import notify_user

    assert await notify_user("hola", channel="telegram") is False


# ===========================================================================
# Criterio 4 — cron creado por chat: se arma y sobrevive a un reinicio
# ===========================================================================
@pytest.mark.anyio
async def test_cron_creado_por_chat_queda_armado_y_sobrevive_al_reinicio(client):
    """`client` arranca el lifespan real (APScheduler incluido)."""
    from app.automation import AutomationRule, automation_engine, scheduler_service
    from app.tools.tool_manager import tool_manager

    r = await tool_manager.execute("aithera", "create_cron_job", {
        "name": "[test R5] recordatorio diario", "hour": 9, "minute": 15,
        "action_type": "chat_query", "action_config": {"prompt": "buenos días"},
    })
    assert r["success"], r
    rule_id = r["result"]["id"]

    # Nace ACTIVO: el usuario lo ha pedido explícitamente (a diferencia de las
    # reglas predefinidas de A3, que nadie pidió).
    assert r["result"]["enabled"] is True
    assert f"automation_rule_{rule_id}" in scheduler_service.jobs()

    # "Reinicio": se desarma todo y se recarga desde la BD, como en el lifespan.
    automation_engine.disarm_rule(rule_id)
    assert f"automation_rule_{rule_id}" not in scheduler_service.jobs()

    automation_engine.load_rules()
    assert rule_id in automation_engine.armed_rule_ids(), "no se re-armó al arrancar"
    assert f"automation_rule_{rule_id}" in scheduler_service.jobs()

    # Limpieza.
    automation_engine.disarm_rule(rule_id)
    db = SessionLocal()
    try:
        row = db.get(AutomationRule, rule_id)
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()


@pytest.mark.anyio
async def test_el_gate_de_checkpoint_tiene_ejecutor_registrado(monkeypatch, rt):
    """Cazado en la verificación en vivo: sin un ejecutor para
    `tie_checkpoint`, el ApprovalGate loguea "sin ejecutor para action_type=..."
    como ERROR al resolverlo — un fallo que no existe, ensuciando la auditoría.
    Mismo motivo por el que T3 registró uno para `tie_resume`."""
    import app.core.notify as notify_mod

    monkeypatch.setattr(notify_mod, "notify_user", _true)
    executor.register_gate_handlers()

    assert approval_gate.has_executor(executor.CHECKPOINT_ACTION_TYPE), (
        "el gate del checkpoint no tiene ejecutor: resolverlo generará un ERROR falso"
    )

    m = new_mission("x", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = _graph_con_checkpoint(m.id)
    tracer.record_plan(trace_id, g)
    await executor.run(g, m, trace_id=trace_id)

    gate = [a for a in approval_gate.list_pending() if a.kind == "tie.checkpoint"][0]
    res = await approval_gate.resolve(gate.id, approved=True, note="ok")
    await asyncio.sleep(0.1)
    # `executed=True` es la prueba de que SÍ había ejecutor y corrió limpio:
    # sin él sería False y el gate habría logueado un ERROR falso.
    assert res.executed is True, res
    assert res.error is None, res.error
