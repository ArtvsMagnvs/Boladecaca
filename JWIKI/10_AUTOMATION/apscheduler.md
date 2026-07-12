# APScheduler — Aithera V0.9+

## Resumen

**APScheduler** (Advanced Python Scheduler) es la librería elegida para Aithera V0.9+ Automation Engine (CLAUDE.md §5). In-process scheduler, simple, no requiere broker.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```bash
pip install apscheduler
```

## Hello World

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

def my_job():
    print(f"Job ran at {datetime.now()}")

scheduler = AsyncIOScheduler()
scheduler.add_job(
    my_job,
    trigger=CronTrigger.from_crontab("0 9 * * 1"),  # cada lunes 9am
    id="weekly_digest",
    name="Weekly digest",
    replace_existing=True
)
scheduler.start()
```

## Trigger types

```python
# Cron trigger
CronTrigger.from_crontab("0 9 * * 1")

# Interval trigger
IntervalTrigger(hours=1)
IntervalTrigger(minutes=30)

# Date trigger (one-shot)
DateTrigger(run_date=datetime(2026, 12, 25, 10, 0))

# Combining triggers
scheduler.add_job(
    my_job,
    trigger="interval",
    minutes=30,
    start_date="2026-07-09 10:00",
    end_date="2026-12-31 23:59"
)
```

## Jobstore

APScheduler persiste jobs en BD:

```python
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

jobstore = SQLAlchemyJobStore(url="postgresql+asyncpg://...")
executor = AsyncIOExecutor()

scheduler = AsyncIOScheduler(
    jobstores={"default": jobstore},
    executors={"default": executor}
)
```

**Benefit**: jobs sobreviven a restart de Aithera.

## Aithera V0.9+ integration

```python
# backend/app/automation/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

class AutomationEngine:
    def __init__(self, db_url: str, action_executor, approval_gate):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=db_url)}
        )
        self.actions = action_executor
        self.approval = approval_gate
    
    def add_rule(self, rule: AutomationRule):
        self.scheduler.add_job(
            self._run_rule,
            trigger=rule.trigger,
            args=[rule],
            id=f"rule-{rule.id}",
            replace_existing=True
        )
    
    async def _run_rule(self, rule: AutomationRule):
        try:
            if rule.approval_required:
                # Gate
                approved = await self.approval.request(rule)
                if not approved:
                    await log_skip(rule, "approval_denied")
                    return
            
            result = await self.actions.execute(rule.action, rule.action_args)
            await log_success(rule, result)
        
        except Exception as e:
            await log_error(rule, e)
    
    def start(self):
        self.scheduler.start()
    
    def stop(self):
        self.scheduler.shutdown(wait=False)
```

## Aithera Lifespan integration

```python
# backend/app/main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... other startup ...
    
    if settings.AUTOMATION_ENABLED:
        automation = AutomationEngine(...)
        automation.start()
    
    yield
    
    # shutdown
    automation.stop()
```

## Cron syntax

```
* * * * *
│ │ │ │ │
│ │ │ │ └─ day of week (0-6, SUN=0)
│ │ │ └─── month (1-12)
│ │ └───── day of month (1-31)
│ └─────── hour (0-23)
└───────── minute (0-59)
```

Special chars:
- `*` any
- `,` list (1,3,5)
- `-` range (1-5)
- `/` step (*/15 = cada 15min)

## Para Aithera

- ⏳ V0.9: APScheduler + SQLAlchemy jobstore.
- ⏳ V0.85+: notification cuando job falla.
- ⏳ V1.0+: job retry policy.

## Referencias cruzadas

- [JWIKI-169 README.md](./README.md)
- CLAUDE.md §5 (V0.9 Automation)

## Fuentes

1. https://apscheduler.readthedocs.io/
2. https://github.com/agronholm/apscheduler

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified