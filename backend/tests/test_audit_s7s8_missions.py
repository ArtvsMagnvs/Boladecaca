# tests/test_audit_s7s8_missions.py — auditoría runtime, sesión S7·S8 (doc 34)
#
# Fusión de la antigua S7 (gate de PERMISO DE TOOL invisible en Misiones + log
# de permisos engañoso) y la antigua S8 (`mission_id` 404 / `trace_id` 200 en
# los endpoints de /api/tie/missions — reabre la tarea #208). Se fusionaron
# porque el fix de S7 (correlacionar el gate de tool con SU misión en la UI)
# necesita el de S8 (que cualquiera de los dos ids funcione en la API).
#
# Lo que se blinda aquí:
#   1. `tracer.resolve_trace_id` resuelve tanto el trace_id (PK) como el
#      mission_id (lo que anuncia el chat).
#   2. Los 4 endpoints de /api/tie/missions aceptan CUALQUIERA de los dos ids.
#   3. El gate de tool (`tie_tool_permission`, R1) lleva `mission_id` en su
#      `action_payload` — y ese campo, y SOLO ese, se expone en
#      `GET /api/automation/approvals` (el resto del payload sigue oculto).
#   4. El log de una auto-aprobación dice la causa REAL: perfil Autónomo
#      (los toggles no aplican) vs. un permiso individual concedido.
from __future__ import annotations

import json
import logging

import pytest

from app.automation import Approval, approval_gate
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.tie import TaskGraph, TaskNode, tracer, toolloop
from app.tools.tool_manager import tool_manager


@pytest.fixture(autouse=True)
def _clean():
    """[LOG-1] `orchestrator_traces`/`approvals` son tablas GLOBALES — otros
    archivos de test también escriben ahí. Limpiar solo al salir deja que el
    residuo de un archivo anterior se cuele en el primer test de éste cuando
    corren juntos en la misma sesión de pytest; se limpia en ambos extremos."""
    def _purge():
        s = SessionLocal()
        try:
            s.query(OrchestratorTrace).delete()
            s.query(Approval).delete()
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()

    Base.metadata.create_all(bind=db_engine)
    _purge()
    yield
    _purge()


