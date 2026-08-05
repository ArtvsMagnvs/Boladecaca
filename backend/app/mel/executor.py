# app/mel/executor.py — ejecución + fallback + registro (doc 19 §8/§9, E1)
#
# El punto donde todo se junta: `complete(req)`/`stream(req)`. Decide (Rule
# Engine) → ejecuta contra el modelo elegido (registry) → si falla, clasifica y
# salta al siguiente candidato (≤3 saltos) → registra en `mel_executions` (async,
# fuera del hot path) → devuelve `ExecutionResult`.
#
# Garantías: el caller JAMÁS conoce el modelo salvo leyendo `served_by`
# (observabilidad, no control); un fallo de registro/evento nunca afecta a la
# respuesta; el `text` sale limpio (strip_reasoning B21).
from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Optional

from app.ai.reasoning_filter import StreamingReasoningFilter, strip_reasoning
from app.core.logging_config import get_system_logger
from app.mel import decision, registry
from app.mel.contracts import (
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ModelRef,
    ServedBy,
    Usage,
)
from app.mel.fallback import FailureAction, REQUEST_FAULT_REASONS, breakers, classify_failure
from app.mel.policies import policy_store
from app.mel.repetition import RepetitionGuard
from app.mel.contracts import PolicyName

logger = get_system_logger("mel.executor")

_MAX_HOPS = 3   # máx. saltos de cadena por request (doc 19 §8.1)


def _chain_for(req: ExecutionRequest, available: list[ModelRef]) -> list[ModelRef]:
    """La cadena de candidatos para esta petición: la de la política activa, o la
    de `policy_override` si el caller la pidió (p.ej. el summarizer → economy).
    `policy_override` lee la política PERSISTIDA por nombre (respeta las ediciones
    del usuario), no la recompila desde el catálogo."""
    if req.policy_override:
        name = req.policy_override.lower()
        try:
            PolicyName(name)  # valida que sea un nombre conocido
            chain = policy_store.chain_for_named(name, req.capability, available)
            if chain:
                return chain
        except ValueError:
            pass  # override inválido → cae a la política activa
    return policy_store.active_chain(req.capability, available)


def _apply_exclude(available: list[ModelRef], exclude: tuple[str, ...]) -> list[ModelRef]:
    """Quita de `available` los model_keys en `req.exclude` (doc 19 §5.4.2 — p.ej.
    research.py evita que un modelo se autoevalúe). Vacío si no hay exclusiones."""
    if not exclude:
        return available
    skip = set(exclude)
    return [r for r in available if r.key not in skip]


def _resolve_forced(
    req: ExecutionRequest, available: list[ModelRef]
) -> tuple[Optional[ModelRef], str, bool]:
    """Precedencia del control explícito (doc 19 §7b): override de TAREA
    (`model_override`, orden inmediato del usuario) > pin de PROYECTO
    (`mel_overrides`, preferencia persistente) > política.

    Devuelve (ref|None, origin, hard):
      - `origin` ∈ "user_explicit" | "project_pin" | "policy" (para la traza).
      - `hard` True SOLO para el override de tarea: si ese modelo no está
        disponible NUNCA se sustituye en silencio → ExplicitModelUnavailable
        (el usuario lo pidió AHORA, se le dice AHORA). El pin de proyecto es
        una preferencia persistente: si su modelo ya no está, degrada a la
        política (mejor que dejar TODO el proyecto sin IA hasta que lo note)."""
    from app.mel import overrides

    by_key = {r.key: r for r in available}

    # 1) override de tarea (efímero, inmediato) — fallo duro si no está
    if req.model_override:
        ref = by_key.get(req.model_override) or registry.resolve_model_name(req.model_override)
        return ref, "user_explicit", True

    # 2) pin de proyecto (persistente) — degradación suave si su modelo no está
    project_id = (req.context_tags or {}).get("project_id")
    pin = overrides.override_model_for(project_id, req.capability.value) if project_id else None
    if pin:
        ref = by_key.get(pin) or registry.resolve_model_name(pin)
        if ref is not None:
            return ref, "project_pin", False
        logger.warning(f"[executor] pin de proyecto {project_id} → «{pin}» no disponible; "
                       f"degrado a política para {req.capability.value}")

    return None, "policy", False


