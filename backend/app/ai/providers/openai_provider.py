# OpenAI AI Provider
from .openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI API provider (Chat Completions, OpenAI-compatible by definition)."""

    api_url = "https://api.openai.com/v1/chat/completions"
    default_model_name = "gpt-5"
    provider_id = "openai"
