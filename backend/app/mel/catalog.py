# app/mel/catalog.py — scores base por (proveedor, modelo) × capacidad (doc 19 §5.1)
#
# DATO, no código: el prior del que arranca el MEL. Extiende el PROVIDER_CATALOG
# de `app/ai/catalog.py` (que solo tiene labels/modelos) con, por proveedor:
#   - `capability_scores` (0-100 por capacidad): qué tan bueno se ESTIMA que es
#   - `relative_cost` (0-100): 0 = gratis (local), 100 = caro
#   - `is_local`: gobierna Offline/Economy (doc 19 §4)
#
# HONESTIDAD (doc 16, PRINCIPIOS_KARPATHY §1): estos scores son PRIORS CURADOS por
# familia de modelo con conocimiento general a 2026 — NO benchmarks medidos. Es
# exactamente el mismo método con el que hoy se cura el catálogo de proveedores.
# El auto-catálogo de E1b (doc 19 §5.4) los PERSONALIZA por usuario investigando
# cada modelo real conectado; el aprendizaje real (v2) los corrige por uso. Un
# score aquí es un punto de partida razonable, nunca una verdad medida.
from __future__ import annotations

from app.mel.contracts import Capability, ModelRef

# Perfil por defecto cuando un modelo no tiene entrada específica (p.ej. modelos
# dinámicos de Ollama, o el campo libre de OpenRouter): scores medios-bajos
# prudentes — el MEL prefiere un modelo conocido a uno del que no sabe nada.
_UNKNOWN_PROFILE = {
    "scores": {c: 50 for c in Capability},
    "relative_cost": 50,
    "is_local": False,
}

# Perfil por defecto para un modelo local desconocido: coste 0, calidad prudente.
_UNKNOWN_LOCAL_PROFILE = {
    "scores": {c: 45 for c in Capability},
    "relative_cost": 0,
    "is_local": True,
}


def _scores(chat, classify, extract, summarize, draft, reason, code, analyze) -> dict:
    """Helper legible: 8 números en el orden de la taxonomía activa. Las
    reservadas (research/vision/agentic) heredan de reason/analyze como prior."""
    return {
        Capability.CHAT: chat,
        Capability.CLASSIFY: classify,
        Capability.EXTRACT: extract,
        Capability.SUMMARIZE: summarize,
        Capability.DRAFT: draft,
        Capability.REASON: reason,
        Capability.CODE: code,
        Capability.ANALYZE: analyze,
        Capability.RESEARCH: reason,     # research ≈ razonamiento largo (prior)
        Capability.VISION: 40,
        Capability.AGENTIC: reason,
    }


# Por PROVEEDOR: perfil por defecto + overrides por modelo concreto. Se consulta
# por (provider, model); si el modelo no está, cae al default del proveedor; si
# el proveedor no está, cae a _UNKNOWN_*.
CATALOG: dict[str, dict] = {
    "ollama": {
        "default": {"scores": _scores(55, 60, 55, 58, 55, 50, 52, 50),
                    "relative_cost": 0, "is_local": True},
        "models": {},   # llama3 y demás dinámicos usan el default local
    },
    "openai": {
        "default": {"scores": _scores(88, 85, 85, 86, 87, 88, 88, 86),
                    "relative_cost": 75, "is_local": False},
        "models": {
            "gpt-5.2": {"scores": _scores(90, 86, 87, 88, 89, 92, 91, 89),
                        "relative_cost": 85, "is_local": False},
        },
    },
    "anthropic": {
        "default": {"scores": _scores(90, 84, 86, 90, 91, 89, 90, 88),
                    "relative_cost": 78, "is_local": False},
        "models": {
            "claude-opus-4-8": {"scores": _scores(92, 85, 88, 92, 93, 94, 93, 91),
                                "relative_cost": 92, "is_local": False},
        },
    },
    "gemini": {
        "default": {"scores": _scores(86, 84, 85, 85, 84, 85, 84, 86),
                    "relative_cost": 60, "is_local": False},
        "models": {
            "gemini-3.5-flash": {"scores": _scores(82, 86, 84, 84, 80, 78, 80, 82),
                                 "relative_cost": 35, "is_local": False},
        },
    },
    "minimax": {
        "default": {"scores": _scores(82, 80, 78, 82, 84, 80, 72, 76),
                    "relative_cost": 30, "is_local": False},
        "models": {},
    },
    "deepseek": {
        "default": {"scores": _scores(80, 82, 82, 80, 78, 84, 88, 82),
                    "relative_cost": 25, "is_local": False},
        "models": {
            "deepseek-v4-pro": {"scores": _scores(84, 84, 84, 84, 82, 88, 90, 86),
                                "relative_cost": 45, "is_local": False},
        },
    },
    "openrouter": {
        # Campo libre: no sabemos qué modelo servirá → perfil prudente medio.
        "default": {"scores": _scores(70, 70, 70, 70, 70, 70, 70, 70),
                    "relative_cost": 55, "is_local": False},
        "models": {},
    },
    "grok": {
        "default": {"scores": _scores(84, 82, 80, 82, 84, 84, 82, 84),
                    "relative_cost": 65, "is_local": False},
        "models": {},
    },
}


def profile_for(provider: str, model: str) -> dict:
    """Perfil (scores/coste/local) de un (provider, model). Cae al default del
    proveedor, y de ahí al perfil desconocido (local o no según el proveedor)."""
    prov = CATALOG.get(provider)
    if prov is None:
        return _UNKNOWN_PROFILE
    model_override = prov.get("models", {}).get(model)
    if model_override is not None:
        return model_override
    return prov.get("default", _UNKNOWN_PROFILE)


def score_of(ref: ModelRef, capability: Capability) -> int:
    """Score 0-100 de un modelo para una capacidad (el prior del catálogo)."""
    return profile_for(ref.provider, ref.model)["scores"].get(capability, 50)


def cost_of(ref: ModelRef) -> int:
    """Coste relativo 0-100 (0 = local gratis)."""
    return profile_for(ref.provider, ref.model)["relative_cost"]


def is_local(provider: str, model: str = "") -> bool:
    return profile_for(provider, model)["is_local"]