async def complete(req: ExecutionRequest) -> ExecutionResult:
    """Ejecuta una petición y devuelve el resultado. Nunca lanza: cualquier fallo
    se convierte en `ExecutionResult(ok=False)` con el detalle (el caller decide su
    degradación — p.ej. el summarizer cae a plantilla)."""
    t0 = time.monotonic()
    available = _apply_exclude(registry.list_available(), req.exclude)
    if not available:
        return ExecutionResult(text="", ok=False, error="no hay proveedores IA configurados")

    policy_store.ensure_compiled(available)   # defensivo (idempotente)

    forced, origin, hard = _resolve_forced(req, available)
    if hard and forced is None:
        # El usuario pidió un modelo que no tiene → NUNCA sustituir en silencio.
        opciones = ", ".join(sorted({r.provider for r in available}))
        return ExecutionResult(
            text="", ok=False,
            error=f"ExplicitModelUnavailable: «{req.model_override}» no está configurado. Disponibles: {opciones}",
        )

    # [2026-07-22, orden del usuario] Ni siquiera un override puede ejecutar un
    # modelo NO CAPAZ de esta tarea (catálogo o medido por el task-bench):
    #  - override de TAREA (duro): se le dice claro al usuario, no se sustituye
    #    en silencio (mismo criterio que ExplicitModelUnavailable).
    #  - pin de PROYECTO (suave): degrada a la política con log, igual que
    #    cuando el modelo pineado ya no está configurado.
    # `fitness_exempt` (append-only): SOLO el banco de medición — sin esta
    # excepción, un modelo excluido no podría re-medirse nunca.
    if forced is not None and not req.fitness_exempt:
        from app.mel.policies import is_capable
        if not is_capable(forced, req.capability):
            if hard:
                return ExecutionResult(
                    text="", ok=False,
                    error=(f"ExplicitModelUnfit: «{forced.key}» no puede realizar la tarea "
                           f"'{req.capability.value}' (no apto por catálogo o por medición). "
                           f"Elige otro modelo para esto."),
                )
            logger.warning(f"[executor] pin de proyecto → «{forced.key}» no es capaz de "
                           f"{req.capability.value}; degrado a política")
            forced = None

    chain = [forced] if forced else _chain_for(req, available)
    trace = decision.decide(req, chain, breakers.is_closed, forced=forced, forced_origin=origin)

    if not chain:
        _record_async(req, None, ok=False, latency_ms=int((time.monotonic() - t0) * 1000),
                      fallback_reason="no_chain", trace_id=trace.id, attempts=0)
        return ExecutionResult(text="", ok=False,
                               error=f"la política activa no tiene modelo para {req.capability.value}",
                               decision_id=trace.id)

    # Recorre la cadena desde el elegido, saltando breakers abiertos.
    attempts = 0
    last_error = "sin candidatos viables"
    last_reason = "no_viable"
    # [2026-07-22, #212] Observabilidad de fallos: se retiene QUIÉN falló (el
    # último candidato) y qué candidatos se probaron. Antes el registro de un
    # fallo llevaba provider/model NULL y solo la razón CLASIFICADA
    # ("request_invalid") — diagnosticar el caso real de MiniMax-M3-highspeed
    # exigió una sonda en vivo que un log con el error crudo habría evitado.
    last_ref: Optional[ModelRef] = None
    tried: list[str] = []
    # [2026-07-23, #213] STOP con EVIDENCIA, no con un solo 4xx. Antes,
    # cualquier "request_invalid" cortaba la cadena entera — y el caso real de
    # producción (MiniMax-M3-highspeed devolviendo 400 "invalid model", un
    # fallo de ESE modelo) dejó al usuario sin respuesta con fallbacks sanos
    # disponibles. Ahora solo se corta cuando ≥2 proveedores DISTINTOS
    # coinciden en un fallo de la familia request (REQUEST_FAULT_REASONS):
    # dos APIs independientes rechazando el mismo request sí prueban que el
    # problema es el request. `bad_model` nunca cuenta (config por-modelo).
    request_fault_providers: set[str] = set()
    for ref in chain:
        if attempts >= _MAX_HOPS:
            break
        if not breakers.is_closed(ref.provider):
            continue
        attempts += 1
        result, err, reason = await _try_one(req, ref)
        if result is not None:
            breakers.record_success(ref.provider)
            latency = int((time.monotonic() - t0) * 1000)
            served = ServedBy(provider=ref.provider, model=ref.model, attempts=attempts,
                              fallbacks_used=attempts - 1)
            _record_async(req, ref, ok=True, latency_ms=latency, tokens=result.get("tokens"),
                          trace_id=trace.id, attempts=attempts)
            return ExecutionResult(
                text=result["text"], ok=True, served_by=served,
                usage=Usage(tokens=result.get("tokens"), latency_ms=latency),
                decision_id=trace.id,
            )
        # falló este candidato
        last_error, last_reason, last_ref = err, reason, ref
        tried.append(ref.key)
        breakers.record_failure(ref.provider, reason)
        if reason in REQUEST_FAULT_REASONS:
            request_fault_providers.add(ref.provider)
            if len(request_fault_providers) >= 2:
                break   # evidencia: es el request, rotar más es quemar llamadas

    latency = int((time.monotonic() - t0) * 1000)
    _record_async(req, last_ref, ok=False, latency_ms=latency, fallback_reason=last_reason,
                  trace_id=trace.id, attempts=attempts, error=last_error, tried=tried)
    return ExecutionResult(text="", ok=False, error=last_error, decision_id=trace.id,
                           usage=Usage(latency_ms=latency))


