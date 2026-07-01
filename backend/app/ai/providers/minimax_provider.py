# MiniMax AI Provider
#
# Endpoint y modelos verificados contra la documentacion oficial vigente
# (platform.minimax.io, consultada en junio 2026): la API "chatcompletion_v2"
# antigua vivia en api.minimax.chat/v1/text/chatcompletion_v2 - ese dominio y
# ruta ya NO son los correctos. El endpoint OpenAI-compatible actual es:
#   POST https://api.minimax.io/v1/chat/completions
# con modelos MiniMax-M2.7 / MiniMax-M2.7-highspeed / MiniMax-M2.5 / MiniMax-M2.1.
#
# CONFIGURACION DE API KEY (tres formas, en orden de prioridad):
#   1. Variable de entorno:  MINIMAX_API_KEY=tu_key_aqui  en el archivo .env
#   2. Key hardcodeada:      MINIMAX_HARDCODED_KEY (constante justo abajo)
#   3. UI de Configuracion:  Ajustes → Proveedores de IA → MiniMax → Guardar
import os
from .openai_compatible import OpenAICompatibleProvider

# ─── HARDCODE DIRECTO ─────────────────────────────────────────────────────────
# Para usar directamente sin UI ni .env, pega aquí tu API key de MiniMax
# (obtén una en https://platform.minimax.io → API Keys):
#
MINIMAX_HARDCODED_KEY: str = "sk-cp--sUhQnGSRs1E87N0fYHhcSBLf2HBNbCc8okAp_QabniiF4H9PqIL2oqJkvAcQR9iudLkGueIu7XutfL7347tEpiLPevl31YO6w4nJgpC3R11JatwQwKL9OU"
# ─────────────────────────────────────────────────────────────────────────────

# Resolución automática: env var → hardcoded → vacío (requiere config UI)
_MINIMAX_RESOLVED_KEY: str = (
    os.environ.get("MINIMAX_API_KEY", "")
    or MINIMAX_HARDCODED_KEY
)


class MinimaxProvider(OpenAICompatibleProvider):
    api_url = "https://api.minimax.io/v1/chat/completions"
    default_model_name = "MiniMax-M2.7-highspeed"
    provider_id = "minimax"
    # Documentado en platform.minimax.io: el campo se llama
    # "max_completion_tokens" (no "max_tokens") y su tope es 2048. Pedir
    # 4096 con el nombre generico "max_tokens" es justo lo que causaba el
    # "400 Bad Request" en el chat real (el chequeo de salud no lo detectaba
    # porque ahi se pedia max_tokens=1, dentro de cualquier limite posible).
    max_tokens_param = "max_completion_tokens"
    max_tokens_value = 2048

    def __init__(self, api_key=None, model=None, base_url=None):
        # FIX V0.2: si no se recibe key (p.ej. desde la UI que aún no tiene
        # nada guardado), usar la key resuelta desde env/hardcoded.
        resolved_key = api_key or _MINIMAX_RESOLVED_KEY or None
        super().__init__(api_key=resolved_key, model=model, base_url=base_url)