# ---------------------------------------------------------------------------
# (S8) tracer.resolve_trace_id
# ---------------------------------------------------------------------------
def test_resolve_trace_id_por_pk():
    from app.tie import new_mission

    m = new_mission("por pk", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    assert tracer.resolve_trace_id(trace_id) == trace_id


def test_resolve_trace_id_por_mission_id():
    """El caso que motivó S8: el chat anuncia el mission_id, no el trace_id."""
    from app.tie import new_mission

    m = new_mission("por mission_id", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    assert tracer.resolve_trace_id(m.id) == trace_id


def test_resolve_trace_id_inexistente_da_none():
    assert tracer.resolve_trace_id("no-existe-ni-como-trace-ni-como-mission") is None


# ---------------------------------------------------------------------------
# (S8) los 4 endpoints aceptan AMBOS ids
# ---------------------------------------------------------------------------
def test_endpoint_get_mission_acepta_mission_id(client):
    from app.tie import new_mission

    m = new_mission("get via mission_id", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = TaskGraph(id="ge", mission_id=m.id, nodes={"n1": TaskNode(id="n1", goal="paso")})
    tracer.record_plan(trace_id, g)

    # el contrato de siempre sigue intacto: el trace_id real también funciona
    r_pk = client.get(f"/api/tie/missions/{trace_id}")
    assert r_pk.status_code == 200

    r = client.get(f"/api/tie/missions/{m.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["trace_id"] == trace_id
    assert body["mission_id"] == m.id
    assert body["graph"]["nodes"]["n1"]["goal"] == "paso"


def test_endpoint_delete_mission_acepta_mission_id(client):
    from app.tie import new_mission

    m = new_mission("delete via mission_id", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    tracer.record_end(trace_id, outcome="listo", state="done")

    r = client.delete(f"/api/tie/missions/{m.id}")
    assert r.status_code == 200 and r.json()["deleted"] is True
    assert r.json()["trace_id"] == trace_id
    # y ya no existe por ninguno de los dos ids
    assert client.get(f"/api/tie/missions/{trace_id}").status_code == 404


def test_endpoint_cancel_mission_acepta_mission_id(client):
    from app.tie import executor, new_mission

    m = new_mission("cancel via mission_id", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")

    r = client.post(f"/api/tie/missions/{m.id}/cancel")
    assert r.status_code == 200 and r.json()["cancelled"] is True
    assert r.json()["trace_id"] == trace_id
    assert executor.is_cancelled(m.id)
    executor._CANCELLED.discard(m.id)


def test_endpoint_approve_plan_acepta_mission_id(client, monkeypatch):
    """`resolve_plan` (la lógica real de aprobar un plan, con toda su
    plomería de gates) se aísla aquí: lo que se blinda es que el ENDPOINT
    resuelve el id ANTES de invocarla — no que `resolve_plan` en sí funcione
    (eso ya lo cubre test_tie_handle.py)."""
    import app.api.endpoints.tie as tie_ep
    from app.tie import new_mission

    m = new_mission("plan pendiente via mission_id", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")

    seen = []

    async def _fake_resolve_plan(resolved_trace_id, approved, note):
        seen.append(resolved_trace_id)
        return {"approved": approved, "executed": True}

    monkeypatch.setattr(tie_ep, "resolve_plan", _fake_resolve_plan)

    r = client.post(f"/api/tie/missions/{m.id}/approve-plan", json={"approved": True})
    assert r.status_code == 200
    assert seen == [trace_id]          # resolve_plan recibió el trace_id REAL, no el mission_id
    assert r.json()["trace_id"] == trace_id


def test_endpoint_get_mission_404_con_id_totalmente_inventado(client):
    """No-regresión: un id que no encaja con nada sigue dando 404 limpio."""
    assert client.get("/api/tie/missions/esto-no-existe-de-ninguna-forma").status_code == 404


# ---------------------------------------------------------------------------
# (S7-a) el gate de tool lleva mission_id en su action_payload
# ---------------------------------------------------------------------------
def _fake_mel(monkeypatch, responses: list[str]):
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    queue = list(responses)

    async def _complete(req):
        text = queue.pop(0) if queue else '{"answer": "sin más que decir"}'
        return ExecutionResult(text=text, ok=True,
                               served_by=ServedBy("fake", "fake-model"), usage=Usage(tokens=1))

    monkeypatch.setattr(mel, "complete", _complete)


class _FakeGate:
    """Mismo doble que test_tie_toolloop.py: responde lo que se le diga sin
    tocar la BD, y guarda TODO lo que se le pidió (incl. action_payload)."""
    def __init__(self, verdict: str):
        self.verdict = verdict
        self.asked: list[dict] = []

    async def request_approval(self, **kwargs):
        self.asked.append(kwargs)
        return "gate-de-prueba"

    def get(self, gate_id):
        class _A:
            status = self.verdict
        return _A()

    async def expire(self, gate_id, note=""):
        return False


@pytest.mark.anyio
async def test_gate_de_tool_lleva_mission_id_en_el_payload(monkeypatch):
    from app.automation import permission_service

    # Determinismo: sin depender del estado ambiente de Permisos que puedan
    # haber dejado otros archivos de test — se fuerza a "sigue preguntando".
    monkeypatch.setattr(permission_service, "is_tool_action_pre_authorized", lambda *a, **k: False)
    monkeypatch.setattr(permission_service, "autonomy_is_full", lambda: False)

    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "email", "action": "send_email",
                             "params": {"to": "x@y.com", "subject": "s", "body": "b"}}}),
        '{"answer": "listo"}',
    ])
    gate = _FakeGate("approved")

    async def _spy(**kwargs):
        return {"success": True, "result": {"message_id": "m1"}, "error": None}

    monkeypatch.setattr(tool_manager, "execute", _spy)

    await toolloop.run(
        instruction="envía un email", context="", allowed_tools=["email"],
        tool_manager=tool_manager, max_iters=3, approval_gate=gate,
        session_key="mission-abc123",
    )

    assert gate.asked, "debía pedirse permiso"
    assert gate.asked[0]["action_payload"]["mission_id"] == "mission-abc123"


@pytest.mark.anyio
async def test_gate_de_tool_sin_session_key_lleva_mission_id_none(monkeypatch):
    """No-regresión: el campo es ADITIVO — sin session_key (caminos que no lo
    pasan) el payload sigue teniendo la forma de siempre, solo que con
    mission_id=None en vez de faltar la clave. Se fija la pre-autorización a
    False explícitamente para no depender del estado ambiente de Permisos
    dejado por otros archivos de test (determinismo, no ambigüedad)."""
    from app.automation import permission_service

    monkeypatch.setattr(permission_service, "is_tool_action_pre_authorized", lambda *a, **k: False)
    monkeypatch.setattr(permission_service, "autonomy_is_full", lambda: False)

    gate = _FakeGate("approved")
    granted, _ = await toolloop._ask_permission(
        {"tool_id": "email", "action": "send_email"}, {"to": "x"}, gate,
        instruction="x",
    )
    assert granted is True
    assert gate.asked[0]["action_payload"]["mission_id"] is None


# ---------------------------------------------------------------------------
# (S7-b) `GET /api/automation/approvals` expone mission_id (y SOLO eso del
# payload crudo — el resto sigue oculto por diseño de A1).
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_approvals_endpoint_expone_mission_id_cuando_esta_presente(client):
    gate_id = await approval_gate.request_approval(
        kind="tool.email.send_email", title="permiso de prueba",
        action_type="tie_tool_permission",
        action_payload={"tool_id": "email", "action": "send_email", "params": {},
                        "mission_id": "mission-xyz"},
    )
    r = client.get("/api/automation/approvals")
    assert r.status_code == 200
    row = next(a for a in r.json() if a["gate_id"] == gate_id)
    assert row["mission_id"] == "mission-xyz"
    # y el resto del payload sigue SIN exponerse crudo (A1, sin cambios aquí)
    assert "params" not in row and "action_payload" not in row


@pytest.mark.anyio
async def test_approvals_endpoint_mission_id_none_si_no_esta_en_el_payload(client):
    gate_id = await approval_gate.request_approval(
        kind="email.send", title="otro permiso", action_type="email_send",
        action_payload={"to": "x@y.com"},
    )
    r = client.get("/api/automation/approvals")
    row = next(a for a in r.json() if a["gate_id"] == gate_id)
    assert row["mission_id"] is None


# ---------------------------------------------------------------------------
# (S7-c) el log de una auto-aprobación dice la causa REAL
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_log_pre_autorizado_por_perfil_autonomo_lo_dice(monkeypatch, caplog):
    from app.automation import permission_service

    monkeypatch.setattr(permission_service, "is_tool_action_pre_authorized", lambda *a, **k: True)
    monkeypatch.setattr(permission_service, "autonomy_is_full", lambda: True)

    caplog.set_level(logging.INFO, logger="tie.toolloop")
    granted, reason = await toolloop._ask_permission(
        {"tool_id": "email", "action": "send_email"}, {}, approval_gate=None,
        instruction="x", mission_id="m1",
    )
    assert granted is True
    assert any("perfil Autónomo" in r.message for r in caplog.records)


@pytest.mark.anyio
async def test_log_pre_autorizado_por_toggle_no_menciona_perfil_autonomo(monkeypatch, caplog):
    from app.automation import permission_service

    monkeypatch.setattr(permission_service, "is_tool_action_pre_authorized", lambda *a, **k: True)
    monkeypatch.setattr(permission_service, "autonomy_is_full", lambda: False)

    caplog.set_level(logging.INFO, logger="tie.toolloop")
    granted, reason = await toolloop._ask_permission(
        {"tool_id": "email", "action": "send_email"}, {}, approval_gate=None,
        instruction="x", mission_id="m1",
    )
    assert granted is True
    assert any("Ajustes → Permisos" in r.message for r in caplog.records)
    assert not any("perfil Autónomo" in r.message for r in caplog.records)