async def _try_one(req: ExecutionRequest, ref: ModelRef) -> tuple[Optional[dict], str, str]:
    """Intenta UN candidato. Devuelve (payload|None, error, reason). `payload` =
    {text, tokens} si OK. Aplica 1 reintento del mismo modelo ante respuesta
    vacía (doc 19 §8.1)."""
    from app.core.config import settings

    deadline = settings.MEL_REQUEST_DEADLINE_S
    for attempt in (1, 2):
        try:
            # [R6.5a] `messages` SOLO se pasa cuando de verdad hay historial.
            # Sin él, la llamada es byte a byte la de siempre — así el cambio es
            # ADITIVO de verdad: nada que envuelva o sustituya a `registry`
            # (tests, futuros decoradores) tiene que enterarse de nada.
            # [2026-08-04] `workdir` viaja igual de aditivo: solo se nombra
            # cuando el caller lo pidió (agentes CLI sobre la carpeta de un
            # proyecto). Sin él, la llamada sigue siendo la de siempre.
            # [B·WEB-2] Las imágenes van primero: son la razón de ser de la
            # petición cuando existen (visión), y a diferencia del resto NO
            # degradan — si el proveedor no las acepta, el registry lanza y
            # este candidato cuenta como fallido (se salta al siguiente).
            if req.images:
                call = registry.execute(ref, req.prompt, req.system_prompt,
                                        messages=req.messages or None,
                                        images=list(req.images))
            elif req.workdir:
                call = registry.execute(ref, req.prompt, req.system_prompt,
                                        messages=req.messages or None, workdir=req.workdir)
            elif req.messages:
                call = registry.execute(ref, req.prompt, req.system_prompt, messages=req.messages)
            else:
                call = registry.execute(ref, req.prompt, req.system_prompt)
            # [S4 · NEW-2] DEADLINE por petición. Antes el único límite era el
            # del propio provider (180 s en Ollama) y, con cadena de fallback,
            # eran 180 s POR SALTO — un proveedor colgado podía costar minutos.
            raw = await (asyncio.wait_for(call, timeout=deadline) if deadline > 0 else call)
        except asyncio.TimeoutError:
            # Razón propia (no la genérica "transient"): un proveedor que agota
            # el plazo es un diagnóstico distinto de un error de red, y así se
            # ve tal cual en `mel_executions`/telemetría. Abre el breaker igual.
            logger.warning(f"[executor] {ref.provider}:{ref.model} superó el plazo de "
                           f"{deadline}s ({req.capability.value}) — salto al siguiente")
            return None, f"deadline de {deadline}s superado", "timeout"
        except Exception as e:
            action, reason = classify_failure(exc=e)
            return None, f"{type(e).__name__}: {e}", reason

        if raw.get("error"):
            action, reason = classify_failure(detail=raw.get("response", "") or "error")
            return None, raw.get("response", "error") or "error", reason

        text = strip_reasoning(raw.get("response", "") or "") or ""
        if text.strip():
            return {"text": text, "tokens": raw.get("tokens")}, "", "ok"

        # respuesta vacía: reintenta una vez el mismo modelo, luego rinde
        if attempt == 1:
            continue
        return None, "empty_response", "empty_response"
    return None, "empty_response", "empty_response"


async def _with_first_chunk_deadline(origen: AsyncIterator[str], deadline_s: int,
                                     ref: ModelRef) -> AsyncIterator[str]:
    """[S4 · NEW-2] Envuelve un stream aplicando plazo SOLO al primer chunk.

    Si el primer chunk no llega a tiempo, lanza `asyncio.TimeoutError` — la
    recoge el `except` de `stream()`, que ya sabe registrar el fallo, abrir el
    breaker y emitir un chunk de error honesto. No se inventa aquí un segundo
    camino de degradación: se reusa el que ya existe."""
    it = origen.__aiter__()
    primero = True
    while True:
        try:
            nxt = it.__anext__()
            raw = await (asyncio.wait_for(nxt, timeout=deadline_s)
                         if (primero and deadline_s > 0) else nxt)
        except StopAsyncIteration:
            return
        except asyncio.TimeoutError:
            logger.warning(f"[executor] {ref.provider}:{ref.model} no emitió el primer chunk "
                           f"en {deadline_s}s — se corta")
            raise
        primero = False
        yield raw


async def stream(req: ExecutionRequest) -> AsyncIterator[str]:
    """Streaming: mismo pipeline de decisión, pero emite chunks de texto ya
    filtrados (B21 incremental). Sin fallback multi-salto a media stream en V1.0
    (si el primer candidato falla antes de emitir, se rinde con un chunk de
    error — el caller conserva su degradación). Los saltos de cadena en streaming
    son V1.2."""
    t0 = time.monotonic()
    available = _apply_exclude(registry.list_available(), req.exclude)
    if not available:
        yield "[MEL: no hay proveedores IA configurados]"
        return
    policy_store.ensure_compiled(available)

    forced, origin, hard = _resolve_forced(req, available)
    if hard and forced is None:
        yield f"[MEL: «{req.model_override}» no está configurado]"
        return

    chain = [forced] if forced else _chain_for(req, available)
    trace = decision.decide(req, chain, breakers.is_closed, forced=forced, forced_origin=origin)
    ref = decision.ref_from_key(trace.chosen, available) if trace.chosen else None
    if ref is None:
        yield f"[MEL: sin modelo viable para {req.capability.value}]"
        return

    filt = StreamingReasoningFilter()
    # [Fix 2026-07-19] Guard anti-atasco. Un modelo puede entrar en bucle y
    # repetir el mismo token cientos de veces (caso real: MiniMax-M2.7 emitió
    # 窗外 ×221 a mitad de una respuesta por lo demás correcta). La degeneración
    # es del modelo, pero retransmitirla entera a la pantalla es cosa nuestra.
    # Aquí, en el único punto por el que sale texto en streaming, se corta una
    # vez y protege a toda la aplicación.
    guard = RepetitionGuard()
    # [S4 · NEW-2] DEADLINE del PRIMER chunk. Es el que importa: si el modelo no
    # ha empezado a escribir en este plazo, el usuario lleva todo ese rato
    # mirando un cursor. Los siguientes chunks NO llevan plazo (ya fluye:
    # cortar a mitad de una respuesta que avanza sería peor). Se lee ANTES del
    # try para que el `except` pueda nombrarlo sin riesgo de NameError.
    from app.core.config import settings

    first_s = settings.MEL_STREAM_FIRST_CHUNK_S
    try:
        # Mismo criterio que en `complete`: sin historial, la llamada de siempre.
        origen = (registry.stream(ref, req.prompt, req.system_prompt, messages=req.messages)
                  if req.messages
                  else registry.stream(ref, req.prompt, req.system_prompt))
        async for raw in _with_first_chunk_deadline(origen, first_s, ref):
            visible = filt.feed(raw)
            if visible:
                yield visible
                if guard.feed(visible):
                    logger.info(
                        f"[mel] {ref.provider}:{ref.model} se atascó repitiendo "
                        f"{guard.pattern!r} — stream cortado"
                    )
                    yield guard.note
                    breakers.record_success(ref.provider)  # respondió; solo se atascó
                    return
        tail = filt.flush()
        if tail:
            yield tail
        breakers.record_success(ref.provider)
    except Exception as e:
        # [S4] Un deadline vencido se nombra como tal ("timeout"), no como el
        # genérico "transient": es un diagnóstico distinto (el proveedor no
        # respondió A TIEMPO, no que la red fallara) y así se lee en la
        # telemetría. `str(TimeoutError())` es vacío, de ahí el texto propio.
        es_timeout = isinstance(e, asyncio.TimeoutError)
        reason = "timeout" if es_timeout else classify_failure(exc=e)[1]
        detalle = f"no empezó a responder en {first_s}s" if es_timeout else str(e)
        breakers.record_failure(ref.provider, reason)
        # [#212] El fallo de streaming tampoco puede ser invisible: antes este
        # camino no dejaba NINGÚN rastro en telemetría (solo el texto de error
        # incrustado en el propio stream, que se pierde con la conversación).
        _record_async(req, ref, ok=False,
                      latency_ms=int((time.monotonic() - t0) * 1000),
                      fallback_reason=reason, trace_id=trace.id,
                      error=f"{type(e).__name__}: {detalle}")
        yield f"[MEL: error de streaming en {ref.provider}: {detalle}]"


