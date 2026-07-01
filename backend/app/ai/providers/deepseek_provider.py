# DeepSeek AI Provider (OpenAI-compatible Chat Completions API)
from .openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    api_url = "https://api.deepseek.com/chat/completions"
    default_model_name = "deepseek-v3"
    provider_id = "deepseek"
