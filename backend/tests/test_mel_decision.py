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
    # [#213] La familia request ya NO devuelve STOP: classify es stateless y no
    # puede saber si rotar ayudaría — el corte con evidencia lo aplica el
    # executor (2 proveedores distintos). "prompt too long" es límite POR
    # MODELO: otro con ventana mayor puede servir.
    assert classify_failure(detail="invalid request: prompt too long") == (FailureAction.NEXT, "context_length")
    assert classify_failure(detail="connection timeout")[0] == FailureAction.NEXT
    assert classify_failure(detail="429 rate limit")[1] == "quota"
    assert classify_failure(detail="401 unauthorized")[1] == "auth"
    import httpx
    assert classify_failure(exc=httpx.ConnectError("boom"))[0] == FailureAction.NEXT


def test_classify_failure_subclasifica_la_familia_request():
    """[#213] El cajón único "request_invalid → STOP" era demasiado ancho: el
    caso real de producción (MiniMax-M3-highspeed, 400 "invalid model") era un
    fallo de ESE modelo y el STOP dejó al usuario sin respuesta con fallbacks
    sanos. Ahora se sub-clasifica y todo es NEXT."""
    from app.mel.fallback import REQUEST_FAULT_REASONS

    # bad_model: modelo inexistente EN ESE proveedor → rotar ayuda seguro.
    assert classify_failure(detail="400 Bad Request (invalid model)") == (FailureAction.NEXT, "bad_model")
    assert classify_failure(detail="model not found: gpt-9")[1] == "bad_model"
    # bad_model NO forma parte de la familia que corta la cadena.
    assert "bad_model" not in REQUEST_FAULT_REASONS

    # context_length: límite por-modelo.
    assert classify_failure(detail="context_length_exceeded")[1] == "context_length"
    assert "context_length" in REQUEST_FAULT_REASONS

    # content_policy: la moderación varía por proveedor (un local no modera).
    assert classify_failure(detail="flagged by content policy")[1] == "content_policy"
    assert "content_policy" in REQUEST_FAULT_REASONS

    # genérico: 4xx de validación sin señal más específica.
    assert classify_failure(detail="invalid request")[1] == "request_invalid"
    assert "request_invalid" in REQUEST_FAULT_REASONS

    # nada de la familia request devuelve STOP ya.
    for d in ("invalid model x", "context length exceeded", "content policy", "400 bad request"):
        assert classify_failure(detail=d)[0] == FailureAction.NEXT


def test_classify_failure_400_dentro_de_otro_numero_no_es_request_invalid():
    """[#213] La marca "400" iba PRIMERO y se colaba dentro de otros números:
    "timeout after 2400ms" se clasificaba como request_invalid (y con el diseño
    viejo, cortaba la cadena). Ahora el cajón genérico va el ÚLTIMO."""
    assert classify_failure(detail="timeout after 2400ms") == (FailureAction.NEXT, "transient")


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
    # [#213] "invalid model" ahora se sub-clasifica como bad_model (más preciso
    # que el genérico request_invalid de antes) — la telemetría gana señal.
    assert ev["detail"]["fallback_reason"] == "bad_model"


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


@pytest.mark.anyio
async def test_override_a_modelo_no_capaz_falla_claro_salvo_fitness_exempt(monkeypatch):
    """[2026-07-22] Un override explicito a un modelo NO CAPAZ de la tarea
    devuelve error claro (nunca se sustituye en silencio). La UNICA excepcion
    es fitness_exempt (el banco de medicion): sin ella, un modelo excluido no
    podria re-medirse jamas."""
    from app.mel import policies as _pol_mod
    import importlib
    pol = importlib.import_module("app.mel.policies")

    avail = [ModelRef("ollama", "llama3", True)]
    _fake_registry(monkeypatch, avail, lambda ref: {"response": "hola", "tokens": 1})
    monkeypatch.setattr(pol, "is_capable", lambda r, cap: False)

    req = ExecutionRequest(capability=Capability.CHAT, prompt="x",
                          model_override="ollama:llama3")
    res = await executor.complete(req)
    assert not res.ok and "ExplicitModelUnfit" in res.error

    req2 = ExecutionRequest(capability=Capability.CHAT, prompt="x",
                           model_override="ollama:llama3", fitness_exempt=True)
    res2 = await executor.complete(req2)
    assert res2.ok, "el banco (fitness_exempt) debe poder medir al excluido"


# ---------------------------------------------------------------------------
# [#213] STOP-vs-NEXT refinado: el corte de cadena exige EVIDENCIA
# (≥2 proveedores DISTINTOS con fallo de la familia request), nunca un solo 4xx.
# ---------------------------------------------------------------------------
def _fixed_chain(monkeypatch, chain):
    """Controla la composición exacta de la cadena (sin depender de cómo
    compile la política activa sobre `available`)."""
    monkeypatch.setattr(executor, "_chain_for", lambda req, av: chain)


