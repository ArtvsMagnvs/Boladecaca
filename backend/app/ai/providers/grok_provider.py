# Grok (xAI) AI Provider (OpenAI-compatible Chat Completions API)
from .openai_compatible import OpenAICompatibleProvider


class GrokProvider(OpenAICompatibleProvider):
    api_url = "https://api.x.ai/v1/chat/completions"
    default_model_name = "grok-2"
    provider_id = "grok"
