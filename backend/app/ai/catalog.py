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
    "openai": {
        "label": "OpenAI",
        "requires_key": True,
        "default_model": "gpt-5.1",
        "models": ["gpt-5.1", "gpt-5.2", "gpt-5"],
        "supports_auto_detect": False,
    },
    "anthropic": {
        "label": "Anthropic",
        "requires_key": True,
        "default_model": "claude-sonnet-4-6",
        "models": ["claude-sonnet-4-6", "claude-opus-4-8"],
        "supports_auto_detect": False,
    },
    "gemini": {
        "label": "Google Gemini",
        "requires_key": True,
        "default_model": "gemini-3.1-pro-preview",
        "models": ["gemini-3.1-pro-preview", "gemini-3.5-flash"],
        "supports_auto_detect": False,
    },
    "minimax": {
        "label": "MiniMax",
        "requires_key": True,
        "default_model": "MiniMax-M2.7-highspeed",
        "models": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.1"],
        "supports_auto_detect": False,
    },
    "deepseek": {
        "label": "DeepSeek",
        "requires_key": True,
        "default_model": "deepseek-v4-flash",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "supports_auto_detect": False,
    },
    "openrouter": {
        "label": "OpenRouter",
        "requires_key": True,
        "default_model": "",
        "models": [],  # cualquier modelo disponible en OpenRouter; campo libre
        "supports_auto_detect": False,
    },
    "grok": {
        "label": "Grok (xAI)",
        "requires_key": True,
        "default_model": "grok-4.3",
        "models": ["grok-4.3"],
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