@pytest.mark.anyio
async def test_bad_model_del_primario_rota_y_el_fallback_responde(monkeypatch):
    """EL caso de producción (2026-07-21): MiniMax-M3-highspeed devolvía 400
    "invalid model" — un fallo de ESE modelo — y el STOP viejo cortaba la
    cadena entera: fallo total para el usuario con fallbacks sanos disponibles.
    Ahora bad_model rota y el secundario sirve la respuesta."""
    chain = [ModelRef("minimax", "MiniMax-M3-highspeed", False),
             ModelRef("ollama", "llama3", True)]

    def responder(ref):
        if ref.provider == "minimax":
            return {"error": True, "response": "invalid request: 400 Bad Request (invalid model)"}
        return {"response": "servido por el fallback", "tokens": 3}

    _fake_registry(monkeypatch, chain, responder)
    _fixed_chain(monkeypatch, chain)

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))
    assert res.ok and "fallback" in res.text
    assert res.served_by.provider == "ollama"
    assert res.served_by.fallbacks_used == 1


@pytest.mark.anyio
async def test_dos_proveedores_distintos_con_fallo_de_request_cortan_la_cadena(monkeypatch):
    """Dos APIs INDEPENDIENTES rechazando el mismo request sí es evidencia de
    que el problema es el request: el tercer candidato no se quema."""
    chain = [ModelRef("ollama", "llama3", True),
             ModelRef("anthropic", "claude-sonnet-5", False),
             ModelRef("openai", "gpt-5.1", False)]
    llamados: list[str] = []

    def responder(ref):
        llamados.append(ref.provider)
        return {"error": True, "response": "invalid request"}

    _fake_registry(monkeypatch, chain, responder)
    _fixed_chain(monkeypatch, chain)

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))
    assert not res.ok
    assert llamados == ["ollama", "anthropic"], \
        f"con 2 proveedores coincidiendo, el 3.º no debe intentarse: {llamados}"


@pytest.mark.anyio
async def test_fallo_de_request_repetido_del_mismo_proveedor_no_es_evidencia(monkeypatch):
    """Dos modelos del MISMO proveedor rechazando puede ser un bug del formato
    de payload de ESE adapter (R6.5a: cada proveedor tiene el suyo) — no prueba
    nada sobre el request. El tercero (proveedor distinto) sí se intenta."""
    chain = [ModelRef("minimax", "MiniMax-M2.7", False),
             ModelRef("minimax", "MiniMax-M3", False),
             ModelRef("ollama", "llama3", True)]

    def responder(ref):
        if ref.provider == "minimax":
            return {"error": True, "response": "invalid request"}
        return {"response": "el local responde", "tokens": 2}

    _fake_registry(monkeypatch, chain, responder)
    _fixed_chain(monkeypatch, chain)

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))
    assert res.ok and "local" in res.text


@pytest.mark.anyio
async def test_bad_model_nunca_corta_la_cadena(monkeypatch):
    """bad_model es config POR MODELO (dos entradas mal escritas en la cadena
    no dicen nada de la tercera) — no cuenta para el corte con evidencia."""
    chain = [ModelRef("minimax", "modelo-que-no-existe", False),
             ModelRef("anthropic", "otro-inexistente", False),
             ModelRef("ollama", "llama3", True)]

    def responder(ref):
        if ref.provider != "ollama":
            return {"error": True, "response": f"model not found: {ref.model}"}
        return {"response": "el tercero responde", "tokens": 2}

    _fake_registry(monkeypatch, chain, responder)
    _fixed_chain(monkeypatch, chain)

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))
    assert res.ok and "tercero" in res.text


@pytest.mark.anyio
async def test_context_length_rota_a_un_modelo_con_ventana_mayor(monkeypatch):
    """El límite de contexto es POR MODELO: un prompt que no cabe en uno puede
    caber en otro con ventana mayor. Con el diseño viejo ("context length" ∈
    request fault → STOP), esto era fallo total."""
    chain = [ModelRef("ollama", "llama3", True),
             ModelRef("anthropic", "claude-sonnet-5", False)]

    def responder(ref):
        if ref.provider == "ollama":
            return {"error": True, "response": "context_length_exceeded: input is too long"}
        return {"response": "cabe en la ventana grande", "tokens": 5}

    _fake_registry(monkeypatch, chain, responder)
    _fixed_chain(monkeypatch, chain)

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="x"))
    assert res.ok and "ventana grande" in res.text


def test_familia_request_no_abre_el_breaker():
    """Un 4xx de validación no dice nada de la SALUD del proveedor: ni las
    razones nuevas (#213) ni la vieja abren el breaker."""
    cb = CircuitBreaker()
    for _ in range(5):
        for reason in ("bad_model", "context_length", "content_policy", "request_invalid"):
            cb.record_failure("p", reason)
    assert cb.is_closed("p")
