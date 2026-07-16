# tests/test_tie_planner.py — Planner + enricher (V1.0 T2, doc 21 §3·T2)
#
# Blinda: el planner emite un TaskGraph válido de 2-3 nodos con modelo potente
# (fake), reintenta 1 vez con feedback ante grafo inválido y degrada a None si
# vuelve a fallar; registra el plan en la Decision API; y el enricher respeta el
# presupuesto de latencia duro + la caché. Toda la parte LLM va con router.complete
# fake (sin credenciales en CI).
import asyncio

import pytest

from app.tie import planner
from app.tie.contracts import Intent, IntentType
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine


@pytest.fixture(autouse=True)
def _tables():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def _fake_router(monkeypatch, responses):
    """Sustituye router.complete por una secuencia de respuestas (str = JSON del
    modelo). Devuelve el contador de llamadas."""
    calls = {"i": 0}

    async def _complete(prompt, *, system_prompt=None, capability="chat"):
        i = calls["i"]
        calls["i"] += 1
        r = responses[min(i, len(responses) - 1)]
        return {"response": r, "model": "fake-smart", "tokens": 30}

    import app.tie.router as router
    monkeypatch.setattr(router, "complete", _complete)
    return calls


def _spy_decision(monkeypatch):
    """Espía store_decision (evita tocar ChromaDB en el test del planner)."""
    seen = {}

    class _Dec:
        id = "dec-test-1"

    async def _store(*, title, body="", reason="", impact="med", mission_id=None, **kw):
        seen["title"] = title
        seen["mission_id"] = mission_id
        return _Dec()

    import app.services.decision_service as ds
    monkeypatch.setattr(ds, "store_decision", _store)
    return seen


_VALID_GRAPH = """{"nodes":[
  {"id":"n1","goal":"buscar la informacion","depends_on":[],"tools":[]},
  {"id":"n2","goal":"redactar el resumen","depends_on":["n1"],"tools":[]}
]}"""

_CYCLIC_GRAPH = """{"nodes":[
  {"id":"a","goal":"paso a","depends_on":["b"]},
  {"id":"b","goal":"paso b","depends_on":["a"]}
]}"""


@pytest.mark.anyio
async def test_plan_valido_2_3_nodos(monkeypatch):
    _fake_router(monkeypatch, [_VALID_GRAPH])
    _spy_decision(monkeypatch)
    it = Intent(type=IntentType.CREATE, goal="haz un resumen", confidence=0.9, requires_planning=True)

    g = await planner.plan("haz un resumen de mi semana", it, context="")
    assert g is not None
    assert set(g.nodes) == {"n1", "n2"}
    assert g.nodes["n2"].depends_on == ["n1"]


@pytest.mark.anyio
async def test_plan_registra_decision(monkeypatch):
    _fake_router(monkeypatch, [_VALID_GRAPH])
    seen = _spy_decision(monkeypatch)
    it = Intent(type=IntentType.CREATE, goal="x", confidence=0.9, requires_planning=True)

    await planner.plan("objetivo concreto", it, mission_id="mis-123")
    assert seen.get("mission_id") == "mis-123"
    assert "objetivo concreto" in seen.get("title", "")


@pytest.mark.anyio
async def test_plan_reintenta_ante_grafo_invalido(monkeypatch):
    # 1º cíclico (inválido) → reintento → 2º válido
    calls = _fake_router(monkeypatch, [_CYCLIC_GRAPH, _VALID_GRAPH])
    _spy_decision(monkeypatch)
    it = Intent(type=IntentType.CREATE, goal="x", confidence=0.9, requires_planning=True)

    g = await planner.plan("algo", it)
    assert g is not None
    assert calls["i"] == 2  # hubo reintento


@pytest.mark.anyio
async def test_plan_degrada_a_none_si_falla_dos_veces(monkeypatch):
    calls = _fake_router(monkeypatch, [_CYCLIC_GRAPH, _CYCLIC_GRAPH])
    _spy_decision(monkeypatch)
    it = Intent(type=IntentType.CREATE, goal="x", confidence=0.9, requires_planning=True)

    g = await planner.plan("algo", it)
    assert g is None
    assert calls["i"] == 2  # reintentó una vez y se rindió


@pytest.mark.anyio
async def test_plan_json_basura_degrada(monkeypatch):
    _fake_router(monkeypatch, ["no soy json", "sigo sin serlo"])
    _spy_decision(monkeypatch)
    it = Intent(type=IntentType.QUERY, goal="x", confidence=0.9, requires_planning=True)
    g = await planner.plan("algo", it)
    assert g is None


@pytest.mark.anyio
async def test_plan_escribe_en_la_traza(monkeypatch):
    _fake_router(monkeypatch, [_VALID_GRAPH])
    _spy_decision(monkeypatch)
    from app.tie import tracer
    from app.tie.missions import new_mission

    m = new_mission("objetivo", source="user", channel="electron")
    trace_id = tracer.record_start(m, channel="electron")
    it = Intent(type=IntentType.CREATE, goal="x", confidence=0.9, requires_planning=True)

    g = await planner.plan("algo", it, mission_id=m.id, trace_id=trace_id)
    assert g is not None

    s = SessionLocal()
    try:
        row = s.get(OrchestratorTrace, trace_id)
        assert row.plan is not None
        assert set(row.plan["nodes"]) == {"n1", "n2"}
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Enricher — presupuesto de latencia + caché
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_enricher_presupuesto_agotado_devuelve_vacio(monkeypatch):
    from app.tie import enricher
    enricher.clear_cache()

    async def _slow_context(query, max_tokens=1500, memory_types=None):
        await asyncio.sleep(0.5)  # excede el presupuesto
        return "contexto que llega tarde"

    import app.memory as mem
    monkeypatch.setattr(mem.memory_router, "context", _slow_context)

    out = await enricher.enrich("algo", budget_ms=50)
    assert out == ""  # se agotó el presupuesto → contexto vacío, sin colgar


@pytest.mark.anyio
async def test_enricher_devuelve_contexto_y_cachea(monkeypatch):
    from app.tie import enricher
    enricher.clear_cache()
    calls = {"i": 0}

    async def _ctx(query, max_tokens=1500, memory_types=None):
        calls["i"] += 1
        return "contexto real del MOS"

    import app.memory as mem
    monkeypatch.setattr(mem.memory_router, "context", _ctx)

    a = await enricher.enrich("misma query", budget_ms=1000)
    b = await enricher.enrich("misma query", budget_ms=1000)
    assert a == "contexto real del MOS" and b == a
    assert calls["i"] == 1  # la 2ª vino de caché


@pytest.mark.anyio
async def test_enricher_error_del_mos_no_rompe(monkeypatch):
    from app.tie import enricher
    enricher.clear_cache()

    async def _boom(query, max_tokens=1500, memory_types=None):
        raise RuntimeError("MOS caído")

    import app.memory as mem
    monkeypatch.setattr(mem.memory_router, "context", _boom)

    out = await enricher.enrich("algo", budget_ms=1000)
    assert out == ""  # degrada a vacío, nunca propaga
