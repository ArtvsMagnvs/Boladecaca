# Automation — Overview

## Resumen

Aithera V0.9 introducirá **Automation Engine** con APScheduler + reglas + sistema de aprobaciones (CLAUDE.md §5 "V0.9 Automation Engine"). Comparativa de approaches (APScheduler, Celery, n8n, BullMQ, cron).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Patrones de automation

| Pattern | Use case | Aithera |
|---|---|---|
| **Time-based (cron)** | "Cada lunes 9am, enviar digest" | ✅ APScheduler |
| **Event-based** | "Cuando llegue email de X, archivar" | ✅ rules engine |
| **Webhook-based** | "Cuando GitHub push, notificar" | ⏳ V0.85+ |
| **Manual trigger** | User dice "ahora corre esto" | ✅ |

## Comparativa de engines

| Engine | Type | Pros | Con | Aithera |
|---|---|---|---|---|
| **APScheduler** | Python lib | simple, no broker | single-node | ✅ V0.9 |
| **Celery + beat** | distributed | scalable | Redis/broker | ❌ overkill |
| **Cron** | OS | ubiquitous | syntax limitada | ❌ |
| **BullMQ** | Node.js | moderno | Node-only | ❌ |
| **n8n** | visual | low-code | extra app | ❌ |
| **Temporal** | workflow engine | stateful | pesado | ⏳ V1.5+ |

## Aithera V0.9 design (Plan Maestro 2026 §11)

```python
# Pseudo-código
@automation_engine.rule(
    name="Daily digest",
    trigger="cron: 0 9 * * 1",  # cada lunes 9am
    action="email.digest.send",
    approval_required=False
)
async def weekly_digest():
    return await generate_weekly_digest()
```

## Approval flow

Acciones **sensibles** (enviar email, borrar, ejecutar shell) requieren **approval**:

```python
@automation_engine.rule(
    name="Auto-archive old emails",
    trigger="cron: 0 2 * * *",  # cada día 2am
    action="email.archive",
    approval_required=True  # <- approval gate
)
async def archive_old():
    candidates = await find_old_emails()
    return await request_approval(candidates)
```

## Architecture

```
Trigger (time/event/manual)
  ↓
Rule engine (match pattern)
  ↓
Action executor (with approval gate if sensitive)
  ↓
Audit log + notification
```

## Para Aithera

- ❌ V0.7.3: NO automation engine (solo manual + auto-reply rules).
- ⏳ V0.9: APScheduler + rule engine + approval flow.
- ⏳ V1.5+: Temporal para stateful workflows.

## Referencias cruzadas

- [JWIKI-170 apscheduler.md](./apscheduler.md)
- [JWIKI-174 rules-engines.md](./rules-engines.md)
- [JWIKI-176 approval-flows-automation.md](./approval-flows-automation.md)
- CLAUDE.md §5 (V0.9)

## Fuentes

1. https://apscheduler.readthedocs.io/
2. https://temporal.io/
3. CLAUDE.md §5

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified