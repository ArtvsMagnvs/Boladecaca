# Kimi (Moonshot AI) Provider — API OpenAI-compatible
#
# V1.0: Moonshot expone Chat Completions con el mismo contrato que OpenAI, así
# que hereda toda la lógica de request/streaming de OpenAICompatibleProvider.
from .openai_compatible import OpenAICompatibleProvider


class KimiProvider(OpenAICompatibleProvider):
    api_url = "https://api.moonshot.ai/v1/chat/completions"
    default_model_name = "kimi-k3"
    provider_id = "kimi"
