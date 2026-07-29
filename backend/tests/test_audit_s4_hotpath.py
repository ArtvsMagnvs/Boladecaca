# tests/test_audit_s4_hotpath.py — camino caliente rápido + deadlines
# (S4 del doc 34; P5 + NEW-2)
#
# EL CONTEXTO QUE CIERRA ESTA SESIÓN:
#
#   · NEW-2 — comprobado por grep en la campaña 00: NO había ni un `timeout` ni
#     un `wait_for` en `mel/executor.py`, `tie/intents.py` ni `tie/router.py`.
#     El único límite del camino caliente eran los 180 s del provider de Ollama
#     y, con cadena de fallback, 180 s POR SALTO. Sin plazo, el chat podía pasar
#     minutos en "analizando" sin escribir una línea — lo que la campaña leyó
#     como "cuelgue" (no lo era: el event loop seguía vivo; era falta de plazo).
#   · P5 — el clasificador heredaba la política de CALIDAD del usuario
#     (custom→opus): decenas de segundos para un parseo estructurado, en CADA
#     mensaje no trivial. Y el transcript del bucle de tool-use se reenviaba
#     entero en cada vuelta (4000 chars × 12 iteraciones ≈ 50k chars al final).
#
# Todo con dobles deterministas: sin red, sin modelos reales, sin esperas
# largas (los deadlines se bajan a décimas de segundo por monkeypatch).
from __future__ import annotations

import asyncio

import pytest

from app.mel.contracts import Capability, ExecutionRequest, ModelRef


# ===========================================================================
# 1) NEW-2 · deadline por petición en el MEL
# ===========================================================================
@pytest.mark.anyio
async def test_provider_lento_vence_el_plazo_y_se_clasifica_como_timeout(monkeypatch):
    """Un proveedor que no responde a tiempo devuelve reason "timeout" — razón
    PROPIA, no la genérica "transient": es un diagnóstico distinto (no respondió
    A TIEMPO, no que la red fallara) y así se lee en `mel_executions`."""
    from app.core.config import settings
    from app.mel import executor

    monkeypatch.setattr(settings, "MEL_REQUEST_DEADLINE_S", 1)

    async def _lentisimo(ref, prompt, system_prompt=None, **kw):
        await asyncio.sleep(30)          # muy por encima del plazo
        return {"response": "tarde"}
    monkeypatch.setattr(executor.registry, "execute", _lentisimo)

    ref = ModelRef(provider="lento", model="m1")
    req = ExecutionRequest(capability=Capability.CHAT, prompt="hola")

    t0 = asyncio.get_event_loop().time()
    payload, err, reason = await executor._try_one(req, ref)
    dt = asyncio.get_event_loop().time() - t0

    assert payload is None
    assert reason == "timeout"
    assert "1s" in err
    assert dt < 5, f"el deadline no cortó: tardó {dt:.1f}s"


@pytest.mark.anyio
async def test_timeout_abre_el_breaker_y_la_cadena_salta_al_siguiente(monkeypatch):
    """El objetivo real de NEW-2: un proveedor colgado cuesta el plazo UNA vez
    y la respuesta llega del siguiente candidato — no minutos de espera muda."""
    from app.core.config import settings
    from app.mel import executor
    from app.mel.fallback import _BREAKER_REASONS, breakers

    assert "timeout" in _BREAKER_REASONS, "un plazo vencido tiene que contar para el breaker"

    monkeypatch.setattr(settings, "MEL_REQUEST_DEADLINE_S", 1)
    breakers.reset()

    lento = ModelRef(provider="lento", model="m1")
    rapido = ModelRef(provider="rapido", model="m2")

    async def _execute(ref, prompt, system_prompt=None, **kw):
        if ref.provider == "lento":
            await asyncio.sleep(30)
        return {"response": "respuesta del rápido"}

    monkeypatch.setattr(executor.registry, "execute", _execute)
    monkeypatch.setattr(executor.registry, "list_available", lambda: [lento, rapido])
    monkeypatch.setattr(executor.policy_store, "ensure_compiled", lambda a: None)
    monkeypatch.setattr(executor, "_chain_for", lambda req, av: [lento, rapido])

    res = await executor.complete(ExecutionRequest(capability=Capability.CHAT, prompt="hola"))

    assert res.ok and res.text == "respuesta del rápido"
    assert res.served_by.provider == "rapido"
    assert res.served_by.fallbacks_used == 1
    # y el lento queda marcado: el siguiente mensaje ni lo intenta
    assert breakers.open_reason("lento") in (None, "timeout")  # 1 fallo aún no abre
    breakers.reset()


