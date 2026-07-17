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
from app.mel.fallback import FailureAction, breakers, classify_failure
from app.mel.policies import _compile_policy, policy_store
from app.mel.contracts import PolicyName

logger = get_system_logger("mel.executor")

_MAX_HOPS = 3   # máx. saltos de cadena por request (doc 19 §8.1)


def _chain_for(req: ExecutionRequest, available: list[ModelRef]) -> list[ModelRef]:
    """La cadena de candidatos para esta petición: la de la política activa, o la
    de `policy_override` si el caller la pidió (p.ej. el summarizer → offline)."""
    if req.policy_override:
        try:
            name = PolicyName(req.policy_override.lower())
            by_key = {r.key: r for r in available}
            chains = _compile_policy(name, available)
            return [by_key[k] for k in chains.get(req.capability.value, []) if k in by_key]
        except (ValueError, KeyError):
            pass  # override inválido → cae a la política activa
    return policy_store.active_chain(req.capability, available)


def _resolve_forced(req: ExecutionRequest, available: list[ModelRef]) -> tuple[Optional[ModelRef], bool]:
    """Si el usuario pidió un modelo explícito (`model_override`, doc 19 §7b),
    lo resuelve contra los disponibles. Devuelve (ref|None, requested): `requested`
    True si había un override (para distinguir "no pidió nada" de "pidió algo no
    disponible" → ExplicitModelUnavailable)."""
    if not req.model_override:
        return None, False
    by_key = {r.key: r for r in available}
    if req.model_override in by_key:
        return by_key[req.model_override], True
    ref = registry.resolve_model_name(req.model_override)
    return ref, True


async def complete(req: ExecutionRequest) -> ExecutionResult:
    """Ejecuta una petición y devuelve el resultado. Nunca lanza: cualquier fallo
    se convierte en `ExecutionResult(ok=False)` con el detalle (el caller decide su
    degradación — p.ej. el summarizer cae a plantilla)."""
    t0 = time.monotonic()
    available = registry.list_available()
    if not available:
        return ExecutionResult(text="", ok=False, error="no hay proveedores IA configurados")

    policy_store.ensure_compiled(available)   # defensivo (idempotente)

    forced, requested = _resolve_forced(req, available)
    if requested and forced is None:
        # El usuario pidió un modelo que no tiene → NUNCA sustituir en silencio.
        opciones = ", ".join(sorted({r.provider for r in available}))
        return ExecutionResult(
            text="", ok=False,
            error=f"ExplicitModelUnavailable: «{req.model_override}» no está configurado. Disponibles: {opciones}",
        )

    chain = [forced] if forced else _chain_for(req, available)
    trace = decision.decide(req, chain, breakers.is_closed,
                            forced=forced, forced_origin="user_explicit" if forced else "policy")

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
        last_error, last_reason = err, reason
        breakers.record_failure(ref.provider, reason)
        if reason == "request_invalid":
            break   # fallo del request: rotar no ayuda (doc 19 §8.1)

    latency = int((time.monotonic() - t0) * 1000)
    _record_async(req, None, ok=False, latency_ms=latency, fallback_reason=last_reason,
                  trace_id=trace.id, attempts=attempts)
    return ExecutionResult(text="", ok=False, error=last_error, decision_id=trace.id,
                           usage=Usage(latency_ms=latency))


async def _try_one(req: ExecutionRequest, ref: ModelRef) -> tuple[Optional[dict], str, str]:
    """Intenta UN candidato. Devuelve (payload|None, error, reason). `payload` =
    {text, tokens} si OK. Aplica 1 reintento del mismo modelo ante respuesta
    vacía (doc 19 §8.1)."""
    for attempt in (1, 2):
        try:
            raw = await registry.execute(ref, req.prompt, req.system_prompt)
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


async def stream(req: ExecutionRequest) -> AsyncIterator[str]:
    """Streaming: mismo pipeline de decisión, pero emite chunks de texto ya
    filtrados (B21 incremental). Sin fallback multi-salto a media stream en V1.0
    (si el primer candidato falla antes de emitir, se rinde con un chunk de
    error — el caller conserva su degradación). Los saltos de cadena en streaming
    son V1.2."""
    available = registry.list_available()
    if not available:
        yield "[MEL: no hay proveedores IA configurados]"
        return
    policy_store.ensure_compiled(available)

    forced, requested = _resolve_forced(req, available)
    if requested and forced is None:
        yield f"[MEL: «{req.model_override}» no está configurado]"
        return

    chain = [forced] if forced else _chain_for(req, available)
    trace = decision.decide(req, chain, breakers.is_closed,
                            forced=forced, forced_origin="user_explicit" if forced else "policy")
    ref = decision.ref_from_key(trace.chosen, available) if trace.chosen else None
    if ref is None:
        yield f"[MEL: sin modelo viable para {req.capability.value}]"
        return

    filt = StreamingReasoningFilter()
    try:
        async for raw in registry.stream(ref, req.prompt, req.system_prompt):
            visible = filt.feed(raw)
            if visible:
                yield visible
        tail = filt.flush()
        if tail:
            yield tail
        breakers.record_success(ref.provider)
    except Exception as e:
        _, reason = classify_failure(exc=e)
        breakers.record_failure(ref.provider, reason)
        yield f"[MEL: error de streaming en {ref.provider}: {e}]"


# ---------------------------------------------------------------------------
# Registro async de mel_executions (fuera del hot path — best-effort)
# ---------------------------------------------------------------------------
def _record_async(req: ExecutionRequest, ref: Optional[ModelRef], *, ok: bool,
                  latency_ms: int, tokens: Optional[int] = None,
                  fallback_reason: Optional[str] = None, trace_id: Optional[str] = None,
                  attempts: int = 1) -> None:
    """Escribe una fila en `mel_executions`. Nunca bloquea ni rompe: si hay un
    event loop corriendo, lo hace en una task; si no (contexto sync/tests), lo
    escribe inline y traga errores."""
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