# ---------------------------------------------------------------------------
# Registro async de mel_executions (fuera del hot path — best-effort)
# ---------------------------------------------------------------------------
def _record_async(req: ExecutionRequest, ref: Optional[ModelRef], *, ok: bool,
                  latency_ms: int, tokens: Optional[int] = None,
                  fallback_reason: Optional[str] = None, trace_id: Optional[str] = None,
                  attempts: int = 1, error: Optional[str] = None,
                  tried: Optional[list[str]] = None) -> None:
    """Escribe una fila en `mel_executions`. Nunca bloquea ni rompe: si hay un
    event loop corriendo, lo hace en una task; si no (contexto sync/tests), lo
    escribe inline y traga errores.

    [#212] `error` es el texto CRUDO del fallo del proveedor (recortado) y
    `tried` la lista de candidatos probados — van al `detail` JSON de la
    telemetría, no a `mel_executions` (su esquema no cambia). La razón
    clasificada ("request_invalid") dice QUÉ tipo de fallo fue; el texto crudo
    dice POR QUÉ de verdad ("invalid model ... 400 Bad Request")."""
    # [2026-07-21, doc 31] Telemetría punta a punta: CADA llamada LLM de
    # `complete` queda en `mission_events` con su capacidad, modelo, latencia y
    # resultado — ligada a la misión en curso vía contextvar. Best-effort:
    # telemetry.record jamás lanza.
    try:
        import app.telemetry as _telemetry

        detail: dict = {}
        if attempts > 1 or fallback_reason:
            detail = {"attempts": attempts, "fallback_reason": fallback_reason}
        if error:
            detail["error"] = error[:300]
        if tried and len(tried) > 1:
            detail["tried"] = tried
        _telemetry.record(
            "llm_call", name=req.capability.value,
            provider=ref.provider if ref else None,
            model=ref.model if ref else None,
            duration_ms=latency_ms, ok=ok,
            detail=detail or None,
        )
    except Exception:
        pass

    async def _store() -> None:
        from app.db.database import SessionLocal
        from app.mel.models import MelExecution

        db = SessionLocal()
        try:
            db.add(MelExecution(
                capability=req.capability.value,
                provider=ref.provider if ref else None,
                model=ref.model if ref else None,
                ok=ok, latency_ms=latency_ms, tokens=tokens,
                attempts=attempts, fallbacks_used=max(0, attempts - 1),
                fallback_reason=fallback_reason,
                decision_id=trace_id, context_tags=req.context_tags or None,
            ))
            db.commit()
        except Exception as e:
            logger.error(f"[executor] registro mel_executions falló (no crítico): {type(e).__name__}: {e}")
            db.rollback()
        finally:
            db.close()

    try:
        asyncio.get_running_loop().create_task(_store())
    except RuntimeError:
        # sin loop (contexto sync): mejor esfuerzo inline
        try:
            asyncio.run(_store())
        except Exception:
            pass
