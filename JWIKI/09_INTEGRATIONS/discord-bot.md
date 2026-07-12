# Discord Bot — discord.py

## Resumen

**Discord** es plataforma de messaging con servidores, canales, roles. SDK oficial `discord.py`. **NO integrado en Aithera V0.8.0** (solo Telegram). Posible V0.85+.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## discord.py setup

```python
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True  # Privileged intent

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {bot.latency*1000:.2f}ms")

@bot.command()
async def aithera(ctx, *, message: str):
    # Enviar al Gateway de Aithera
    response = await aithera_gateway.dispatch(
        channel="discord",
        sender_id=str(ctx.author.id),
        text=message
    )
    await ctx.send(response)

bot.run("DISCORD_BOT_TOKEN")
```

## Discord vs Telegram

| Aspecto | Discord | Telegram |
|---|---|---|
| Comandos | `!command` | `/command` |
| Permissions | roles + channels | none |
| Servers | miles | uno (groups) |
| Voice channels | ✅ | ✅ |
| Threads | ✅ | ❌ |
| Custom emojis | ✅ | ❌ |

## Slash commands (recomendado Discord 2026)

```python
from discord import app_commands

@bot.tree.command(name="ping", description="Ping Aithera")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

bot.tree.sync()
```

## Channels vs DMs

Discord soporta:
- **DMs**: mensaje directo al user.
- **Server channels**: `#general`, `#support`, etc.
- **Threads**: sub-discusiones dentro de channel.
- **Voice channels**: audio (requiere extra setup).

Aithera se conectaría inicialmente a DMs + un channel específico del server del user.

## Permissions

Bot necesita permisos:
- Send Messages.
- Read Message History.
- Embed Links (si quieres embeds).
- Attach Files.
- Use Slash Commands.

## Bot hosting

Discord bot requiere conexión persistente. Aithera puede:
- ✅ **Polling**: bot activo mientras Aithera está corriendo.
- ❌ **Cloud**: Aithera es local, Discord bot no debería correr 24/7.

## Para Aithera

- ❌ V0.8.0: NO integrado.
- ⏳ V0.85+: Discord bot opcional.
- ⏳ V1.0+: Voice channels (conversación voice).

## Referencias cruzadas

- [JWIKI-156 telegram-bot.md](./telegram-bot.md)
- CLAUDE.md §20

## Fuentes

1. https://discordpy.readthedocs.io/
2. https://discord.com/developers/docs/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified