# tests/test_approval_gate.py — ApprovalGate (V0.9 A1, doc 11 §A.2 / doc 20)
#
# El ApprovalGate es EL primitivo genérico (lo reusan V1.0 Orchestrator y V1.1
# Hermes/skills). Su prueba de fuego: SOBREVIVIR A UN REINICIO del backend. Aquí
# se valida el contrato completo:
#   - request -> pending (persistido)
#   - resolve aprobado -> ejecuta la acción + escribe en `decisions`
#   - resolve rechazado -> NO ejecuta
#   - reanudación tras reinicio (una instancia NUEVA del gate resuelve una
#     aprobación creada antes, reconstruyendo la acción desde su action_payload)
#   - idempotencia (doble resolve no re-ejecuta)
#   - emisión de approval.requested / approval.resolved
#   - endpoints /api/automation/approvals (list + resolve)
#   - main.py registra el ejecutor 'email_send' (migración del email-confirm)

import pytest

from app.automation import Approval, ApprovalGate, approval_gate
from app.automation import approval as approval_mod
from app.db.database import Base, SessionLocal, engine
from app.db.models import Decision


@pytest.fixture(autouse=True)
def _tables_and_clean():
    """Asegura las tablas (create_all idempotente) y limpia approvals/decisions
    entre tests para que las aserciones no arrastren filas de otros tests."""
    Base.metadata.create_all(bind=engine)
    yield
    s = SessionLocal()
    try:
        s.query(Approval).delete()
        s.query(Decision).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


# --------------------------------------------------------------------------
# API Python del gate (async)
# --------------------------------------------------------------------------
@pytest.mark.anyio
async def test_request_crea_pending_persistido():
    gate_id = await approval_gate.request_approval(
        kind="test", title="Enviar informe", action_type="noop", action_payload={"x": 1}
    )
    appr = approval_gate.get(gate_id)
    assert appr is not None
    assert appr.status == "pending"
    assert appr.action_type == "noop"
    assert appr.action_payload == {"x": 1}
    assert any(a.id == gate_id for a in approval_gate.list_pending())


@pytest.mark.anyio
async def test_resolve_aprobado_ejecuta_y_escribe_decision():
    ran = {}

    async def _exec(payload):
        ran["payload"] = payload
        return "hecho"

    approval_gate.register_executor("run_ok", _exec)
    gate_id = await approval_gate.request_approval(
        kind="test", title="Acción X", action_type="run_ok", action_payload={"a": 2}
    )
    result = await approval_gate.resolve(gate_id, approved=True, note="ok va")

    assert result.status == "approved"
    assert result.executed is True
    assert result.result == "hecho"
    assert ran["payload"] == {"a": 2}
    # la aprobación quedó resuelta y fuera de pendientes
    assert approval_gate.get(gate_id).status == "approved"
    assert all(a.id != gate_id for a in approval_gate.list_pending())
    # se escribió una decisión (Decision API) por la aprobación
    s = SessionLocal()
    try:
        decs = s.query(Decision).filter(Decision.title.like("Aprobación concedida:%")).all()
        assert len(decs) == 1
        assert approval_gate.get(gate_id).decision_id == decs[0].id
    finally:
        s.close()


@pytest.mark.anyio
async def test_resolve_rechazado_no_ejecuta():
    ran = {"count": 0}

    async def _exec(payload):
        ran["count"] += 1
        return "no debería correr"

    approval_gate.register_executor("run_reject", _exec)
    gate_id = await approval_gate.request_approval(
        kind="test", title="Acción rechazable", action_type="run_reject"
    )
    result = await approval_gate.resolve(gate_id, approved=False, note="paso")

    assert result.status == "rejected"
    assert result.executed is False
    assert ran["count"] == 0
    assert approval_gate.get(gate_id).status == "rejected"


