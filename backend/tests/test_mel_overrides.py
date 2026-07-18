# tests/test_mel_overrides.py — Override explícito del usuario (MEL E2b, doc 19 §7b)
#
# Cubre: la personalización de políticas (set_primary/restore/custom, Parte A del
# usuario) + la precedencia real override>proyecto>política del Rule Engine +
# los pines de proyecto (mel_overrides). Registry FAKE para no tocar red.
import pytest

from app.db.database import Base, SessionLocal, engine as db_engine
from app.mel import Capability, ExecutionRequest, ModelRef
from app.mel import executor, registry
from app.mel.fallback import breakers
from app.mel.models import MelExecution, MelOverride, MelPolicy
from app.mel.policies import policy_store


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    breakers.reset()
    _wipe()
    yield
    breakers.reset()
    _wipe()


def _wipe():
    s = SessionLocal()
    try:
        s.query(MelExecution).delete()
        s.query(MelPolicy).delete()
        s.query(MelOverride).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def _fake_registry(monkeypatch, avail, responder):
    monkeypatch.setattr(registry, "list_available", lambda: avail)
    async def _exec(ref, prompt, system_prompt=None):
        return responder(ref)
    monkeypatch.setattr(registry, "execute", _exec)


AVAIL = [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)]


# ---------------------------------------------------------------------------
# Parte A — personalización de políticas
# ---------------------------------------------------------------------------
def test_ensure_compiled_crea_custom():
    policy_store.ensure_compiled(AVAIL)
    names = {p["name"] for p in policy_store.list_policies()}
    assert names == {"economy", "quality", "offline", "custom"}


def test_set_primary_pone_el_modelo_primero_con_respaldos():
    policy_store.ensure_compiled(AVAIL)
    ok = policy_store.set_primary("custom", "chat", "ollama:llama3", AVAIL)
    assert ok
    custom = next(p for p in policy_store.list_policies() if p["name"] == "custom")
    assert custom["compiled"]["chat"][0] == "ollama:llama3"   # primario elegido
    assert "anthropic:claude-opus-4-8" in custom["compiled"]["chat"]  # respaldo conservado
    assert custom["pristine"] is False   # marcada como editada


def test_set_primary_auto_recompila_esa_capacidad():
    policy_store.ensure_compiled(AVAIL)
    policy_store.set_primary("quality", "chat", "ollama:llama3", AVAIL)
    # None = automático → vuelve a poner el mejor por catálogo (anthropic) primero
    policy_store.set_primary("quality", "chat", None, AVAIL)
    q = next(p for p in policy_store.list_policies() if p["name"] == "quality")
    assert q["compiled"]["chat"][0] == "anthropic:claude-opus-4-8"


def test_set_primary_modelo_inexistente_devuelve_false():
    policy_store.ensure_compiled(AVAIL)
    assert policy_store.set_primary("custom", "chat", "foo:bar", AVAIL) is False


def test_restore_vuelve_a_pristine():
    policy_store.ensure_compiled(AVAIL)
    policy_store.set_primary("economy", "code", "ollama:llama3", AVAIL)
    assert policy_store.restore("economy", AVAIL) is True
    eco = next(p for p in policy_store.list_policies() if p["name"] == "economy")
    assert eco["pristine"] is True


# ---------------------------------------------------------------------------
# Precedencia — override de tarea > pin de proyecto > política
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_model_override_de_tarea_gana(monkeypatch):
    _fake_registry(monkeypatch, AVAIL, lambda ref: {"response": f"por {ref.provider}", "tokens": 1})
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x", model_override="anthropic:claude-opus-4-8")
    res = await executor.complete(req)
    assert res.ok and res.served_by.provider == "anthropic"


@pytest.mark.anyio
async def test_pin_de_proyecto_gana_sobre_politica(monkeypatch):
    from app.mel import overrides
    _fake_registry(monkeypatch, AVAIL, lambda ref: {"response": f"por {ref.provider}", "tokens": 1})
    # Economy pondría a ollama primero para classify; el pin fuerza anthropic.
    overrides.set_project_override(42, "anthropic:claude-opus-4-8")
    req = ExecutionRequest(capability=Capability.CLASSIFY, prompt="x", context_tags={"project_id": 42})
    res = await executor.complete(req)
    assert res.ok and res.served_by.provider == "anthropic"


@pytest.mark.anyio
async def test_override_de_tarea_gana_sobre_pin_de_proyecto(monkeypatch):
    from app.mel import overrides
    _fake_registry(monkeypatch, AVAIL, lambda ref: {"response": f"por {ref.provider}", "tokens": 1})
    overrides.set_project_override(7, "anthropic:claude-opus-4-8")
    # el usuario pide ollama AHORA para esta tarea → gana sobre el pin del proyecto
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x",
                           context_tags={"project_id": 7}, model_override="ollama:llama3")
    res = await executor.complete(req)
    assert res.ok and res.served_by.provider == "ollama"


@pytest.mark.anyio
async def test_pin_no_disponible_degrada_a_politica(monkeypatch):
    from app.mel import overrides
    _fake_registry(monkeypatch, AVAIL, lambda ref: {"response": f"por {ref.provider}", "tokens": 1})
    # el pin apunta a un modelo que NO está en available → degradación suave
    overrides.set_project_override(9, "deepseek:deepseek-v4-flash")
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x", context_tags={"project_id": 9})
    res = await executor.complete(req)
    assert res.ok   # no falla: usa la política en vez de romper (pin persistente)


@pytest.mark.anyio
async def test_override_de_tarea_no_disponible_falla_duro(monkeypatch):
    _fake_registry(monkeypatch, AVAIL, lambda ref: {"response": "no debería"})
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x", model_override="gpt-5")
    res = await executor.complete(req)
    assert not res.ok and "ExplicitModelUnavailable" in res.error  # nunca sustituye en silencio


# ---------------------------------------------------------------------------
# CRUD de pines de proyecto
# ---------------------------------------------------------------------------
def test_overrides_crud():
    from app.mel import overrides
    assert overrides.set_project_override(1, "ollama:llama3") is True
    # re-pinear reemplaza (idempotente por project_id+capability)
    overrides.set_project_override(1, "anthropic:claude-opus-4-8")
    lst = overrides.overrides_for(1)
    assert len(lst) == 1 and lst[0]["model_id"] == "anthropic:claude-opus-4-8"
    assert overrides.override_model_for(1, "chat") == "anthropic:claude-opus-4-8"
    # borrar
    oid = lst[0]["id"]
    assert overrides.clear_override(oid) is True
    assert overrides.overrides_for(1) == []
    assert overrides.override_model_for(1, "chat") is None


def test_pin_especifico_de_capacidad_gana_sobre_global():
    from app.mel import overrides
    overrides.set_project_override(3, "ollama:llama3")                       # global
    overrides.set_project_override(3, "anthropic:claude-opus-4-8", "code")   # solo code
    assert overrides.override_model_for(3, "chat") == "ollama:llama3"
    assert overrides.override_model_for(3, "code") == "anthropic:claude-opus-4-8"
