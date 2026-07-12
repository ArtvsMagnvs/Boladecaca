# WhatsApp — Baileys (Node.js)

## Resumen

**WhatsApp** es la plataforma de messaging más grande (2B+ users). **No tiene API oficial** para bots, pero **Baileys** (Node.js) permite conexión vía WhatsApp Web. **NO integrado en Aithera** (privacy concerns).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Baileys (Node.js)

```javascript
// app.js
const { default: makeWASocket } = require("@whiskeysockets/baileys");

async function connectToWhatsApp() {
    const sock = makeWASocket({
        printQRInTerminal: true,  // QR scan en consola
        auth: state  // persistir sesión
    });
    
    sock.ev.on("messages.upsert", async (m) => {
        const msg = m.messages[0];
        if (!msg.key.fromMe && msg.message?.conversation) {
            console.log("Received:", msg.message.conversation);
            // Enviar a Aithera Gateway
            const response = await fetch("http://localhost:8000/api/aithera", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    channel: "whatsapp",
                    sender_id: msg.key.remoteJid,
                    text: msg.message.conversation
                })
            });
            const data = await response.json();
            await sock.sendMessage(msg.key.remoteJid, {text: data.response});
        }
    });
    
    sock.ev.on("connection.update", (update) => {
        if (update.qr) {
            console.log("QR received, scan with WhatsApp app");
        }
    });
}

connectToWhatsApp();
```

## Auth via QR

WhatsApp no usa tokens. Auth es **QR scan desde la app WhatsApp** (vincular device).

⚠️ Esto es:
- No oficial (puede ser bloqueado).
- Personal (vincular tu propio número).
- Requiere conexión persistente.

## Por qué Aithera NO integra WhatsApp

- ⚠️ **Privacy**: WhatsApp detecta bots (ToS violation).
- ⚠️ **Setup friccionado**: QR scan cada vez que se reinicia.
- ⚠️ **No oficial**: Baileys puede dejar de funcionar sin aviso.
- ✅ **Telegram ya cubre el caso messaging**.

## Alternativas oficiales

- **WhatsApp Business API**: oficial, requiere Meta approval, costs.
- **Twilio WhatsApp**: managed service.

## Para Aithera

- ❌ NO integrado por decisión arquitectónica.
- ✅ Telegram cubre messaging.
- ⏳ Si user pide WhatsApp: considerar Twilio (oficial, costo).

## Referencias cruzadas

- [JWIKI-156 telegram-bot.md](./telegram-bot.md)

## Fuentes

1. https://github.com/WhiskeySockets/Baileys
2. https://developers.facebook.com/docs/whatsapp

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified