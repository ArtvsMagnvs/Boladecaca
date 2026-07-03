# app/gateway/ — Gateway multi-canal (V0.8, esqueleto creado 2026-07-02)
#
# Diseno completo y guia para escribir adapters:
#   PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md
from app.gateway.envelope import Attachment, MessageEnvelope, OutboundMessage  # noqa: F401
from app.gateway.base import ChannelAdapter  # noqa: F401
from app.gateway.gateway import Gateway, GatewayError, gateway, chat_message_handler  # noqa: F401
