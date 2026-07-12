# Integrations — Overview servicios externos

## Resumen

Aithera V0.7.3+ integra múltiples servicios externos (Google, Microsoft, Telegram, GitHub, Notion, Linear). Comparativa de approaches (OAuth2 vs API keys, REST vs GraphQL, polling vs webhooks).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Integraciones activas Aithera V0.7.3

| Servicio | Tipo | Auth | Aithera |
|---|---|---|---|
| **Google Gmail** | Email | OAuth2 + PKCE | ✅ V0.7+ |
| **Google Calendar** | Calendar | OAuth2 + PKCE | ✅ V0.7+ |
| **Telegram** | Messaging | Bot token | ✅ V0.8+ (Gateway) |
| **GitHub** | Code | OAuth2 | ⏳ V1.0+ (skills) |
| **Notion** | Docs | OAuth2 | ⏳ V1.0+ |
| **Linear** | Issues | API key | ⏳ V1.0+ |
| **Microsoft Graph** | Email/Calendar | OAuth2 | ⏳ V1.5+ |
| **Slack** | Messaging | OAuth2 | ⏳ V1.5+ |
| **WhatsApp** | Messaging | QR (Baileys) | ❌ (privacy) |
| **Discord** | Messaging | Bot token | ⏳ V1.5+ |

## Categorías

### Email providers
- **Gmail** (Google) — ✅
- **Outlook** (Microsoft Graph) — ⏳

### Calendar providers
- **Google Calendar** — ✅
- **Outlook Calendar** (Microsoft Graph) — ⏳

### Messaging (multi-canal via Gateway)
- **Telegram** — ✅ V0.8+
- **Discord** — ⏳
- **Slack** — ⏳
- **WhatsApp** — ❌

### Productivity
- **Notion** — ⏳
- **Linear** — ⏳
- **GitHub** — ⏳

## Auth patterns

| Pattern | Pros | Con | Uso |
|---|---|---|---|
| **OAuth2 + PKCE** | standard, seguro | setup complejo | Google, Microsoft |
| **API key** | simple | less secure | Linear, OpenAI |
| **Bot token** | simple | single channel | Telegram, Discord |
| **QR login** | user-friendly | ephemeral | WhatsApp |

## Para Aithera

Aithera V0.7.3 ya implementa **OAuth2 + PKCE** correctamente (Google). Ver [JWIKI-152 google-oauth-flow.md](./google-oauth-flow.md).

V0.8+ añade **Gateway** que abstrae channel-specific details.

## Referencias cruzadas

- [JWIKI-152 google-oauth-flow.md](./google-oauth-flow.md)
- [JWIKI-156 telegram-bot.md](./telegram-bot.md)
- [JWIKI-166 auto-reply-patterns.md](./auto-reply-patterns.md)
- CLAUDE.md §13 (integraciones Google)

## Fuentes

1. https://developers.google.com/identity/protocols/oauth2
2. https://learn.microsoft.com/en-us/graph/
3. https://core.telegram.org/bots/api

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified