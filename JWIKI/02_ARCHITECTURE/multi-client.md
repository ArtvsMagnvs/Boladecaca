# Multi-Client — Gateway multi-canal (V0.8+)

## Resumen

Aithera V0.8 introduce el patrón **Gateway multi-canal** (inspirado en OpenClaw). El Gateway es channel-agnostic y permite añadir clientes (Telegram, Discord, Slack, WhatsApp) sin tocar la lógica de negocio. El handler central es reemplazable: en V1.0 será el Orchestrator.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Arquitectura Gateway

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Telegram     │    │ Discord      │    │ Slack        │
│ adapter      │    │ adapter      │    │ adapter      │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
              ┌─────────────────────────┐
              │   Gateway               │
              │   - dispatch(envelope)  │
              │   - register(adapter)   │
              │   - chat_message_handler│ (V0.8) → Orchestrator (V1.0)
              └────────────┬────────────┘
                           ▼
              ┌─────────────────────────┐
              │   Aithera Backend       │
              │   (AI + Tools + Memory) │
              └─────────────────────────┘
```

## Componentes V0.8

- **`MessageEnvelope`**: input normalizado (channel, chat_id, user_id, text, attachments).
- **`OutboundMessage`**: output normalizado.
- **`ChannelAdapter`** (ABC): `to_envelope()` + `deliver()`.
- **`Gateway`**: registro + `dispatch()` fail-soft.
- **`chat_message_handler`**: V0.8 usa el mismo handler que `/api/chat`.

## Adaptador Telegram (V0.8 primer adapter real)

```python
# app/gateway/adapters/telegram_adapter.py
from telegram.ext import Application, CommandHandler, MessageHandler

class TelegramAdapter(ChannelAdapter):
    def __init__(self, token: str, allowed_chat_ids: list[str]):
        self.app = Application.builder().token(token).build()
        self.allowed = set(allowed_chat_ids)
        # handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("proyectos", self.cmd_proyectos))
        self.app.add_handler(MessageHandler(filters.TEXT, self.on_message))
    
    async def on_message(self, update, context):
        if str(update.effective_chat.id) not in self.allowed:
            return
        envelope = MessageEnvelope(
            channel="telegram",
            chat_id=str(update.effective_chat.id),
            user_id=str(update.effective_user.id),
            text=update.message.text
        )
        await self.gateway.dispatch(envelope)
```

## Fail-soft semantics

El Gateway **nunca crashea** un canal por un error del handler:
- Handler lanza excepción → mensaje amable al usuario, log con detalle.
- Canal offline → log y retry.
- Auth falla → mensaje "configura el bot".

## V1.0 — Orchestrator reemplaza el handler

```python
# V1.0 (futuro)
gateway.set_handler(orchestrator)  # en vez de chat_message_handler
```

Un solo punto de cambio. **El Gateway no necesita reescribirse para V1.0**.

## Compatibilidad con Electron

El cliente Electron sigue siendo el **cliente principal**:
- No usa el Gateway.
- Llama directamente a FastAPI.
- Auth API key.
- Más rico (UI, 3D).

El Gateway es **adicional**, para canales externos.

## Patrón OpenClaw inspiration

OpenClaw tiene 11+ channels. Aithera V0.8 empieza con 1 (Telegram) y puede crecer.

## Diseño de MessageEnvelope

```python
@dataclass
class MessageEnvelope:
    channel: str            # "telegram" | "discord" | "slack" | ...
    chat_id: str            # identificador del canal
    user_id: str            # identificador del usuario
    text: str               # texto del mensaje
    attachments: list[Attachment] = field(default_factory=list)
    reply_to: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
```

## Canales futuros (roadmap)

| Canal | Prioridad | Adapter |
|---|---|---|
| Telegram | ✅ V0.8 (hecho) | `telegram_adapter.py` |
| Discord | Media V0.85 | `discord_adapter.py` |
| Slack | Baja V1.0 | `slack_adapter.py` |
| WhatsApp | Media V1.0 | `whatsapp_baileys.py` |
| Signal | Baja V1.0+ | `signal_adapter.py` |
| Email (incoming) | Alta V0.85 | `email_adapter.py` |

## Referencias cruzadas

- [JWIKI-046 client-server.md](./client-server.md)
- [JWIKI-055 orchestrator-pattern.md](./orchestrator-pattern.md)
- [JWIKI-156 telegram-bot.md](../09_INTEGRATIONS/telegram-bot.md)
- [JWIKI-007 hermes-agent.md](../01_LANDSCAPE/hermes-agent.md) — inspiration OpenClaw

## Fuentes

1. Aithera V0.8 codebase (`app/gateway/`)
2. `PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md`
3. https://openclaw.io/ — inspiration
4. python-telegram-bot docs

## Nivel de confianza

**90%** — Arquitectura V0.8 documentada en el codebase.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified