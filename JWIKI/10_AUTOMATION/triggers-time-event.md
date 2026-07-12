# Triggers — Time, Event, Webhook, Manual

## Resumen

**Triggers** son los eventos que disparan reglas de automation en Aithera V0.9+. 4 tipos principales: time-based, event-based, webhook-based, manual.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Tipos

### Time-based

```json
{
    "type": "cron",
    "expression": "0 9 * * 1"  // Mondays 9am
}

// o interval
{
    "type": "interval",
    "minutes": 30
}
```

### Event-based

```json
{
    "type": "event",
    "topic": "email.received",
    "filter": "from:boss@..."
}

// Topics posibles
"email.received"
"email.sent"
"calendar.event_created"
"calendar.event_updated"
"agent.execution_completed"
"chat.message_received"
"telegram.message_received"
"memory.item_added"
```

### Webhook-based

```json
{
    "type": "webhook",
    "path": "/api/webhook/external",
    "method": "POST",
    "auth": "hmac"  // HMAC signature verify
}
```

### Manual

```json
{
    "type": "manual",
    "command": "/run-rule weekly-digest",
    "allowed_users": ["user_1"]
}
```

## Filter syntax

```json
// Simple
{"field": "email.from", "op": "==", "value": "boss@company.com"}

// Regex
{"field": "email.subject", "op": "regex", "value": "\\b(URGENT|ASAP)\\b"}

// Multiple (AND)
{
    "type": "and",
    "rules": [
        {"field": "email.from", "op": "regex", "value": "@company\\.com$"},
        {"field": "email.labels", "op": "contains", "value": "IMPORTANT"}
    ]
}
```

## Para Aithera

- ⏳ V0.9: 4 tipos de triggers implementados.
- ⏳ V0.85+: visual trigger builder UI.

## Referencias cruzadas

- [JWIKI-174 rules-engines.md](./rules-engines.md)
- [JWIKI-170 apscheduler.md](./apscheduler.md)

## Fuentes

1. Plan Maestro 2026 §11
2. https://ifttt.com/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified