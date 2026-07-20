# app/tie/router.py — Model Router mínimo del TIE (doc 14 §3.5, T2)
#
# El punto ÚNICO por el que el TIE llama a un LLM: intents, planner y responder
# pasan todos por `router.complete(prompt, capability=...)`.
#
# HISTORIA (y por qué este archivo sigue existiendo siendo tan corto): en T2 esto
# era una fachada sobre el AIManager con hints `fast()`/`smart()`, porque el MEL
# todavía no existía. El bloque E2 (doc 22) hizo EL SWITCH que este archivo
# anunciaba: `complete()` delega en `mel.complete(capability=...)` y es el MEL
# quien elige el modelo (política activa, override de tarea, pin de proyecto).
#
# [R7] Los hints `fast()`/`smart()`/`choose()`/`active_model()` se retiraron aquí:
# desde E2 no los consultaba NADIE (verificado por grep en `app/` y `tests/`), y
# un reparto de modelos paralelo al del MEL sería una segunda fuente de verdad
# sobre la misma decisión. La selección de modelo vive en UN solo sitio: el MEL
# (Ajustes → Inteligencia). Se mantiene `complete()` porque el TIE conserva su
# API interna — el día que el MEL cambie, solo cambia este archivo.
from __future__ import annotations

from typing import Optional

from app.core.logging_config import get_system_logger

logger = get_system_logger("tie.router")

async def complete(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    capability: str = "chat",
) -> dict:
    """Ejecuta una petición al modelo adecuado para `capability`. Punto ÚNICO de
    llamada al LLM del TIE — intents/planner/responder pasan por aquí. Devuelve
    `{response, model, tokens, error}` (mismo shape que `ai_manager.chat` — el
    caller no se entera del cambio).

    [E2, doc 22 §3·E2] EL SWITCH que este archivo ya anunciaba: delega en
    `mel.complete(ExecutionRequest(capability=...))`. El MEL elige el modelo por
    la política activa; `fast()`/`smart()` quedan como hints heredados de T2 que
    ya nadie consulta (el reparto real lo hacen las cadenas compiladas). El TIE
    conserva su API interna (`router.complete`) — solo cambia a QUÉ delega."""
    from app.mel import Capability, ExecutionRequest, complete as mel_complete

    # capability es un string (p.ej. "reason") que coincide con el valor del enum.
    try:
        cap = Capability(capability)
    except ValueError:
        cap = Capability.CHAT
    res = await mel_complete(ExecutionRequest(
        capability=cap, prompt=prompt, system_prompt=system_prompt,
    ))
    # Adaptación al shape dict de siempre (response/model/tokens/error): el
    # caller (intents/planner/responder) lee result.get("response")/.get("error").
    return {
        "response": res.text,
        "model": res.served_by.model if res.served_by else None,
        "tokens": res.usage.tokens if res.usage else None,
        "error": not res.ok,
        "capability": capability,
    }
