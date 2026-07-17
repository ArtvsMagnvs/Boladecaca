# tests/test_mel_research.py — Catálogo Auto-Investigado (MEL E1b, doc 19 §5.4)
#
# Blinda: la investigación se dispara al configurar un modelo, persiste un
# informe por capacidad, un JSON inválido no rompe nada, un informe con
# confianza "bajo" no desplaza el catálogo, el refresco periódico re-investiga
# TODOS los modelos configurados, y el evento real (`provider.model_configured`)
# llega desde el endpoint sin necesitar red (ai_manager/mel.complete fake).
import json

import pytest

from app.db.database import Base, SessionLocal, engine as db_engine
from app.mel import Capability, ExecutionResult, ModelRef, ServedBy, Usage
from app.mel import research
from app.mel.models import MelCapabilityReport


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(MelCapabilityReport).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


_VALID_JSON = json.dumps({
    "capabilities": {
        "chat": {"score": 85, "rationale": "conversa bien", "confidence": "alto"},
        "code": {"score": 60, "rationale": "flojo en código", "confidence": "medio"},
        "reason": {"score": 40, "rationale": "no lo conozco bien", "confidence": "bajo"},
    }
})


def _fake_complete(monkeypatch, text, *, served_by=("anthropic", "claude-opus-4-8"), ok=True):
    async def _complete(req):
        if not ok:
            return ExecutionResult(text="", ok=False, error="boom")
        return ExecutionResult(
            text=text, ok=True,
            served_by=ServedBy(provider=served_by[0], model=served_by[1]),
            usage=Usage(tokens=10),
        )
    import app.mel.executor as executor_mod
    monkeypatch.setattr(executor_mod, "complete", _complete)


def _fake_available(monkeypatch, refs):
    from app.mel import registry
    monkeypatch.setattr(registry, "list_available", lambda: refs)


# ---------------------------------------------------------------------------
# investigate() — el flujo principal
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_investigate_persiste_un_informe_por_capacidad(monkeypatch):
    _fake_available(monkeypatch, [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)])
    _fake_complete(monkeypatch, _VALID_JSON)

    ok = await research.investigate("ollama", "llama3")
    assert ok is True

    s = SessionLocal()
    try:
        rows = s.query(MelCapabilityReport).filter(MelCapabilityReport.provider == "ollama").all()
        assert len(rows) == 3
        by_cap = {r.capability: r for r in rows}
        assert by_cap["chat"].score == 85 and by_cap["chat"].confidence == "alto"
        assert by_cap["reason"].confidence == "bajo"
    finally:
        s.close()


@pytest.mark.anyio
async def test_investigate_json_invalido_no_rompe(monkeypatch):
    _fake_available(monkeypatch, [ModelRef("ollama", "llama3", True)])
    _fake_complete(monkeypatch, "esto no es JSON en absoluto")

    ok = await research.investigate("ollama", "llama3")
    assert ok is False

    s = SessionLocal()
    try:
        assert s.query(MelCapabilityReport).count() == 0
    finally:
        s.close()


@pytest.mark.anyio
async def test_investigate_llm_falla_no_rompe(monkeypatch):
    _fake_available(monkeypatch, [ModelRef("ollama", "llama3", True)])
    _fake_complete(monkeypatch, "", ok=False)

    ok = await research.investigate("ollama", "llama3")
    assert ok is False


@pytest.mark.anyio
async def test_investigate_no_reinvestiga_si_reciente(monkeypatch):
    _fake_available(monkeypatch, [ModelRef("ollama", "llama3", True)])
    calls = {"n": 0}
    import app.mel.executor as executor_mod

    async def _complete(req):
        calls["n"] += 1
        return ExecutionResult(text=_VALID_JSON, ok=True,
                               served_by=ServedBy(provider="a", model="b"), usage=Usage())
    monkeypatch.setattr(executor_mod, "complete", _complete)

    assert await research.investigate("ollama", "llama3") is True
    assert calls["n"] == 1
    # segunda vez, sin force: ya hay informe reciente -> no reinvestiga
    assert await research.investigate("ollama", "llama3") is False
    assert calls["n"] == 1


@pytest.mark.anyio
async def test_investigate_excluye_el_propio_modelo_si_hay_alternativa(monkeypatch):
    avail = [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)]
    _fake_available(monkeypatch, avail)

    seen_exclude = {}
    import app.mel.executor as executor_mod

    async def _complete(req):
        seen_exclude["exclude"] = req.exclude
        return ExecutionResult(text=_VALID_JSON, ok=True,
                               served_by=ServedBy(provider="anthropic", model="claude-opus-4-8"), usage=Usage())
    monkeypatch.setattr(executor_mod, "complete", _complete)

    await research.investigate("ollama", "llama3")
    assert seen_exclude["exclude"] == ("ollama:llama3",)


@pytest.mark.anyio
async def test_investigate_no_excluye_si_es_el_unico_disponible(monkeypatch):
    _fake_available(monkeypatch, [ModelRef("ollama", "llama3", True)])
    seen_exclude = {}
    import app.mel.executor as executor_mod

    async def _complete(req):
        seen_exclude["exclude"] = req.exclude
        return ExecutionResult(text=_VALID_JSON, ok=True,
                               served_by=ServedBy(provider="ollama", model="llama3"), usage=Usage())
    monkeypatch.setattr(executor_mod, "complete", _complete)

    await research.investigate("ollama", "llama3")
    assert seen_exclude["exclude"] == ()


# ---------------------------------------------------------------------------
# effective_score — el desplazamiento sobre el catálogo curado
# ---------------------------------------------------------------------------
def test_effective_score_sin_informe_usa_catalogo():
    ref = ModelRef("anthropic", "claude-opus-4-8", False)
    from app.mel.catalog import score_of as catalog_score
    assert research.effective_score(ref, Capability.CHAT) == catalog_score(ref, Capability.CHAT)


def test_effective_score_confianza_bajo_no_desplaza():
    ref = ModelRef("ollama", "modelo-raro", True)
    from app.mel.catalog import score_of as catalog_score
    research._persist("ollama", "modelo-raro", {
        "chat": {"score": 99, "rationale": "x", "confidence": "bajo"},
    }, "anthropic:claude-opus-4-8")
    assert research.effective_score(ref, Capability.CHAT) == catalog_score(ref, Capability.CHAT)


def test_effective_score_confianza_alta_desplaza():
    ref = ModelRef("ollama", "modelo-raro", True)
    from app.mel.catalog import score_of as catalog_score
    base = catalog_score(ref, Capability.CHAT)
    research._persist("ollama", "modelo-raro", {
        "chat": {"score": 10, "rationale": "malo de verdad", "confidence": "alto"},
    }, "anthropic:claude-opus-4-8")
    effective = research.effective_score(ref, Capability.CHAT)
    assert effective != base
    assert effective == round(base * 0.5 + 10 * 0.5)


# ---------------------------------------------------------------------------
# El informe legible (GET /api/mel/capability-report)
# ---------------------------------------------------------------------------
def test_report_summary_agrupa_por_modelo():
    research._persist("ollama", "llama3", {
        "chat": {"score": 70, "rationale": "ok", "confidence": "medio"},
        "code": {"score": 50, "rationale": "regular", "confidence": "medio"},
    }, "anthropic:claude-opus-4-8")

    summary = research.report_summary()
    assert len(summary) == 1
    entry = summary[0]
    assert entry["provider"] == "ollama" and entry["model"] == "llama3"
    assert set(entry["capabilities"].keys()) == {"chat", "code"}


# ---------------------------------------------------------------------------
# Evento provider.model_configured
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_evento_dispara_la_investigacion(monkeypatch):
    _fake_available(monkeypatch, [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)])
    _fake_complete(monkeypatch, _VALID_JSON)
    research.register()

    from app.core.events import emit
    import asyncio
    emit("provider.model_configured", source="ai", payload={"provider": "anthropic", "model": "claude-opus-4-8"})
    await asyncio.sleep(0.05)

    s = SessionLocal()
    try:
        assert s.query(MelCapabilityReport).filter(MelCapabilityReport.provider == "anthropic").count() == 3
    finally:
        s.close()


@pytest.mark.anyio
async def test_evento_sin_payload_no_rompe(monkeypatch):
    research.register()
    from app.core.events import emit
    import asyncio
    emit("provider.model_configured", source="ai", payload={})
    await asyncio.sleep(0.05)  # no debe lanzar ni bloquear


# ---------------------------------------------------------------------------
# refresh_all — el job periódico
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_refresh_all_reinvestiga_todos_los_configurados(monkeypatch):
    avail = [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)]
    _fake_available(monkeypatch, avail)
    calls = []
    import app.mel.executor as executor_mod

    async def _complete(req):
        calls.append(req.prompt)
        return ExecutionResult(text=_VALID_JSON, ok=True,
                               served_by=ServedBy(provider="a", model="b"), usage=Usage())
    monkeypatch.setattr(executor_mod, "complete", _complete)

    # ya hay un informe "reciente" de ollama; refresh_all con force=True lo repite igual
    await research.investigate("ollama", "llama3")
    n = await research.refresh_all()
    assert n == 2   # los 2 modelos configurados, force ignora la frescura
    assert len(calls) == 3  # 1 (investigate inicial) + 2 (refresh_all)
