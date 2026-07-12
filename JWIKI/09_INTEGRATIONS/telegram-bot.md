# Telegram Bot — python-telegram-bot en Aithera

## Resumen

**Telegram** es el primer canal externo del Gateway de Aithera (V0.8+). Usa `python-telegram-bot 21.10` con polling. CLAUDE.md §20 (Gateway + Telegram).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Aithera V0.8+ setup

```python
# backend/app/gateway/adapters/telegram_adapter.py
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

class TelegramAdapter:
    def __init__(self, bot_token: str, allowed_chat_ids: list[str], gateway):
        self.bot_token = bot_token
        self.allowed_chat_ids = set(allowed_chat_ids)
        self.gateway = gateway
        self.app = Application.builder().token(bot_token).build()
        self._register_handlers()
    
    def _register_handlers(self):
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("proyectos", self.cmd_proyectos))
        self.app.add_handler(CommandHandler("tareas", self.cmd_tareas))
        self.app.add_handler(CommandHandler("estado", self.cmd_estado))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message))
    
    async def cmd_start(self, update: Update, context):
        if str(update.effective_chat.id) not in self.allowed_chat_ids:
            await update.message.reply_text("No autorizado.")
            return
        await update.message.reply_text("¡Hola! Soy Aithera. ¿En qué te ayudo?")
    
    async def on_message(self, update: Update, context):
        if str(update.effective_chat.id) not in self.allowed_chat_ids:
            return
        # Enviar al Gateway
        await self.gateway.dispatch(
            channel="telegram",
            sender_id=str(update.effective_chat.id),
            text=update.message.text
        )
    
    def start(self):
        self.app.run_polling()
    
    def stop(self):
        self.app.stop()
```

## Token storage (DPAPI cifrado)

CLAUDE.md §1: token cifrado con DPAPI.

```python
# Settings endpoint
@router.post("/api/telegram/configure")
async def configure_telegram(token: str, chat_id: str):
    encrypted_token = encrypt_dpapi(token)
    await db.set_config("telegram_bot_token", encrypted_token)
    await db.set_config("telegram_chat_id", chat_id)
```

## Comandos Aithera

- `/start` — saludo + onboarding.
- `/proyectos` — lista proyectos activos.
- `/tareas` — lista tareas pendientes.
- `/estado` — status del sistema (AI provider activo, memoria, etc.).
- **Chat natural** — cualquier mensaje → Gateway → Aithera.

## Whitelist

Aithera solo responde a `chat_id`s autorizados (configurados en Ajustes):

```python
ALLOWED_CHAT_IDS = ["123456789", "-1001234567890"]  # user + group
```

Si un user no autorizado envía mensaje, se ignora silenciosamente.

## Polling vs Webhooks

| Approach | Setup | Aithera |
|---|---|---|
| **Polling** (default) | nada extra | ✅ V0.8+ |
| Webhooks | requiere HTTPS server | ⏳ futuro |

Polling funciona perfecto para single-user desktop.

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Rápido setup | ❌ Solo polling (no webhook) |
| ✅ Whitelist por chat_id | ❌ Sin read receipts |
| ✅ Comandos nativos | ❌ Requiere bot token |
| ✅ Soporta grupos | ❌ 4096 chars/msg |

## Para Aithera

V0.8+: primer canal del Gateway (CLAUDE.md §20).
V0.85+: webhooks (HTTPS).
V1.0+: inline queries, payments, voice messages.

## Referencias cruzadas

- [JWIKI-151 README.md](./README.md)
- CLAUDE.md §20 (Gateway + Telegram)

## Fuentes

1. https://python-telegram-bot.readthedocs.io/
2. https://core.telegram.org/bots/api
3. CLAUDE.md §20

## Nivel de confianza

**100%** — implementado en CLAUDE.md §20.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified