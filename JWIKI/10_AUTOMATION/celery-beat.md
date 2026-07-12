# Celery Beat — Distributed tasks

## Resumen

**Celery Beat** es el scheduler distribuido de Celery. Permite scheduling de tareas en clusters con broker (Redis/RabbitMQ). **NO usado en Aithera** (overkill para single-user desktop).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```bash
pip install celery[redis]
```

```python
# celery_app.py
from celery import Celery
from celery.schedules import crontab

app = Celery("tasks", broker="redis://localhost:6379/0")

app.conf.beat_schedule = {
    "weekly-digest": {
        "task": "tasks.send_weekly_digest",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Mondays 9am
    },
    "archive-old-emails": {
        "task": "tasks.archive_old_emails",
        "schedule": crontab(hour=2, minute=0),  # Daily 2am
    },
}
```

## Start workers + beat

```bash
# Worker
celery -A celery_app worker --loglevel=info

# Beat scheduler (separate process)
celery -A celery_app beat --loglevel=info
```

## Cuándo elegir Celery

- ✅ **Multi-machine**: tareas distribuidas en cluster.
- ✅ **High throughput**: miles de tasks/segundo.
- ✅ **Production-grade**: retry policies, monitoring built-in.
- ❌ Single-user desktop → overkill.

## Para Aithera

- ❌ NO usa Celery (single-user desktop).
- ✅ APScheduler es suficiente.
- ⏳ Si Aithera crece a SaaS: Celery + Redis.

## Referencias cruzadas

- [JWIKI-170 apscheduler.md](./apscheduler.md)

## Fuentes

1. https://docs.celeryq.dev/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified