# tests/test_mel_decision.py — Rule Engine + circuit breakers + executor (MEL E1)
#
# El corazón de decisión: determinista, explicable, con fallback. Se usa un
# registry FAKE (monkeypatch) para no tocar red — se prueba la LÓGICA del MEL
# (elegir, saltar, clasificar, registrar), no un LLM real (eso es la verificación
# en vivo).
import pytest

from app.db.database import Base, SessionLocal, engine as db_engine
from app.mel import Capability, ExecutionRequest, ModelRef
from app.mel import decision, executor, registry
from app.mel.fallback import CircuitBreaker, FailureAction, breakers, classify_failure
from app.mel.models import MelExecution, MelPolicy


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    breakers.reset()
    yield
    breakers.reset()
    s = SessionLocal()
    try:
        s.query(MelExecution).delete()
        s.query(MelPolicy).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Rule Engine
# ---------------------------------------------------------------------------
def test_decide_determinista_y_elige_primero_viable():
    chain = [ModelRef("a", "1"), ModelRef("b", "2"), ModelRef("c", "3")]
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x")

    t1 = decision.decide(req, chain, lambda r: True)
    t2 = decision.decide(req, chain, lambda r: True)
    assert t1.chosen == "a:1" and t2.chosen == "a:1"   # determinista


def test_decide_salta_no_viables():
    chain = [ModelRef("a", "1"), ModelRef("b", "2"), ModelRef("c", "3")]
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x")
    # a y b no viables (breaker abierto) → elige c
    t = decision.decide(req, chain, lambda r: r.provider == "c")
    assert t.chosen == "c:3"
    assert [s[0] for s in t.skipped] == ["a:1", "b:2"]


def test_decide_forced_gana(monkeypatch):
    chain = [ModelRef("a", "1"), ModelRef("b", "2")]
    forced = ModelRef("z", "9")
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x")
    t = decision.decide(req, chain, lambda r: True, forced=forced, forced_origin="user_explicit")
    assert t.chosen == "z:9" and t.origin == "user_explicit"


def test_get_trace_recupera():
    chain = [ModelRef("a", "1")]
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x")
    t = decision.decide(req, chain, lambda r: True)
    assert decision.get_trace(t.id) is t
    assert decision.get_trace("no-existe") is None


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------
def test_breaker_abre_tras_3_fallos_transitorios():
    cb = CircuitBreaker()
    assert cb.is_closed("p")
    for _ in range(3):
        cb.record_failure("p", "transient")
    assert not cb.is_closed("p")           # abierto
    cb.record_success("p")
    assert cb.is_closed("p")               # cerrado tras éxito


def test_breaker_no_abre_por_auth_ni_quota():
    cb = CircuitBreaker()
    for _ in range(5):
        cb.record_failure("p", "auth")
        cb.record_failure("p", "quota")
    assert cb.is_closed("p")               # auth/quota no abren el breaker


# ---------------------------------------------------------------------------
# Clasificación de fallos
# ---------------------------------------------------------------------------
def test_classify_failure():
    assert classify_failure(detail="invalid request: prompt too long")[0] == FailureAction.STOP
    assert classify_failure(detail="connection timeout")[0] == FailureAction.NEXT
    assert classify_failure(detail="429 rate limit")[1] == "quota"
    assert classify_failure(detail="401 unauthorized")[1] == "auth"
    import httpx
    assert classify_failure(exc=httpx.ConnectError("boom"))[0] == FailureAction.NEXT


# ---------------------------------------------------------------------------
# Executor (con registry fake)
# ---------------------------------------------------------------------------
def _fake_registry(monkeypatch, avail, responder):
    monkeypatch.setattr(registry, "list_available", lambda: avail)
    async def _exec(ref, prompt, system_prompt=None):
        return responder(ref)
    monkeypatch.setattr(registry, "execute", _exec)


@pytest.mark.anyio
async def test_complete_ok_devuelve_served_by(monkeypatch):
    avail = [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)]
    _fake_registry(monkeypatch, avail, lambda ref: {"response": f"hola desde {ref.provider}", "tokens": 5})

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="hola"))
    assert res.ok and res.text.startswith("hola desde")
    assert res.served_by is not None
    assert res.decision_id is not None


@pytest.mark.anyio
async def test_complete_salta_al_siguiente_si_el_primero_falla(monkeypatch):
    avail = [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)]
    # SUMMARIZE: la cadena Economy pone el local (ollama) PRIMERO (barato,
    # score sobre umbral) — el primer candidato falla (transitorio) y el
    # segundo (anthropic) responde. Verifica el salto de cadena.
    def responder(ref):
        if ref.provider == "ollama":
            return {"error": True, "response": "connection timeout"}
        return {"response": "ok segundo", "tokens": 3}
    _fake_registry(monkeypatch, avail, responder)

    res = await executor.complete(ExecutionRequest(capability=Capability.SUMMARIZE, prompt="x"))
    assert res.ok and "segundo" in res.text
    assert res.served_by.fallbacks_used >= 1


@pytest.mark.anyio
async def test_complete_sin_proveedores(monkeypatch):
    monkeypatch.setattr(registry, "list_available", lambda: [])
    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))
    assert not res.ok and "proveedores" in res.error


@pytest.mark.anyio
async def test_model_override_no_disponible_es_error_explicito(monkeypatch):
    avail = [ModelRef("ollama", "llama3", True)]
    _fake_registry(monkeypatch, avail, lambda ref: {"response": "no debería llegar aquí"})
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x", model_override="gpt-5")
    res = await executor.complete(req)
    assert not res.ok and "ExplicitModelUnavailable" in res.error   # nunca sustituye en silencio


@pytest.mark.anyio
async def test_model_override_disponible_fuerza_ese_modelo(monkeypatch):
    avail = [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)]
    _fake_registry(monkeypatch, avail, lambda ref: {"response": f"servido por {ref.provider}", "tokens": 2})
    # pide explícitamente Claude aunque Economy pondría a ollama primero
    req = ExecutionRequest(capability=Capability.CHAT, prompt="x", model_override="claude")
    res = await executor.complete(req)
    assert res.ok and res.served_by.provider == "anthropic"


@pytest.mark.anyio
async def test_policy_override_offline_solo_local(monkeypatch):
    avail = [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)]
    _fake_registry(monkeypatch, avail, lambda ref: {"response": f"servido por {ref.provider}", "tokens": 1})
    req = ExecutionRequest(capability=Capability.SUMMARIZE, prompt="x", policy_override="offline")
    res = await executor.complete(req)
    assert res.ok and res.served_by.provider == "ollama"   # offline nunca sale de local


@pytest.mark.anyio
async def test_respuesta_vacia_reintenta_y_luego_falla(monkeypatch):
    avail = [ModelRef("ollama", "llama3", True)]
    calls = {"n": 0}
    def responder(ref):
        calls["n"] += 1
        return {"response": "   "}   # siempre vacío
    _fake_registry(monkeypatch, avail, responder)
    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))
    assert not res.ok
    assert calls["n"] == 2   # 1 intento + 1 reintento del mismo modelo (doc 19 §8.1)


# ---------------------------------------------------------------------------
# [#212] Observabilidad de fallos: modelo + error crudo en telemetría
#
# El caso real que motivó esto (2026-07-21): un modelo primario inválido
# (MiniMax-M3-highspeed, 400 real de la API) dejaba en telemetría solo
# `provider=None, model=None, detail={'fallback_reason': 'request_invalid'}` —
# diagnosticarlo exigió una sonda en vivo que un log con el texto crudo habría
# evitado.
# ---------------------------------------------------------------------------
def _capture_telemetry(monkeypatch):
    import app.telemetry as telemetry

    grabado: list[dict] = []

    def _record(stage, **kw):
        grabado.append({"stage": stage, **kw})

    monkeypatch.setattr(telemetry, "record", _record)
    return grabado


@pytest.mark.anyio
async def test_fallo_registra_el_modelo_que_fallo_y_el_error_crudo(monkeypatch):
    """Un fallo request_invalid del primario (el caso MiniMax-M3-highspeed) debe
    dejar en telemetría QUIÉN falló y el texto REAL del proveedor — no
    provider=None y una razón clasificada a secas."""
    avail = [ModelRef("ollama", "llama3", True)]

    def responder(ref):
        return {"error": True, "response": "invalid request: 400 Bad Request (invalid model)"}

    _fake_registry(monkeypatch, avail, responder)
    grabado = _capture_telemetry(monkeypatch)

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))

    assert not res.ok
    fallos = [g for g in grabado if g["stage"] == "llm_call" and g["ok"] is False]
    assert fallos, "el fallo no dejó ningún evento llm_call en telemetría"
    ev = fallos[-1]
    assert ev["provider"] == "ollama" and ev["model"] == "llama3", \
        "el evento de fallo debe identificar al candidato que falló, no None:None"
    assert "400 Bad Request" in ev["detail"]["error"], \
        "el detail debe llevar el texto CRUDO del proveedor, no solo la razón clasificada"
    assert ev["detail"]["fallback_reason"] == "request_invalid"


@pytest.mark.anyio
async def test_fallo_multi_salto_registra_los_candidatos_probados(monkeypatch):
    """Cuando la cadena rota por fallos transitorios, `detail.tried` lista los
    candidatos probados — la diferencia entre 'falló el chat' y 'fallaron
    ollama Y anthropic, en este orden'."""
    avail = [ModelRef("ollama", "llama3", True), ModelRef("anthropic", "claude-opus-4-8", False)]

    def responder(ref):
        return {"error": True, "response": "connection timeout"}   # transitorio → rota

    _fake_registry(monkeypatch, avail, responder)
    grabado = _capture_telemetry(monkeypatch)

    res = await executor.complete(ExecutionRequest(capability=Capability.SUMMARIZE, prompt="x"))

    assert not res.ok
    ev = [g for g in grabado if g["stage"] == "llm_call" and g["ok"] is False][-1]
    assert ev["provider"] is not None, "el último candidato fallido debe quedar identificado"
    assert len(ev["detail"]["tried"]) == 2, f"tried debería listar 2 candidatos: {ev['detail']}"
    assert "timeout" in ev["detail"]["error"]


@pytest.mark.anyio
async def test_exito_no_arrastra_error_ni_tried(monkeypatch):
    """No-regresión: un éxito limpio registra igual que antes (sin claves nuevas
    de fallo colándose en el detail)."""
    avail = [ModelRef("ollama", "llama3", True)]
    _fake_registry(monkeypatch, avail, lambda ref: {"response": "hola", "tokens": 2})
    grabado = _capture_telemetry(monkeypatch)

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))

    assert res.ok
    ev = [g for g in grabado if g["stage"] == "llm_call"][-1]
    assert ev["ok"] is True
    assert ev["detail"] is None, f"un éxito a la primera no debe llevar detail: {ev['detail']}"
