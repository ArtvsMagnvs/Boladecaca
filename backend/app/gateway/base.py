# app/gateway/base.py — interfaz que TODO canal debe implementar (V0.8)
#
# Un adapter es una pieza FINA: convierte formatos y entrega mensajes.
# Prohibido meter logica de negocio aqui (eso vive detras del Gateway).
# Guia paso a paso para escribir un adapter (telegram, web...):
# PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md

from abc import ABC, abstractmethod
from typing import Any

from app.gateway.envelope import MessageEnvelope, OutboundMessage


class ChannelAdapter(ABC):
    """Contrato de un canal. Implementaciones previstas en V0.8:
    TelegramAdapter (python-telegram-bot v21, polling) y WebAdapter
    (mismo React build servido por FastAPI). Electron podra migrar
    despues sin prisa (principio 1: no romper lo que funciona)."""

    #: nombre unico del canal ("telegram", "web", ...). Minusculas.
    name: str = ""

    @abstractmethod
    async def to_envelope(self, raw: Any) -> MessageEnvelope:
        """Convierte el mensaje nativo del canal en un MessageEnvelope."""

    @abstractmethod
    async def deliver(self, message: OutboundMessage, envelope: MessageEnvelope) -> None:
        """Entrega la respuesta al usuario por el canal (usa envelope.user_ref)."""

    async def authorize(self, envelope: MessageEnvelope) -> bool:
        """Hook de seguridad POR CANAL (V0.8 hardening). Telegram debe
        sobreescribirlo con la whitelist de chat_id; Web con el PIN/token.
        Default True para canales locales de confianza (localhost)."""
        return True

    async def start(self) -> None:
        """Arranque del canal (p.ej. polling de Telegram). Default: nada."""

    async def stop(self) -> None:
        """Parada limpia. Default: nada."""
