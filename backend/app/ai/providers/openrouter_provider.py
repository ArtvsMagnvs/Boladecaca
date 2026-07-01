# OpenRouter AI Provider (OpenAI-compatible Chat Completions API, model
# is whichever string the user picks from OpenRouter's catalog - it is not
# fixed, hence no specific entries in app/ai/catalog.py for this provider).
from .openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    default_model_name = "openrouter/auto"
    provider_id = "openrouter"
