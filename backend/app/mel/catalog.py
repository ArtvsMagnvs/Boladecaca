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


def _scores(chat, classify, extract, summarize, draft, reason, code, analyze,
            vision: int = 40) -> dict:
    """Helper legible: 8 números en el orden de la taxonomía activa. Las
    reservadas (research/agentic) heredan de reason como prior. `vision` es
    opcional (default 40 = "no es multimodal"): solo los modelos de visión
    reales lo suben."""
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
        Capability.VISION: vision,
        Capability.AGENTIC: reason,
    }


# Por PROVEEDOR: perfil por defecto + overrides por modelo concreto. Se consulta
# por (provider, model); si el modelo no está, cae al default del proveedor; si
# el proveedor no está, cae a _UNKNOWN_*.
CATALOG: dict[str, dict] = {
    "ollama": {
        # Calibración honesta (E2, 2026-07-18): un modelo local llama3-class es
        # bueno-suficiente en tareas ESTRUCTURADAS baratas (classify/summarize/
        # extract ≥ umbral Economy 55 → local gana, ahorra coste/latencia) pero
        # genuinamente más flojo en generación ABIERTA (chat/draft/reason/code/
        # analyze < 55 → cloud gana bajo Economy cuando hay uno). Así Economy da
        # el reparto ideal calidad/coste SIN degradar el chat del usuario, en vez
        # de mandarlo todo al local por ser gratis. En Offline (solo local) sigue
        # cubriendo todo — esa política no filtra por umbral (doc 19 §4).
        "default": {"scores": _scores(48, 60, 55, 58, 48, 45, 50, 48),
                    "relative_cost": 0, "is_local": True},
        # [V1.0 modelos locales especializados] El default de arriba describe un
        # llama3-class genérico. Estos overrides describen a los ESPECIALISTAS
        # del catálogo local (app/ai/local_catalog.py) por sus fuerzas reales —
        # y son lo que hace que el reparto del MEL sea de verdad: con Ornith y
        # DeepSeek instalados, `code` va a Ornith y `reason` a DeepSeek sin que
        # el usuario configure nada. Todos coste 0 (locales).
        "models": {
            # — General (Qwen): buen generalista, sin picos —
            "qwen3:8b":  {"scores": _scores(60, 68, 66, 68, 58, 54, 54, 56),
                          "relative_cost": 0, "is_local": True},
            "qwen3:14b": {"scores": _scores(68, 72, 70, 72, 66, 62, 60, 64),
                          "relative_cost": 0, "is_local": True},
            "qwen3:32b": {"scores": _scores(74, 76, 75, 76, 72, 70, 68, 72),
                          "relative_cost": 0, "is_local": True},
            # — Programación (Ornith): pico en code, flojo razonando (el propio
            #   usuario lo describe así; el auto-catálogo E1b puede ajustarlo) —
            "hf.co/deepreinforce-ai/Ornith-1.0-9B-GGUF:Q4_K_M":
                {"scores": _scores(55, 60, 66, 58, 54, 52, 82, 58),
                 "relative_cost": 0, "is_local": True},
            "hf.co/deepreinforce-ai/Ornith-1.0-35B-GGUF:Q4_K_M":
                {"scores": _scores(62, 65, 72, 64, 60, 60, 90, 66),
                 "relative_cost": 0, "is_local": True},
            # — Razonamiento (DeepSeek R1): pico en reason/analyze —
            "deepseek-r1:8b":  {"scores": _scores(58, 62, 64, 62, 56, 72, 62, 70),
                                "relative_cost": 0, "is_local": True},
            "deepseek-r1:14b": {"scores": _scores(62, 66, 68, 66, 60, 80, 68, 78),
                                "relative_cost": 0, "is_local": True},
            "deepseek-r1:32b": {"scores": _scores(68, 70, 72, 70, 66, 86, 74, 84),
                                "relative_cost": 0, "is_local": True},
            # — Visión (Qwen-VL): los ÚNICOS con vision alta; buenos leyendo
            #   documentos/capturas (extract), medianos en el resto —
            "qwen2.5vl:7b":  {"scores": _scores(58, 64, 68, 62, 55, 52, 48, 60, vision=78),
                              "relative_cost": 0, "is_local": True},
            "qwen2.5vl:32b": {"scores": _scores(66, 70, 76, 70, 62, 62, 56, 70, vision=88),
                              "relative_cost": 0, "is_local": True},
        },
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
    # V1.0: Claude via el CLI local del usuario. Calidad de gama alta (es Claude),
    # con dos matices propios de ir por CLI:
    #   - `relative_cost` 20 y NO 90: no se paga por token, va con la suscripcion
    #     que el usuario YA tiene. Bajo Economy sigue siendo caro comparado con un
    #     local gratis, pero mucho mas barato que abrir una API de pago.
    #   - `is_local` False: corre en el equipo, pero NECESITA internet y la sesion
    #     del CLI. Marcarlo local haria que la politica Offline contara con el
    #     estando sin conexion — justo lo que Offline promete evitar.
    # Pico en CODE: es un agente de programacion, no un chat generico.
    "claude_code": {
        "default": {"scores": _scores(88, 82, 86, 88, 88, 90, 94, 88),
                    "relative_cost": 20, "is_local": False},
        "models": {
            "opus":   {"scores": _scores(92, 85, 88, 92, 93, 95, 96, 92),
                       "relative_cost": 30, "is_local": False},
            "haiku":  {"scores": _scores(80, 84, 82, 82, 78, 76, 82, 78),
                       "relative_cost": 10, "is_local": False},
            # `fable` es el modelo rápido de gama alta del CLI: casi calidad de
            # sonnet con menos coste/latencia.
            "fable":  {"scores": _scores(86, 84, 85, 86, 85, 86, 90, 85),
                       "relative_cost": 15, "is_local": False},
        },
    },
    # --- V1.0: proveedores nuevos (2026-07-18) ---
    "kimi": {
        # Kimi destaca en contexto largo y razonamiento; buen generalista.
        "default": {"scores": _scores(84, 82, 84, 86, 82, 85, 82, 85),
                    "relative_cost": 28, "is_local": False},
        "models": {
            "kimi-k3": {"scores": _scores(86, 84, 86, 88, 84, 88, 85, 87),
                        "relative_cost": 35, "is_local": False},
        },
    },
    "glm": {
        # GLM: fuerte en tareas estructuradas y código, coste contenido.
        "default": {"scores": _scores(82, 84, 84, 82, 80, 82, 85, 82),
                    "relative_cost": 22, "is_local": False},
        "models": {
            "glm-5.2-max": {"scores": _scores(86, 86, 87, 86, 84, 87, 89, 86),
                            "relative_cost": 40, "is_local": False},
        },
    },
    "qwen": {
        # Qwen por API (de pago) — distinto de los Qwen locales de Ollama.
        "default": {"scores": _scores(83, 84, 84, 84, 81, 82, 82, 83),
                    "relative_cost": 26, "is_local": False},
        "models": {
            "qwen4.7-max": {"scores": _scores(87, 86, 87, 87, 85, 87, 86, 87),
                            "relative_cost": 42, "is_local": False},
            "qwen-turbo":  {"scores": _scores(74, 78, 76, 76, 72, 70, 72, 73),
                            "relative_cost": 8, "is_local": False},
        },
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
