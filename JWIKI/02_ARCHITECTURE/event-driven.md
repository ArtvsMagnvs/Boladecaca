# Event-Driven vs Request-Response

## Resumen

**Request-Response** (HTTP) vs **Event-Driven** (message queues, pub/sub). Aithera V0.7.3 es request-response (HTTP API). V0.9 introducirá event-driven para Automation Engine.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Comparativa

| Aspecto | Request-Response | Event-Driven |
|---|---|---|
| **Sincronía** | Sincrónico (request espera response) | Asincrónico (fire & forget) |
| **Latencia** | Baja (ms-seg) | Variable (ms-seg-horas) |
| **Acoplamiento** | Tight (cliente conoce server) | Loose (publisher no conoce subscriber) |
| **Escalabilidad** | Vertical | Horizontal (workers paralelos) |
| **Retry** | Cliente decide | Sistema decide |
| **Idempotencia** | Por request | Por evento (idempotency key) |
| **Debugging** | Stack trace simple | Distributed tracing |
| **Caso de uso** | API interactiva | Tareas async, webhooks, automation |

## Cuando usar Request-Response

- ✅ **API interactiva** (chat, dashboard).
- ✅ **Latencia crítica** (< 200ms).
- ✅ **UI-driven** (frontend llama backend).
- ✅ **Tráfico esporádico**.

## Cuando usar Event-Driven

- ✅ **Tareas largas** (email processing, memory indexing).
- ✅ **Webhooks** (Gmail push notifications).
- ✅ **Automation** (cron + acciones).
- ✅ **Multi-consumer** (varios workers procesan misma cola).
- ✅ **Retry policy** (sistema decide).

## Aithera V0.7.3 — request-response

- FastAPI HTTP API.
- Cliente Electron llama backend.
- Chat usa SSE (semi-event-driven).

## Aithera V0.9 — event-driven

V0.9 introduce **Automation Engine** con APScheduler:
- Cron jobs (time-based triggers).
- Email triggers (when email arrives).
- Calendar triggers (when event X happens).

Patrón event-driven con **APScheduler** + **SQLAlchemy job store**.

## Aithera V1.0 — Orchestrator

V1.0 Orchestrator usa **event-driven interno**:
- Task queue para jobs async.
- Pub/sub para comunicación entre agentes.
- State management con checkpoints.

## Message brokers

| Broker | Latencia | Throughput | Caso de uso |
|---|---|---|---|
| **Redis Streams** | < 1ms | Alto | Lightweight queue |
| **RabbitMQ** | < 5ms | Alto | Standard pub/sub |
| **Apache Kafka** | < 10ms | Muy alto | Event sourcing |
| **AWS SQS** | < 100ms | Alto | Serverless |
| **PostgreSQL LISTEN/NOTIFY** | < 10ms | Medio | DB-integrated |
| **Celery + Redis** | < 5ms | Alto | Python task queue |

Para Aithera V0.9: **APScheduler + asyncio.Queue** (suficiente, sin infra extra).

## Idempotency keys

En event-driven, el mismo evento puede procesarse 2+ veces (retry). Solución:

```python
event = {
    "id": "evt_abc123",  # idempotency key
    "type": "email.received",
    "data": {...}
}

# Antes de procesar, check si ya se procesó
if db.exists("processed_events", event["id"]):
    return  # skip
process(event)
db.insert("processed_events", event["id"])
```

## Para Aithera V0.9

```python
# Pseudo-código del Automation Engine
@scheduler.scheduled_job('interval', minutes=5)
async def check_inbox():
    new_emails = await gmail.list_unread()
    for email in new_emails:
        event = Event(
            id=f"email-{email.id}",
            type="email.received",
            data=email.to_dict()
        )
        await event_queue.put(event)

@event_queue.handler("email.received")
async def process_email(event):
    # triage + respond
    await email_assistant.process(event.data)
```

## Referencias cruzadas

- [JWIKI-046 client-server.md](./client-server.md)
- [JWIKI-049 async-patterns.md](./async-patterns.md)
- [JWIKI-170 apscheduler.md](../10_AUTOMATION/apscheduler.md)
- [JWIKI-055 orchestrator-pattern.md](./orchestrator-pattern.md)

## Fuentes

1. https://martinfowler.com/articles/201701-event-driven.html
2. https://www.enterpriseintegrationpatterns.com/
3. APScheduler docs

## Nivel de confianza

**85%** — Patrones bien establecidos.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified