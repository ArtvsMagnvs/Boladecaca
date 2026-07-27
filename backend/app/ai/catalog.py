# AI Provider Catalog - Fase 2
#
# Catalogo estatico de proveedores y modelos preconfigurados, usado para
# poblar la pantalla "Configuracion -> Modelos IA" (lista de proveedores,
# modelos sugeridos por defecto) y para que el backend sepa que clase de
# proveedor instanciar para cada "provider" guardado en la base de datos.
#
# IMPORTANTE sobre los identificadores de modelo:
# Verificados contra documentacion oficial de cada proveedor en junio 2026
# (antes varios eran simplemente los nombres que el usuario pidio para el
# catalogo, y resultaron desactualizados o incorrectos - p.ej. MiniMax y Grok
# apuntaban a modelos/endpoints que ya no existen, causando que el chat se
# quedara "pensando" sin responder):
# - Anthropic: "claude-sonnet-4-6" y "claude-opus-4-8" (verificado).
# - MiniMax: "MiniMax-M2.7" / "MiniMax-M2.7-highspeed" / "MiniMax-M2.5" /
#   "MiniMax-M2.1" (verificado en platform.minimax.io).
# - DeepSeek: "deepseek-v4-flash" / "deepseek-v4-pro" (verificado en
#   api-docs.deepseek.com; los alias "deepseek-chat"/"deepseek-reasoner"
#   siguen funcionando pero se retiran el 24/07/2026).
# - Grok (xAI): "grok-4.3" (verificado en docs.x.ai; "grok-2" ya no es el
#   modelo recomendado).
# - Gemini: "gemini-3.1-pro-preview" (verificado en ai.google.dev).
# - OpenAI: "gpt-5.1" / "gpt-5.2" / "gpt-5" (verificado; "gpt-5-thinking" no
#   es un model id real - el modo de razonamiento de GPT-5.1+ se controla
#   con el parametro reasoning_effort, no con un nombre de modelo distinto).
# El campo "model" en la UI sigue siendo editable a mano por si algun
# proveedor cambia de nuevo su catalogo.

from typing import Dict, Any

PROVIDER_CATALOG: Dict[str, Dict[str, Any]] = {
    "ollama": {
        "label": "Ollama (Local)",
        "requires_key": False,
        "default_model": "llama3",
        "models": [],  # se autodetectan via GET /api/tags del propio Ollama
        "supports_auto_detect": True,
    },
    # V1.0: Claude via el CLI de Claude Code que el usuario ya tiene logueado.
    # NO requiere API key — la suscripcion Pro/Max no expone una utilizable, pero
    # el CLI si esta autenticado. Ver app/ai/providers/claude_code_provider.py.
    # [2026-07-21] `model_labels`: el VALOR sigue siendo el alias que entiende el
    # CLI (`fable`/`opus`/...), pero la UI muestra el nombre comercial real
    # ("Fable 5", "Opus 4.8"...) — petición del usuario: "haiku,sonnet,opus"
    # a secas no dice qué modelo es de verdad.
    "claude_code": {
        "label": "Claude Code CLI",
        "description": "Plan Pro/Max: sin API key — usa Claude Code desde tu terminal",
        "requires_key": False,
        "default_model": "sonnet",
        "models": ["fable", "opus", "sonnet", "haiku"],
        "model_labels": {
            "fable": "Fable 5 (el más capaz)",
            "opus": "Opus 4.8",
            "sonnet": "Sonnet 5",
            "haiku": "Haiku 4.5 (rápido)",
        },
        "supports_auto_detect": False,
    },
    # V1.0 (2026-07-24): Codex CLI de OpenAI — el gemelo de claude_code para
    # OpenAI. NO requiere API key: se autentica con la sesión de ChatGPT del
    # usuario (`codex login`) o, si se prefiere, con una API key vía el propio CLI
    # (`codex login --with-api-key`). Repo oficial: github.com/openai/codex.
    # [2026-07-25] SÍ se puede elegir modelo — `codex exec --model <id>` (docs
    # oficiales learn.chatgpt.com/docs/models, verificado 2026-07-24). Lista
    # verificada de ids ACTUALES (misma familia que el proveedor "openai"):
    # gpt-5.6-terra/luna, 5.5, 5.4, 5.4-mini. Deliberadamente NO se ofrecen los
    # ids con sufijo "-codex" (p.ej. gpt-5.3-codex): deprecados o rechazados
    # bajo login por ChatGPT. TAMPOCO se ofrece "gpt-5.6-sol" — CONFIRMADO EN
    # VIVO (2026-07-25, `codex exec --model gpt-5.6-sol`, cuenta autenticada):
    # `400 "The 'gpt-5.6-sol' model is not supported when using Codex with a
    # ChatGPT account."` — el flagship exige facturación por API key, no login
    # por ChatGPT (el propio benchmark del MEL ya lo había detectado y excluido
    # solo). `default_model=""` (recomendado) sigue siendo la opción más
    # segura: Codex elige el modelo recomendado de la cuenta si el usuario no
    # fija uno explícito.
    "codex": {
        "label": "Codex CLI (OpenAI)",
        "description": "Incluido en tu plan de ChatGPT (Free/Go/Plus/Pro…): sin API key — usa Codex desde tu terminal (`codex login`)",
        "requires_key": False,
        "default_model": "",
        "models": ["gpt-5.6-terra", "gpt-5.6-luna",
                   "gpt-5.5", "gpt-5.4", "gpt-5.4-mini"],
        "model_labels": {
            "gpt-5.6-terra": "GPT-5.6 Terra (el más capaz vía ChatGPT)",
            "gpt-5.6-luna": "GPT-5.6 Luna (rápido)",
            "gpt-5.5": "GPT-5.5",
            "gpt-5.4": "GPT-5.4",
            "gpt-5.4-mini": "GPT-5.4 mini (barato)",
        },
        "supports_auto_detect": False,
    },
    # [2026-07-21] Catálogo RE-VERIFICADO con búsqueda web (julio 2026):
    # OpenAI: familia GPT-5.6 (Sol/Terra/Luna, GA 9-jul-2026, ids exactos del
    # changelog oficial developers.openai.com) + 5.5 (abril) + 5.4/5.4-mini
    # (marzo). Los gpt-5.1/5.2 anteriores quedaron obsoletos.
    "openai": {
        "label": "OpenAI",
        "requires_key": True,
        "default_model": "gpt-5.6-terra",
        "models": ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna",
                   "gpt-5.5", "gpt-5.4", "gpt-5.4-mini"],
        "model_labels": {
            "gpt-5.6-sol": "GPT-5.6 Sol (el más capaz)",
            "gpt-5.6-terra": "GPT-5.6 Terra (equilibrado)",
            "gpt-5.6-luna": "GPT-5.6 Luna (rápido)",
            "gpt-5.5": "GPT-5.5",
            "gpt-5.4": "GPT-5.4",
            "gpt-5.4-mini": "GPT-5.4 mini",
        },
        "supports_auto_detect": False,
    },
    # Anthropic API: Fable 5 / Opus 4.8 / Sonnet 5 / Haiku 4.5 (jul-2026).
    "anthropic": {
        "label": "Anthropic",
        "requires_key": True,
        "default_model": "claude-sonnet-5",
        "models": ["claude-fable-5", "claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5"],
        "model_labels": {
            "claude-fable-5": "Fable 5 (el más capaz)",
            "claude-opus-4-8": "Opus 4.8",
            "claude-sonnet-5": "Sonnet 5",
            "claude-haiku-4-5": "Haiku 4.5 (rápido)",
        },
        "supports_auto_detect": False,
    },
    # Gemini: 3.5 Flash es el GA actual (detrás de gemini-flash-latest);
    # 3.5 Pro aún no es público (jul-2026).
    "gemini": {
        "label": "Google Gemini",
        "requires_key": True,
        "default_model": "gemini-3.5-flash",
        "models": ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.1-pro-preview"],
        "model_labels": {
            "gemini-3.5-flash": "Gemini 3.5 Flash (actual)",
            "gemini-flash-latest": "Gemini Flash (siempre el último)",
            "gemini-3.1-pro-preview": "Gemini 3.1 Pro (anterior)",
        },
        "supports_auto_detect": False,
    },
    # MiniMax M3 (lanzado 1-jun-2026, verificado en minimax.io): M3 y
    # M3-highspeed, junto a la familia M2.7 anterior.
    "minimax": {
        "label": "MiniMax",
        "requires_key": True,
        "default_model": "MiniMax-M2.7-highspeed",
        "models": ["MiniMax-M3", "MiniMax-M3-highspeed", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
        "model_labels": {
            "MiniMax-M3": "MiniMax M3 (el más potente)",
            "MiniMax-M3-highspeed": "MiniMax M3 highspeed",
            "MiniMax-M2.7": "MiniMax M2.7",
            "MiniMax-M2.7-highspeed": "MiniMax M2.7 highspeed (rápido)",
        },
        "supports_auto_detect": False,
    },
    # DeepSeek V4 (verificado api-docs.deepseek.com): flash y pro; los alias
    # deepseek-chat/reasoner mueren el 24-jul-2026 — no se ofrecen.
    "deepseek": {
        "label": "DeepSeek",
        "requires_key": True,
        "default_model": "deepseek-v4-flash",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "model_labels": {
            "deepseek-v4-flash": "DeepSeek V4 Flash (rápido)",
            "deepseek-v4-pro": "DeepSeek V4 Pro (razonador)",
        },
        "supports_auto_detect": False,
    },
    "openrouter": {
        "label": "OpenRouter",
        "requires_key": True,
        "default_model": "",
        "models": [],  # cualquier modelo disponible en OpenRouter; campo libre
        "supports_auto_detect": False,
    },
    # Grok 4.5 es el flagship desde el 8-jul-2026 (docs.x.ai); build-0.1 para código.
    "grok": {
        "label": "Grok (xAI)",
        "requires_key": True,
        "default_model": "grok-4.5",
        "models": ["grok-4.5", "grok-4.3", "grok-build-0.1"],
        "model_labels": {
            "grok-4.5": "Grok 4.5 (flagship)",
            "grok-4.3": "Grok 4.3",
            "grok-build-0.1": "Grok Build 0.1 (código)",
        },
        "supports_auto_detect": False,
    },
    # --- V1.0: proveedores anadidos a peticion del usuario (2026-07-18) ---
    # Los tres exponen Chat Completions con contrato OpenAI, asi que heredan de
    # OpenAICompatibleProvider sin logica propia.
    # Kimi K3 (16-jul-2026, platform.kimi.ai): flagship k3; k2.7-code para
    # código; k2.6/k2.5 como tier económico. La serie k2 vieja está retirada.
    "kimi": {
        "label": "Kimi (Moonshot)",
        "requires_key": True,
        "default_model": "kimi-k3",
        "models": ["kimi-k3", "kimi-k2.7-code", "kimi-k2.6", "kimi-k2.5"],
        "model_labels": {
            "kimi-k3": "Kimi K3 (flagship)",
            "kimi-k2.7-code": "Kimi K2.7 Code (código)",
            "kimi-k2.6": "Kimi K2.6 (económico)",
            "kimi-k2.5": "Kimi K2.5 (económico)",
        },
        "supports_auto_detect": False,
    },
    # GLM-5.2 (13-jun-2026, Z.ai): el actual; 5.1 anterior.
    "glm": {
        "label": "GLM (Z.ai)",
        "requires_key": True,
        "default_model": "glm-5.2",
        "models": ["glm-5.2", "glm-5.2-max", "glm-5.1"],
        "model_labels": {
            "glm-5.2": "GLM-5.2 (actual)",
            "glm-5.1": "GLM-5.1 (anterior)",
        },
        "supports_auto_detect": False,
    },
    # Qwen POR API (de pago). Distinto de los Qwen LOCALES que corren en Ollama.
    # Flagship actual: Qwen3.7-Max (mayo-2026, API-only); 3.8-Max aún en preview.
    "qwen": {
        "label": "Qwen (API)",
        "requires_key": True,
        "default_model": "qwen3.7-max",
        "models": ["qwen3.7-max", "qwen-max", "qwen-plus", "qwen-turbo"],
        "model_labels": {
            "qwen3.7-max": "Qwen3.7-Max (flagship)",
            "qwen-max": "Qwen Max",
            "qwen-plus": "Qwen Plus",
            "qwen-turbo": "Qwen Turbo (rápido)",
        },
        "supports_auto_detect": False,
    },
}


def get_provider_info(provider: str) -> Dict[str, Any]:
    return PROVIDER_CATALOG.get(provider, {
        "label": provider,
        "requires_key": True,
        "default_model": "",
        "models": [],
        "supports_auto_detect": False,
    })


def list_provider_names():
    return list(PROVIDER_CATALOG.keys())
