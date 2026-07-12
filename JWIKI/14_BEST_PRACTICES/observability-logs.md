# Observability — Logs estructurados

## Resumen

**Logs estructurados** son la base de debugging + observability. Aithera V0.7.3+ usa structured logging (CLAUDE.md §1).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## structlog setup

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger()

# Uso
logger.info(
    "email_sent",
    user_id=user.id,
    email_id=email.id,
    to=email.to,
    duration_ms=elapsed
)
```

## Output (JSON)

```json
{
    "timestamp": "2026-07-09T14:30:15.123Z",
    "level": "info",
    "event": "email_sent",
    "user_id": 1,
    "email_id": 42,
    "to": "client@example.com",
    "duration_ms": 234
}
```

## Logger estándar (CLAUDE.md §1)

```python
from app.core.logging_config import get_system_logger
logger = get_system_logger()
```

## Log levels

| Level | Use |
|---|---|
| DEBUG | dev only, verbose |
| INFO | significant events |
| WARNING | unexpected but recoverable |
| ERROR | failures |
| CRITICAL | system down |

## Best practices

- ✅ **Structured** (JSON, parseable).
- ✅ **Context** (user_id, request_id, etc.).
- ✅ **No secrets** (redact API keys).
- ✅ **Stack trace on error**.

## Para Aithera

- ✅ V0.7.3: structlog o similar.

## Fuentes

1. https://www.structlog.org/
2. CLAUDE.md §1

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified