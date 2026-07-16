# tests/test_permissions.py — Permisos & Autonomía (V0.9 A3b, doc 20 §A3b)
#
# La capa de política sobre el ApprovalGate. Blinda: fail-CLOSED por defecto
# (sin fila en Config = NO pre-autorizado), toggle persiste, perfiles setean
# todos los permisos disponibles de una vez, y — lo crítico — la integración
# real con request_approval: un permiso OFF sigue abriendo el gate (pending),
# uno ON lo auto-resuelve SIN saltarse la auditoría (rastro en `approvals`
# con resolution_note="auto...").
import pytest

from app.automation import (
    Approval,
    AutomationExecution,
    AutomationRule,
    approval_gate,
    permission_service,
)
from app.automation.permissions import CATALOG, PROFILES
from app.db.database import Base, SessionLocal, engine as db_engine
from app.db.models import Config


@pytest.fixture(autouse=True)
def _tables_and_clean():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(Config).filter(Config.key.like("permission.%")).delete(synchronize_session=False)
        s.query(Config).filter(Config.key == "autonomy_profile").delete()
        s.query(Approval).delete()
        s.query(AutomationExecution).delete()
        s.query(AutomationRule).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Catálogo + fail-closed por defecto
# ---------------------------------------------------------------------------
def test_catalogo_tiene_9_permisos_2_no_disponibles():
    assert len(CATALOG) == 9
    unavailable = [p for p in CATALOG if not p.available]
    assert {p.id for p in unavailable} == {"browser.use", "computer.use"}


def test_sin_config_nada_esta_pre_autorizado():
    for p in CATALOG:
        assert permission_service.is_pre_authorized(p.id) is False


def test_permiso_desconocido_nunca_pre_autorizado():
    assert permission_service.is_pre_authorized("algo.que.no.existe") is False


def test_permiso_no_disponible_no_se_puede_activar():
    with pytest.raises(ValueError, match="no disponible"):
        permission_service.set_permission("browser.use", True)


def test_permiso_inexistente_lanza():
    with pytest.raises(ValueError, match="desconocido"):
        permission_service.set_permission("algo.raro", True)


# ---------------------------------------------------------------------------
# Toggle individual — persiste en Config, is_pre_authorized lo refleja
# ---------------------------------------------------------------------------
def test_toggle_persiste_y_se_refleja_en_is_pre_authorized():
    assert permission_service.is_pre_authorized("email.send") is False

    permission_service.set_permission("email.send", True)
    assert permission_service.is_pre_authorized("email.send") is True

    permission_service.set_permission("email.send", False)
    assert permission_service.is_pre_authorized("email.send") is False


def test_catalogo_con_estado_refleja_el_toggle():
    permission_service.set_permission("workspace.write", True)
    catalog = permission_service.get_catalog()
    entry = next(p for p in catalog.permissions if p.id == "workspace.write")
    assert entry.enabled is True
    others = [p for p in catalog.permissions if p.id != "workspace.write" and p.available]
    assert all(p.enabled is False for p in others)


# ---------------------------------------------------------------------------
# Perfiles — setean TODOS los disponibles de golpe
# ---------------------------------------------------------------------------
def test_perfil_manual_deja_todo_apagado():
    permission_service.set_permission("email.send", True)  # algo encendido antes
    permission_service.apply_profile("manual")
    catalog = permission_service.get_catalog()
    assert catalog.profile == "manual"
    assert all(not p.enabled for p in catalog.permissions)


def test_perfil_balanced_enciende_solo_bajo_riesgo():
    permission_service.apply_profile("balanced")
    catalog = permission_service.get_catalog()
    assert catalog.profile == "balanced"
    low_risk_available = {p.id for p in CATALOG if p.available and p.risk == "low"}
    for p in catalog.permissions:
        if not p.available:
            continue
        assert p.enabled == (p.id in low_risk_available)


def test_perfil_full_enciende_todo_lo_disponible():
    permission_service.apply_profile("full")
    catalog = permission_service.get_catalog()
    assert catalog.profile == "full"
    for p in catalog.permissions:
        assert p.enabled == p.available  # todo lo disponible ON, lo futuro sigue OFF


def test_perfil_desconocido_lanza():
    with pytest.raises(ValueError, match="desconocido"):
        permission_service.apply_profile("omnisciente")