@pytest.mark.anyio
async def test_reanudacion_tras_reinicio():
    """Simula un reinicio: se crea la aprobación, y una instancia NUEVA del gate
    (con su registro de ejecutores re-poblado, como en el arranque) la resuelve
    reconstruyendo la acción desde la fila persistida. La aprobación 'sobrevive'."""
    # 1) el gate vivo crea la aprobación (queda en la tabla `approvals`)
    gate_id = await approval_gate.request_approval(
        kind="test", title="Persistente", action_type="run_resumed", action_payload={"v": 9}
    )

    # 2) "reinicio": un gate nuevo, en memoria limpia, re-registra sus ejecutores
    fresh = ApprovalGate()
    seen = {}

    async def _exec(payload):
        seen["v"] = payload.get("v")
        return "reanudado"

    fresh.register_executor("run_resumed", _exec)

    # 3) el gate nuevo resuelve la aprobación creada ANTES del "reinicio"
    result = await fresh.resolve(gate_id, approved=True)
    assert result.executed is True
    assert result.result == "reanudado"
    assert seen["v"] == 9
    assert fresh.get(gate_id).status == "approved"


@pytest.mark.anyio
async def test_idempotencia_doble_resolve_no_reejecuta():
    ran = {"count": 0}

    async def _exec(payload):
        ran["count"] += 1
        return ran["count"]

    approval_gate.register_executor("run_once", _exec)
    gate_id = await approval_gate.request_approval(
        kind="test", title="Una sola vez", action_type="run_once"
    )
    r1 = await approval_gate.resolve(gate_id, approved=True)
    r2 = await approval_gate.resolve(gate_id, approved=True)  # segundo intento
    r3 = await approval_gate.resolve(gate_id, approved=False)  # incluso cambiando

    assert r1.executed is True
    assert r2.executed is False and r2.status == "approved"
    assert r3.executed is False and r3.status == "approved"
    assert ran["count"] == 1  # el ejecutor corrió UNA sola vez


@pytest.mark.anyio
async def test_resolve_aprobado_sin_ejecutor_no_rompe():
    gate_id = await approval_gate.request_approval(
        kind="test", title="Sin ejecutor", action_type="no_existe_executor"
    )
    result = await approval_gate.resolve(gate_id, approved=True)
    assert result.status == "approved"
    assert result.executed is False
    assert "sin ejecutor" in (result.error or "")


@pytest.mark.anyio
async def test_emite_eventos_request_y_resolved(monkeypatch):
    eventos = []
    monkeypatch.setattr(
        approval_mod, "emit",
        lambda name, source, payload: eventos.append((name, payload)),
    )

    async def _exec(payload):
        return "ok"

    approval_gate.register_executor("run_ev", _exec)
    gate_id = await approval_gate.request_approval(
        kind="test", title="Con eventos", action_type="run_ev"
    )
    await approval_gate.resolve(gate_id, approved=True)

    names = [n for n, _ in eventos]
    assert "approval.requested" in names
    assert "approval.resolved" in names
    resolved_payload = dict(eventos)["approval.resolved"]
    assert resolved_payload["gate_id"] == gate_id
    assert resolved_payload["resolution"] == "approved"


# --------------------------------------------------------------------------
# Endpoints HTTP (sync, via TestClient)
# --------------------------------------------------------------------------
def test_endpoints_list_get_resolve(client):
    # crear una aprobación directamente en BD (sin el gate async) para el test HTTP
    s = SessionLocal()
    try:
        s.add(Approval(
            id="gate-http-1", kind="test", title="HTTP T",
            action_type="http_noop", action_payload={}, status="pending", channel="hub",
        ))
        s.commit()
    finally:
        s.close()

    called = {"yes": False}

    async def _noop(payload):
        called["yes"] = True
        return "ok"

    approval_gate.register_executor("http_noop", _noop)

    # GET pendientes
    r = client.get("/api/automation/approvals")
    assert r.status_code == 200
    assert any(a["gate_id"] == "gate-http-1" for a in r.json())

    # GET uno
    r = client.get("/api/automation/approvals/gate-http-1")
    assert r.status_code == 200 and r.json()["title"] == "HTTP T"

    # POST resolve (aprobado)
    r = client.post("/api/automation/approvals/gate-http-1/resolve", json={"approved": True})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "approved" and body["executed"] is True
    assert called["yes"] is True

    # 404 en id inexistente
    assert client.get("/api/automation/approvals/no-existe").status_code == 404
    assert client.post(
        "/api/automation/approvals/no-existe/resolve", json={"approved": True}
    ).status_code == 404


def test_lifespan_registra_ejecutor_email_send(client):
    """La migración del email-confirm: main.py registra 'email_send' en el arranque
    (el /api/email/send con confirmed:true sigue intacto — eso lo cubre
    test_email_contracts)."""
    assert approval_gate.has_executor("email_send") is True
