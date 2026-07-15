# app/gateway/gateway.py — nucleo channel-agnostic (V0.8, patron OpenClaw)
#
# Flujo: canal -> adapter.to_envelope() -> gateway.dispatch() -> handler
#        -> OutboundMessage -> adapter.deliver() -> canal
#
# El handler por defecto es el pipeline de chat (AIManager + memoria), el
# mismo que usa Electron via /api/chat. En V1.0 el handler pasara a ser el
# Orchestrator SIN tocar ni un adapter: esa es la gracia del envelope.

from typing import Awaitable, Callable, Dict, Optional, Union

from app.core.logging_config import get_system_logger
from app.gateway.base import ChannelAdapter
from app.gateway.envelope import MessageEnvelope, OutboundMessage

logger = get_system_logger("gateway")

#: un handler recibe el envelope y devuelve texto u OutboundMessage completo
MessageHandler = Callable[[MessageEnvelope], Awaitable[Union[str, OutboundMessage]]]


class GatewayError(Exception):
    """Errores de configuracion/registro del gateway (no de negocio)."""


async def chat_message_handler(envelope: MessageEnvelope) -> str:
    """Handler por defecto: chat con el proveedor IA activo + memoria del MOS.

    Equivalente channel-agnostic de POST /api/chat (no streaming: Telegram
    y similares no lo necesitan). B21 aplicado: sin razonamiento del modelo.

    [V0.85 M4] Delega en chat_service.answer() — MISMA implementacion que usa
    POST /api/chat (doc 12 A4: antes esta logica estaba duplicada casi entera
    entre este handler y el endpoint). persist_chat_message=False: los
    canales del Gateway no escriben en ChatMessage (historial de la UI de
    escritorio) — comportamiento identico al que ya tenia este handler.
    """
    from app.services import chat_service

    result = await chat_service.answer(
        envelope.text, channel=envelope.channel, persist_chat_message=False
    )
    return result.text or "(sin respuesta)"


class Gateway:
    """Registro de adapters + despacho de envelopes al handler de negocio."""

    def __init__(self, handler: Optional[MessageHandler] = None) -> None:
        self._adapters: Dict[str, ChannelAdapter] = {}
        self._handler: MessageHandler = handler or chat_message_handler

    # -------------------- registro --------------------

    def register(self, adapter: ChannelAdapter) -> None:
        name = (adapter.name or "").strip().lower()
        if not name:
            raise GatewayError("el adapter no declara nombre de canal")
        if name in self._adapters:
            raise GatewayError(f"canal ya registrado: {name!r}")
        self._adapters[name] = adapter
        logger.info(f"[gateway] canal registrado: {name}")

    def adapters(self) -> Dict[str, ChannelAdapter]:
        return dict(self._adapters)

    def set_handler(self, handler: MessageHandler) -> None:
        """V1.0: aqui se enchufara el Orchestrator. Un solo punto de cambio."""
        self._handler = handler

    # -------------------- despacho --------------------

    async def dispatch(self, envelope: MessageEnvelope) -> OutboundMessage:
        """Procesa un envelope y ENTREGA la respuesta por su canal.

        Garantias:
          - canal desconocido -> GatewayError (bug de wiring, debe explotar)
          - authorize() False -> respuesta de rechazo, el handler NI se llama
          - excepcion del handler -> fail-soft: el usuario recibe un error
            amable por su canal y el detalle queda en el log
        """
        adapter = self._adapters.get(envelope.channel)
        if adapter is None:
            raise GatewayError(f"canal no registrado: {envelope.channel!r}")

        if not await adapter.authorize(envelope):
            outbound = OutboundMessage(
                text="No autorizado en este canal.",
                envelope_id=envelope.envelope_id,
                error=True,
                metadata={"reason": "unauthorized"},
            )
            await adapter.deliver(outbound, envelope)
            return outbound

        try:
            result = await self._handler(envelope)
            if isinstance(result, OutboundMessage):
                outbound = result
                outbound.envelope_id = outbound.envelope_id or envelope.envelope_id
            else:
                outbound = OutboundMessage(text=str(result), envelope_id=envelope.envelope_id)
        except Exception as e:  # fail-soft hacia el usuario, detalle al log
            logger.error(f"[gateway] handler fallo para {envelope.channel}: {e!r}")
            outbound = OutboundMessage(
                text="Ha habido un error procesando tu mensaje. Intentalo de nuevo.",
                envelope_id=envelope.envelope_id,
                error=True,
                metadata={"exception": type(e).__name__},
            )

        await adapter.deliver(outbound, envelope)
        return outbound

    # -------------------- push saliente (V0.9) --------------------

    async def notify(self, channel: str, target: Optional[str], message: OutboundMessage) -> bool:
        """Entrega SALIENTE iniciada por el backend, sin envelope entrante (V0.9,
        para el ApprovalGate y futuras notificaciones proactivas).

        Construye un envelope sintético sólo con el destino (`user_ref=target`) y
        llama a `adapter.deliver` — cero cambios en los adapters. El Hub NO es un
        canal del Gateway (su UI sondea por HTTP), así que `channel="hub"` no
        entrega nada aquí y devuelve False, como debe.

        Fail-soft: devuelve False si el canal no está registrado o la entrega
        falla; NUNCA lanza — quien notifica ya hizo su trabajo crítico (p.ej. el
        gate ya persistió la aprobación), esto es best-effort.
        """
        adapter = self._adapters.get((channel or "").strip().lower())
        if adapter is None or not target:
            return False
        try:
            synthetic = MessageEnvelope(channel=channel, user_ref=str(target), text="")
            await adapter.deliver(message, synthetic)
            return True
        except Exception as e:
            logger.error(f"[gateway] notify a {channel!r} falló: {e!r}")
            return False

    # -------------------- ciclo de vida --------------------

    async def start_all(self) -> None:
        """Arranca todos los canales (llamar desde el lifespan en V0.8)."""
        for adapter in self._adapters.values():
            await adapter.start()

    async def stop_all(self) -> None:
        for adapter in self._adapters.values():
            await adapter.stop()


# Singleton (mismo patron que ai_manager / memory_manager). En V0.8 el
# lifespan de main.py registrara los adapters y llamara a start_all().
gateway = Gateway()