def test_profiles_dict_coincide_con_el_catalogo():
    """PROFILES no debe referenciar ids que no existan en CATALOG (invariante
    interna — si se borra un permiso del catálogo, esto lo detecta)."""
    all_ids = {p.id for p in CATALOG}
    for ids in PROFILES.values():
        assert ids.issubset(all_ids)


# ---------------------------------------------------------------------------
# Integración con el gate — lo crítico: OFF pregunta, ON auto-resuelve CON rastro
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_permiso_off_el_gate_sigue_preguntando():
    async def _exec(payload):
        return "no deberia importar aqui"

    approval_gate.register_executor("test_perm_off", _exec)
    gate_id = await approval_gate.request_approval(
        kind="test.permiso.off", title="Prueba", action_type="test_perm_off"
    )

    appr = approval_gate.get(gate_id)
    assert appr.status == "pending"  # sigue esperando al usuario


@pytest.mark.anyio
async def test_permiso_on_auto_resuelve_con_rastro_de_auditoria():
    ran = {"count": 0}

    async def _exec(payload):
        ran["count"] += 1
        return "ejecutado automaticamente"

    approval_gate.register_executor("test_perm_on", _exec)
    permission_service.set_permission("email.send", True)

    gate_id = await approval_gate.request_approval(
        kind="email.send", title="Enviar factura", action_type="test_perm_on"
    )

    appr = approval_gate.get(gate_id)
    # NUNCA se salta en silencio: hay una fila, ya resuelta, con rastro claro.
    assert appr is not None
    assert appr.status == "approved"
    assert appr.resolution_note == "auto (permiso pre-autorizado)"
    assert appr.resolved_at is not None
    assert ran["count"] == 1  # la acción SÍ corrió


@pytest.mark.anyio
async def test_permiso_on_no_afecta_a_un_kind_distinto():
    """Pre-autorizar email.send no debe pre-autorizar telegram.send — cada
    permiso gobierna solo su propio `kind`."""
    async def _exec(payload):
        return "x"

    approval_gate.register_executor("test_perm_scope", _exec)
    permission_service.set_permission("email.send", True)

    gate_id = await approval_gate.request_approval(
        kind="telegram.send", title="Mensaje", action_type="test_perm_scope"
    )
    appr = approval_gate.get(gate_id)
    assert appr.status == "pending"  # telegram.send sigue OFF, distinto de email.send


@pytest.mark.anyio
async def test_permiso_on_pero_desactivado_despues_vuelve_a_preguntar():
    async def _exec(payload):
        return "x"

    approval_gate.register_executor("test_perm_revert", _exec)
    permission_service.set_permission("agent.execute", True)
    permission_service.set_permission("agent.execute", False)  # el usuario se arrepiente

    gate_id = await approval_gate.request_approval(
        kind="agent.execute", title="Ejecutar agente", action_type="test_perm_revert"
    )
    appr = approval_gate.get(gate_id)
    assert appr.status == "pending"


# ---------------------------------------------------------------------------
# Endpoints HTTP
# ---------------------------------------------------------------------------
def test_endpoint_get_permissions(client):
    r = client.get("/api/automation/permissions")
    assert r.status_code == 200
    body = r.json()
    assert len(body["permissions"]) == 9
    assert body["profile"] == "manual"


def test_endpoint_set_permission(client):
    r = client.post("/api/automation/permissions", json={"id": "workspace.write", "enabled": True})
    assert r.status_code == 200
    entry = next(p for p in r.json()["permissions"] if p["id"] == "workspace.write")
    assert entry["enabled"] is True


def test_endpoint_set_permission_desconocido_400(client):
    r = client.post("/api/automation/permissions", json={"id": "algo.raro", "enabled": True})
    assert r.status_code == 400


def test_endpoint_set_profile(client):
    r = client.post("/api/automation/permissions/profile", json={"profile": "full"})
    assert r.status_code == 200
    body = r.json()
    assert body["profile"] == "full"
    assert all(p["enabled"] == p["available"] for p in body["permissions"])


def test_endpoint_set_profile_desconocido_400(client):
    r = client.post("/api/automation/permissions/profile", json={"profile": "no_existe"})
    assert r.status_code == 400