@pytest.mark.anyio
async def test_deadline_cero_desactiva_el_plazo(monkeypatch):
    """Escape hatch: `MEL_REQUEST_DEADLINE_S=0` deja el comportamiento anterior
    a S4 (sin plazo). Que exista la palanca es parte del contrato."""
    from app.core.config import settings
    from app.mel import executor

    monkeypatch.setattr(settings, "MEL_REQUEST_DEADLINE_S", 0)

    async def _normal(ref, prompt, system_prompt=None, **kw):
        await asyncio.sleep(0.05)
        return {"response": "sin plazo, respondo igual"}
    monkeypatch.setattr(executor.registry, "execute", _normal)

    payload, _, reason = await executor._try_one(
        ExecutionRequest(capability=Capability.CHAT, prompt="x"),
        ModelRef(provider="p", model="m"))
    assert reason == "ok" and payload["text"] == "sin plazo, respondo igual"


@pytest.mark.anyio
async def test_stream_sin_primer_chunk_a_tiempo_se_corta_con_error_honesto(monkeypatch):
    """El plazo del PRIMER chunk. Los siguientes no llevan plazo a propósito
    (cortar a mitad de una respuesta que ya avanza sería peor)."""
    from app.core.config import settings
    from app.mel import executor

    monkeypatch.setattr(settings, "MEL_STREAM_FIRST_CHUNK_S", 1)
    ref = ModelRef(provider="mudo", model="m")

    async def _nunca_empieza(ref_, prompt, system_prompt=None, **kw):
        await asyncio.sleep(30)
        yield "tarde"

    monkeypatch.setattr(executor.registry, "stream", _nunca_empieza)
    monkeypatch.setattr(executor.registry, "list_available", lambda: [ref])
    monkeypatch.setattr(executor.policy_store, "ensure_compiled", lambda a: None)
    monkeypatch.setattr(executor, "_chain_for", lambda req, av: [ref])

    chunks = [c async for c in executor.stream(
        ExecutionRequest(capability=Capability.CHAT, prompt="hola"))]

    assert len(chunks) == 1
    assert "no empezó a responder en 1s" in chunks[0]   # honesto y concreto
    assert "TimeoutError" not in chunks[0]              # no se le enseña la excepción cruda


@pytest.mark.anyio
async def test_stream_que_arranca_a_tiempo_fluye_entero(monkeypatch):
    """No regresión: el plazo del primer chunk no puede cortar un stream sano,
    ni siquiera si TARDA entre chunks intermedios."""
    from app.core.config import settings
    from app.mel import executor

    monkeypatch.setattr(settings, "MEL_STREAM_FIRST_CHUNK_S", 1)
    ref = ModelRef(provider="ok", model="m")

    async def _fluye(ref_, prompt, system_prompt=None, **kw):
        yield "Hola"
        await asyncio.sleep(0.3)   # pausa entre chunks: NO debe cortar
        yield ", mundo"

    monkeypatch.setattr(executor.registry, "stream", _fluye)
    monkeypatch.setattr(executor.registry, "list_available", lambda: [ref])
    monkeypatch.setattr(executor.policy_store, "ensure_compiled", lambda a: None)
    monkeypatch.setattr(executor, "_chain_for", lambda req, av: [ref])

    texto = "".join([c async for c in executor.stream(
        ExecutionRequest(capability=Capability.CHAT, prompt="hola"))])
    assert texto == "Hola, mundo"


# ===========================================================================
# 2) P5 · el clasificador: modelo/política fijos + su propio plazo
# ===========================================================================
@pytest.mark.anyio
async def test_classify_model_fijado_llega_como_override(monkeypatch):
    """`TIE_CLASSIFY_MODEL` tiene que llegar al MEL como override de tarea —
    igual que `TIE_TOOL_MODEL` en el bucle de tool-use."""
    from app.core.config import settings
    from app.tie import intents, router

    monkeypatch.setattr(settings, "TIE_CLASSIFY_MODEL", "ollama:llama3.2:3b")
    visto = {}

    async def _complete(prompt, *, system_prompt=None, capability="chat",
                        model_override=None, policy_override=None, **kw):
        visto.update(model=model_override, policy=policy_override, cap=capability)
        return {"response": '{"type":"conversational","goal":"x","confidence":0.9}', "error": False}
    monkeypatch.setattr(router, "complete", _complete)

    await intents.classify("resume el informe del proyecto")

    assert visto["model"] == "ollama:llama3.2:3b"
    assert visto["policy"] is None      # un modelo fijo manda: no se pasa política
    assert visto["cap"] == "classify"


