# Slack — Bolt SDK

## Resumen

**Slack** es plataforma de messaging enterprise. SDK oficial **Bolt** (Python, JS, Java). **NO integrado en Aithera V0.8.0** (solo Telegram).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Slack Bolt setup

```python
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token="xoxb-...", signing_secret="...")

@app.event("message")
def handle_message(event, say):
    user = event["user"]
    text = event["text"]
    
    # Enviar a Aithera Gateway
    response = requests.post("http://localhost:8000/api/aithera", json={
        "channel": "slack",
        "sender_id": user,
        "text": text
    }).json()
    
    say(response["text"])

@app.command("/aithera")
def handle_command(ack, respond, command):
    ack()
    respond(f"Procesando: {command['text']}")

if __name__ == "__main__":
    SocketModeHandler(app, "xapp-...").start()
```

## App + Bot + User tokens

| Token type | Función |
|---|---|
| `xoxb-...` | Bot token (apps) |
| `xoxp-...` | User token (personal) |
| `xapp-...` | App-level token (socket mode) |

## Slack vs Telegram

| Aspecto | Slack | Telegram |
|---|---|---|
| Comandos | `/command` | `/command` |
| Enterprise | ✅ | ❌ |
| Apps/Workflows | ✅ | ❌ |
| Free tier | limited (90 days history) | unlimited |
| Threads | ✅ | ❌ |

## OAuth2

Slack usa OAuth2 standard:

```
https://slack.com/oauth/v2/authorize?
  client_id=...&
  scope=chat:write,im:history,...&
  redirect_uri=...
```

## Slack apps vs Webhooks

- **Webhooks** (incoming): one-way, solo enviar mensajes.
- **Bolt SDK**: full bidirectional, eventos.

Aithera V0.85+ debería usar Bolt SDK para full integration.

## Para Aithera

- ❌ V0.8.0: NO integrado.
- ⏳ V0.85+: Slack support opcional.
- ⏳ V1.0+: Slack Workflows integration (botones interactivos).

## Referencias cruzadas

- [JWIKI-156 telegram-bot.md](./telegram-bot.md)

## Fuentes

1. https://api.slack.com/tools/bolt-python
2. https://api.slack.com/docs

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified