# app/tie/router.py — Model Router mínimo del TIE (doc 14 §3.5, T2)
#
# La política de "qué modelo" sobre el AIManager. Hoy es una FACHADA de pocas
# líneas a propósito (doc 19 §1.1 + doc 21 §Δ): el TIE llama SIEMPRE a
# `router.complete(prompt, capability=...)`, y cuando exista el MEL (bloque E1 de
# V1.0, plan aparte) esta función pasa a delegar en `mel.complete(capability=...)`
# con un cambio de UNA línea — el resto del TIE (intents, planner, responder) no
# se entera. La taxonomía de capacidades es la del MEL (doc 19 §3), ya congelada
# en `contracts.MEL_CAPABILITIES`.
#
# En V1.0/T2 el AIManager no permite override de modelo por-llamada (usa el
# proveedor activo), así que `fast()`/`smart()` devuelven HINTS (de Settings o el
# modelo activo) para la traza y el futuro MEL; `complete()` ejecuta por el
# proveedor activo. Es la "implementación mínima funcional" — sin duplicar la
# gestión de proveedores que ya hace el AIManager (y que el MEL absorberá).
from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.logging_config import get_system_logger

logger = get_system_logger("tie.router")

# Capacidades que el TIE mapea a "modelo potente" (el resto → barato). El MEL
# afinará esto por catálogo + aprendizaje; aquí es el reparto mínimo de V1.0.
_SMART_CAPABILITIES = {"reason", "code", "analyze"}


def active_model() -> Optional[str]:
    """El modelo del proveedor activo del AIManager (o None si no hay)."""
    try:
        from app.ai.ai_manager import ai_manager

        prov = ai_manager.current_provider
        return getattr(prov, "model", None) if prov else None
    except Exception:
        return None


def fast() -> Optional[str]:
    """Hint de modelo barato (intent/clasificación). Settings o modelo activo."""
    return settings.TIE_FAST_MODEL or active_model()


def smart() -> Optional[str]:
    """Hint de modelo potente (planner). Settings o modelo activo."""
    return settings.TIE_SMART_MODEL or active_model()


def choose(capability: str = "chat", *, model_hint: Optional[str] = None) -> Optional[str]:
    """Resuelve un hint de modelo para una capacidad/nodo. Respeta `model_hint`
    del nodo si es un id concreto; si es 'fast'/'smart' o una capacidad, mapea."""
    if model_hint:
        if model_hint == "fast":
            return fast()
        if model_hint == "smart":
            return smart()
        if model_hint in _SMART_CAPABILITIES:
            return smart()
        if model_hint in ("chat", "classify", "extract", "summarize", "draft"):
            return fast()
        return model_hint  # id concreto
    return smart() if capability in _SMART_CAPABILITIES else fast()


async def complete(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    capability: str = "chat",
) -> dict:
    """Ejecuta una petición al modelo adecuado para `capability`. Punto ÚNICO de
    llamada al LLM del TIE — intents/planner/responder pasan por aquí. Devuelve
    `{response, model, tokens, error}` (mismo shape que `ai_manager.chat`).

    [Shim del MEL] En T2 delega en `ai_manager.chat` (proveedor activo). E1:
    esta función se reescribe a `mel.complete(ExecutionRequest(capability=...))`
    y los hints fast/smart migran a las políticas del MEL — el TIE no cambia."""
    from app.ai.ai_manager import ai_manager

    result = await ai_manager.chat(message=prompt, system_prompt=system_prompt)
    # anotamos qué capacidad se pidió (traza/observabilidad; el MEL lo formaliza)
    result.setdefault("capability", capability)
    return result
