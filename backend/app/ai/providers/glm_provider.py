# GLM (Zhipu AI / Z.ai) Provider — API OpenAI-compatible
#
# V1.0: la plataforma abierta de Z.ai sirve los modelos GLM con contrato
# OpenAI Chat Completions.
from .openai_compatible import OpenAICompatibleProvider


class GLMProvider(OpenAICompatibleProvider):
    api_url = "https://api.z.ai/api/paas/v4/chat/completions"
    default_model_name = "glm-5.2"
    provider_id = "glm"
