# Qwen (Alibaba DashScope) Provider — API OpenAI-compatible
#
# V1.0: Qwen por API de pago, DISTINTO de los Qwen locales que corren en Ollama
# (esos van por el proveedor `ollama` como modelos locales). Un mismo nombre de
# familia puede vivir en los dos sitios: por eso la pantalla Inteligencia marca
# explícitamente "(local)" en los que corren en el PC del usuario.
#
# DashScope ofrece un endpoint "compatible-mode" con el contrato de OpenAI.
from .openai_compatible import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    api_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
    default_model_name = "qwen-max"
    provider_id = "qwen"