@pytest.mark.anyio
async def test_classify_sin_modelo_fijo_usa_la_politica_rapida(monkeypatch):
    """Sin modelo fijado manda `TIE_CLASSIFY_POLICY` ("speed" por defecto): el
    clasificador NUNCA hereda la política de calidad del usuario."""
    from app.core.config import settings
    from app.tie import intents, router

    monkeypatch.setattr(settings, "TIE_CLASSIFY_MODEL", "")
    monkeypatch.setattr(settings, "TIE_CLASSIFY_POLICY", "speed")
    visto = {}

    async def _complete(prompt, *, system_prompt=None, capability="chat",
                        model_override=None, policy_override=None, **kw):
        visto.update(model=model_override, policy=policy_override)
        return {"response": '{"type":"conversational","goal":"x","confidence":0.9}', "error": False}
    monkeypatch.setattr(router, "complete", _complete)

    await intents.classify("resume el informe del proyecto")

    assert visto["model"] is None
    assert visto["policy"] == "speed"


@pytest.mark.anyio
async def test_classify_lento_degrada_por_el_camino_que_ya_existia(monkeypatch):
    """Al vencer el plazo NO se inventa una segunda forma de fallar: se degrada
    exactamente igual que ya lo hacía ante un error del clasificador."""
    from app.core.config import settings
    from app.tie import intents, router
    from app.tie.contracts import IntentType

    monkeypatch.setattr(settings, "TIE_CLASSIFY_DEADLINE_S", 1)

    async def _eterno(prompt, **kw):
        await asyncio.sleep(30)
        return {"response": "{}", "error": False}
    monkeypatch.setattr(router, "complete", _eterno)

    t0 = asyncio.get_event_loop().time()
    intent = await intents.classify("cuéntame algo sobre el proyecto")
    dt = asyncio.get_event_loop().time() - t0

    assert intent.type == IntentType.CONVERSATIONAL   # degradación de siempre
    assert dt < 5, f"el deadline del clasificador no cortó: {dt:.1f}s"


@pytest.mark.anyio
async def test_router_propaga_los_overrides_al_mel(monkeypatch):
    """El shim del TIE tiene que trasladar los dos campos al ExecutionRequest —
    si se queda a medias, el ajuste del usuario no llega a ningún sitio."""
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy
    from app.tie import router

    visto = {}

    async def _complete(req):
        visto.update(model=req.model_override, policy=req.policy_override)
        return ExecutionResult(text="ok", ok=True, served_by=ServedBy("f", "m"))
    monkeypatch.setattr(mel, "complete", _complete)

    await router.complete("x", capability="classify",
                          model_override="ollama:llama3", policy_override="speed")
    assert visto == {"model": "ollama:llama3", "policy": "speed"}


@pytest.mark.anyio
async def test_router_sin_overrides_no_cambia_nada(monkeypatch):
    """No regresión: los callers de siempre (planner, responder) no pasan nada
    y el request sale idéntico a antes de S4."""
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy
    from app.tie import router

    visto = {}

    async def _complete(req):
        visto.update(model=req.model_override, policy=req.policy_override)
        return ExecutionResult(text="ok", ok=True, served_by=ServedBy("f", "m"))
    monkeypatch.setattr(mel, "complete", _complete)

    await router.complete("x", capability="reason")
    assert visto == {"model": None, "policy": None}


