# app/mel/registry.py — Provider Registry del MEL (doc 19 §1.1/§10, E1)
#
# ENVUELVE al AIManager existente (doc 22 Δ4) — no lo reescribe. El AIManager ya
# tiene 8 providers reales con clientes httpx persistentes (doc 12 A2) y health
# cacheado; aquí solo se TRADUCE entre el mundo del MEL (capacidades, ModelRef) y
# el mundo del AIManager (instancias de proveedor con su modelo).
#
# **El único módulo del MEL que importa `ai_manager`** (frontera dura, doc 16 —
# vigilada por test_module_boundaries): el resto del MEL habla con proveedores
# SOLO a través de este registry.
#
# Decisión de diseño clave (auditada en el código real, doc 22 Δ4): el AIManager
# NO permite override de modelo por-llamada — cada instancia de proveedor tiene UN
# modelo fijo. Como en Aithera V1.0 hay exactamente 1 modelo configurado por
# proveedor, un candidato del MEL = `(provider, su modelo)`, y ejecutar = llamar a
# `ai_manager.providers[provider].generate(...)` directamente. No hay desajuste
# posible porque `list_available()` SOLO devuelve los (provider, model) realmente
# configurados. (Multi-modelo por proveedor es futuro, no V1.0 — se anota, no se
# construye: sería sobreingeniería sobre algo que Aithera aún no soporta.)
from __future__ import annotations

import re
from typing import AsyncIterator, Optional

from app.core.logging_config import get_system_logger
from app.mel.catalog import is_local as _catalog_is_local
from app.mel.contracts import ModelRef

logger = get_system_logger("mel.registry")


def list_available() -> list[ModelRef]:
    """Los (proveedor, modelo) realmente utilizables: configurados en el
    AIManager, MÁS los modelos locales especializados instalados y habilitados
    (tabla `local_models`, V1.0). La SALUD no se comprueba aquí (sería una
    llamada de red por proveedor — rompería el presupuesto <1 ms del Rule
    Engine); la viabilidad real (breaker cerrado) la decide el fallback en la
    ejecución (doc 19 §9.1)."""
    from app.ai.ai_manager import ai_manager

    out: list[ModelRef] = []
    seen: set[str] = set()
    try:
        for entry in ai_manager.list_configured():
            if not entry.get("is_configured"):
                continue
            provider = entry["provider"]
            model = entry.get("model") or ""
            if not model:
                continue
            ref = ModelRef(provider=provider, model=model,
                           is_local=_catalog_is_local(provider, model))
            out.append(ref)
            seen.add(ref.key)
    except Exception as e:
        logger.error(f"[registry] list_available falló: {type(e).__name__}: {e}")

    # [V1.0 multi-modelo local] Cada modelo local habilitado es un candidato
    # PROPIO para el MEL: así "Ornith programa y Qwen conversa" es una decisión
    # real del Rule Engine, no una preferencia teórica. Todos comparten el
    # runtime `ollama`, por eso son (provider="ollama", model=<tag>).
    try:
        for tag in _enabled_local_tags():
            ref = ModelRef(provider="ollama", model=tag, is_local=True)
            if ref.key not in seen:
                out.append(ref)
                seen.add(ref.key)
    except Exception as e:
        logger.error(f"[registry] modelos locales no disponibles: {type(e).__name__}: {e}")
    return out


def _enabled_local_tags() -> list[str]:
    """Tags de `local_models` habilitados. Fail-soft: si la tabla aún no existe
    (BD antigua sin migrar), devuelve vacío y el MEL sigue con lo de siempre."""
    from app.db.database import SessionLocal
    from app.db.models import LocalModel

    db = SessionLocal()
    try:
        rows = db.query(LocalModel).filter(LocalModel.enabled.is_(True)).all()
        return [r.model_tag for r in rows if r.model_tag]
    except Exception:
        return []
    finally:
        db.close()


def get_ref(provider: str) -> Optional[ModelRef]:
    """El ModelRef del proveedor tal como está configurado ahora (su modelo
    actual). None si no está configurado/instanciado."""
    from app.ai.ai_manager import ai_manager

    inst = ai_manager.providers.get(provider)
    if inst is None:
        return None
    model = getattr(inst, "model", "") or ""
    return ModelRef(provider=provider, model=model, is_local=_catalog_is_local(provider, model))


def _instance_for(ref: ModelRef):
    """La instancia de proveedor que atiende ESTE ModelRef. Para los locales, el
    ref puede apuntar a un modelo distinto del que tiene configurado el
    proveedor `ollama` (varios especialistas comparten runtime): en ese caso se
    usa la vista `with_model()` — misma conexión, otro modelo."""
    from app.ai.ai_manager import ai_manager

    inst = ai_manager.providers.get(ref.provider)
    if inst is None:
        raise RuntimeError(f"proveedor no instanciado: {ref.provider}")
    if ref.model and getattr(inst, "model", None) != ref.model:
        with_model = getattr(inst, "with_model", None)
        if callable(with_model):
            return with_model(ref.model)
    return inst


async def execute(ref: ModelRef, prompt: str, system_prompt: Optional[str] = None) -> dict:
    """Ejecuta una petición contra un (proveedor, modelo) CONCRETO — el MEL
    enruta él mismo. Devuelve el dict del proveedor (`{response, model, tokens?,
    error?}`). Lanza si el proveedor no existe (el executor lo trata como fallo y
    salta al siguiente candidato)."""
    inst = _instance_for(ref)
    return await inst.generate(prompt, system_prompt)


async def stream(ref: ModelRef, prompt: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
    """Streaming contra un (proveedor, modelo) concreto — chunks de texto crudos
    (el filtro B21 lo aplica el executor/caller)."""
    inst = _instance_for(ref)
    async for chunk in inst.generate_stream(prompt, system_prompt):
        yield chunk


# ---------------------------------------------------------------------------
# Resolución de nombre (doc 19 §7b.2) — la usa E2b, definida aquí porque es el
# registry quien conoce los (provider, model) reales.
# ---------------------------------------------------------------------------
# Alias coloquiales → nombre de proveedor. Cómo la gente nombra los modelos.
_PROVIDER_ALIASES = {
    "claude": "anthropic", "anthropic": "anthropic", "sonnet": "anthropic", "opus": "anthropic",
    "gpt": "openai", "openai": "openai", "chatgpt": "openai",
    "gemini": "gemini", "google": "gemini",
    "minimax": "minimax",
    "deepseek": "deepseek",
    "grok": "grok", "xai": "grok",
    "openrouter": "openrouter",
    "ollama": "ollama", "local": "ollama", "llama": "ollama",
}


def resolve_model_name(text: str) -> Optional[ModelRef]:
    """Resuelve un nombre coloquial ("GPT-5", "el modelo de OpenAI", "Sonnet")
    al (provider, model) REALMENTE configurado, o None si no hay match. Nunca
    inventa: si el usuario nombra algo que no tiene configurado, devuelve None y
    el caller (TIE) le dice qué SÍ hay (doc 19 §7b.2). Match por, en orden:
      1. el model id exacto de algún proveedor configurado;
      2. el nombre del proveedor / un alias coloquial;
      3. una subcadena del model id."""
    if not text:
        return None
    available = list_available()
    if not available:
        return None
    low = text.strip().lower()

    # 1) model id exacto
    for ref in available:
        if ref.model.lower() == low:
            return ref

    # 2) proveedor o alias (palabra suelta dentro del texto)
    words = set(re.findall(r"[a-z0-9.\-]+", low))
    for alias, provider in _PROVIDER_ALIASES.items():
        if alias in words:
            for ref in available:
                if ref.provider == provider:
                    return ref

    # 3) subcadena del model id (p.ej. "gpt-5" ⊂ "gpt-5.1")
    for ref in available:
        ml = ref.model.lower()
        if low in ml or ml in low:
            return ref

    return None