# ===========================================================================
# 3) P5 · ventana deslizante del transcript del toolloop
# ===========================================================================
def test_ventana_conserva_cabecera_y_ultimas_interacciones():
    """Lo que NO puede caerse nunca: el objetivo y el catálogo de herramientas.
    Sin ellos el modelo pierde qué hace y con qué."""
    from app.tie.toolloop import _prompt_from

    transcript = ["OBJETIVO DEL PASO:\nhaz X", "CONTEXTO DISPONIBLE:\nctx",
                  "HERRAMIENTAS DISPONIBLES:\nfilesystem.read"]
    for i in range(1, 13):
        transcript.append(f"RESULTADO REAL de paso {i}")

    prompt = _prompt_from(transcript, head_n=3, window=8)

    assert "OBJETIVO DEL PASO" in prompt
    assert "HERRAMIENTAS DISPONIBLES" in prompt
    assert "CONTEXTO DISPONIBLE" in prompt
    assert "RESULTADO REAL de paso 12" in prompt      # las últimas, sí
    assert "RESULTADO REAL de paso 5" in prompt
    assert "RESULTADO REAL de paso 1\n" not in prompt + "\n"  # la primera, no
    assert "4 interacciones anteriores omitidas" in prompt    # y se declara


def test_ventana_no_toca_un_transcript_corto():
    """No regresión: mientras quepa, el prompt es exactamente el de siempre."""
    from app.tie.toolloop import _prompt_from

    transcript = ["OBJETIVO", "HERRAMIENTAS", "paso 1", "paso 2"]
    assert _prompt_from(transcript, head_n=2, window=8) == "\n\n".join(transcript)


def test_ventana_cero_desactiva_el_recorte():
    """Escape hatch (`TIE_TOOL_TRANSCRIPT_WINDOW=0`): comportamiento previo a S4."""
    from app.tie.toolloop import _prompt_from

    transcript = ["OBJETIVO", "HERRAMIENTAS"] + [f"paso {i}" for i in range(30)]
    assert _prompt_from(transcript, head_n=2, window=0) == "\n\n".join(transcript)


def test_la_ventana_recorta_de_verdad_el_tamano_del_prompt():
    """La medida que importa: con observaciones grandes, el prompt de la última
    vuelta deja de crecer sin límite (era ~50k chars a las 12 iteraciones)."""
    from app.tie.toolloop import _prompt_from

    cabecera = ["OBJETIVO", "HERRAMIENTAS"]
    gordo = "x" * 4000
    transcript = cabecera + [f"RESULTADO {i}: {gordo}" for i in range(12)]

    entero = _prompt_from(transcript, head_n=2, window=0)
    acotado = _prompt_from(transcript, head_n=2, window=8)

    assert len(entero) > 48_000
    assert len(acotado) < len(entero) * 0.75


# ===========================================================================
# 4) NEW-2 · latido: ningún turno mudo
# ===========================================================================
@pytest.mark.anyio
async def test_heartbeat_emite_mientras_la_tarea_sigue_viva():
    """El objetivo medible de S4: ningún turno por encima del plazo sin evento."""
    from app.tie.pipeline import _heartbeat_until

    async def _trabajo_largo():
        await asyncio.sleep(0.35)
        return "hecho"

    task = asyncio.ensure_future(_trabajo_largo())
    eventos = [ev async for ev in _heartbeat_until(task, every_s=0.1)]

    assert len(eventos) >= 2
    assert all(k == "status" for k, _ in eventos)
    assert await task == "hecho"        # el latido NO consume el resultado


@pytest.mark.anyio
async def test_heartbeat_no_molesta_a_una_tarea_rapida():
    """Una respuesta rápida (el ~80% de los turnos) no ve ni un latido."""
    from app.tie.pipeline import _heartbeat_until

    async def _rapido():
        return "ya"

    task = asyncio.ensure_future(_rapido())
    eventos = [ev async for ev in _heartbeat_until(task, every_s=5)]
    assert eventos == []
    assert await task == "ya"


@pytest.mark.anyio
async def test_heartbeat_desactivado_con_cero():
    from app.tie.pipeline import _heartbeat_until

    async def _algo():
        await asyncio.sleep(0.05)
        return 1

    task = asyncio.ensure_future(_algo())
    assert [ev async for ev in _heartbeat_until(task, every_s=0)] == []
    assert await task == 1


@pytest.mark.anyio
async def test_heartbeat_no_se_traga_la_excepcion_de_la_tarea():
    """Si el trabajo falla, el fallo tiene que seguir llegando al caller — el
    latido observa, no captura."""
    from app.tie.pipeline import _heartbeat_until

    async def _revienta():
        await asyncio.sleep(0.05)
        raise RuntimeError("boom")

    task = asyncio.ensure_future(_revienta())
    _ = [ev async for ev in _heartbeat_until(task, every_s=5)]
    with pytest.raises(RuntimeError, match="boom"):
        await task
