# FASE 6 — V0.9: Automation Engine
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.9.0
**Prerrequisito**: Aithera V0.8.0 completada (Telegram + Web App funcionando)
**Sesiones**: 2

---

## CONTEXTO

Aithera ejecuta tareas automáticamente según reglas configuradas por el usuario. APScheduler corre dentro del mismo proceso FastAPI — sin broker externo, sin Redis, sin Celery.

---

## SESIÓN 1: Modelos + AutomationEngine + APScheduler

**Tiempo estimado**: 2-3 horas
**Empieza con**: Aithera V0.8.0 funcionando

### Paso 1 — Instalar dependencias

```bash
pip install apscheduler==3.10.4 --break-system-packages
```

Añadir a `backend/requirements.txt`: `apscheduler==3.10.4`

### Paso 2 — Migración Alembic: nuevas tablas

Añadir a `backend/app/db/database.py`:

```python
class AutomationRule(Base):
    __tablename__ = 'automation_rules'
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    description = Column(Text)
    trigger_type = Column(String(50))   # 'cron'|'interval'|'manual'
    trigger_config = Column(Text)       # JSON: {"hour": 8, "minute": 0}
    action_type = Column(String(50))    # 'telegram_message'|'email_summary'|'agent_task'|'chat_query'
    action_config = Column(Text)        # JSON con config de la acción
    is_active = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)
    last_run_at = Column(DateTime)
    run_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class AutomationExecution(Base):
    __tablename__ = 'automation_executions'
    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey('automation_rules.id'))
    status = Column(String(20), default='pending')
    # 'pending'|'approved'|'rejected'|'completed'|'failed'
    trigger_data = Column(Text)    # JSON con datos del trigger
    result = Column(Text)
    error_message = Column(Text)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)
```

Generar y aplicar migración:
```bash
alembic revision --autogenerate -m "add_automation_tables"
alembic upgrade head
```

### Paso 3 — Crear `backend/app/automation/automation_engine.py`

```python
"""
AutomationEngine — Motor de automatizaciones de Aithera.
Usa APScheduler (3.x) con AsyncIOScheduler.

Tipos de trigger:
- cron: {"hour": 8, "minute": 0}
- interval: {"minutes": 30}
- manual: disparo inmediato desde la UI o API

Tipos de acción:
- telegram_message: envía mensaje al bot de Telegram
- email_summary: genera y envía resumen de email por Telegram
- agent_task: asigna una tarea a un agente
- chat_query: envía una query a la IA y opcionalmente manda el resultado por Telegram
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class AutomationEngine:
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._running = False

    async def start(self):
        """Llamado desde el lifespan de FastAPI."""
        self._scheduler.start()
        self._running = True
        # Cargar y registrar todas las reglas activas de la BD
        db = SessionLocal()
        try:
            rules = db.query(AutomationRule).filter(AutomationRule.is_active == True).all()
            for rule in rules:
                self._schedule_rule(rule)
        finally:
            db.close()

    async def stop(self):
        if self._running:
            self._scheduler.shutdown()
            self._running = False

    def _schedule_rule(self, rule: AutomationRule):
        """Registra una regla en APScheduler según su tipo de trigger."""
        config = json.loads(rule.trigger_config or '{}')
        job_id = f"rule_{rule.id}"
        if rule.trigger_type == 'cron':
            self._scheduler.add_job(self._execute_rule, 'cron', id=job_id,
                                    args=[rule.id], replace_existing=True, **config)
        elif rule.trigger_type == 'interval':
            self._scheduler.add_job(self._execute_rule, 'interval', id=job_id,
                                    args=[rule.id], replace_existing=True, **config)

    async def _execute_rule(self, rule_id: int, trigger_data: dict = None):
        """Ejecuta la acción de una regla. Crea registro de ejecución."""
        # 1. Cargar regla de BD
        # 2. Crear AutomationExecution con status='pending'|'approved'
        # 3. Si requires_approval: notificar por Telegram y esperar
        # 4. Si no: ejecutar _run_action() directamente

    async def _run_action(self, rule: AutomationRule, execution_id: int, db):
        """Ejecuta la acción concreta según rule.action_type."""
        # telegram_message: build_message() → bot.send_message()
        # email_summary: EmailTool.list_inbox() → classify() → resumen IA → Telegram
        # agent_task: agent_manager.execute_task()
        # chat_query: ai_manager.chat() → opcionalmente Telegram

    async def activate_rule(self, rule_id: int):
        """Activa una regla y la registra en el scheduler."""

    async def deactivate_rule(self, rule_id: int):
        """Desactiva una regla y la elimina del scheduler."""

    async def trigger_manual(self, rule_id: int):
        """Disparo manual de una regla (para probar desde la UI)."""

    async def approve_execution(self, execution_id: int):
        """Aprueba una ejecución pendiente y la ejecuta."""


automation_engine = AutomationEngine()  # Singleton
```

### Paso 4 — Integrar en el lifespan de FastAPI

```python
from app.automation.automation_engine import automation_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... código existente ...
    await automation_engine.start()
    yield
    await automation_engine.stop()
    # ... shutdown existente ...
```

### Paso 5 — Reglas de ejemplo predefinidas

Insertar en el seed de la BD (en `init_db()` o en el lifespan, solo si la tabla está vacía):

```python
DEFAULT_RULES = [
    {
        "name": "Resumen diario matutino",
        "description": "Envía por Telegram el estado de proyectos y tareas cada mañana a las 8:00",
        "trigger_type": "cron",
        "trigger_config": '{"hour": 8, "minute": 0}',
        "action_type": "telegram_message",
        "action_config": '{"template": "daily_summary"}',
        "is_active": False,  # Desactivada hasta que el usuario la active
    },
    {
        "name": "Resumen de email diario",
        "description": "Envía el resumen de email a las 9:00 (requiere Google conectado)",
        "trigger_type": "cron",
        "trigger_config": '{"hour": 9, "minute": 0}',
        "action_type": "email_summary",
        "action_config": '{}',
        "is_active": False,
    },
]
```

### ✅ Checkpoint Sesión 1 — verificar antes de parar

- [ ] `alembic upgrade head` aplicó las dos tablas nuevas sin errores
- [ ] El backend arranca con APScheduler sin errores
- [ ] Las dos reglas de ejemplo aparecen en la BD (desactivadas)
- [ ] `automation_engine.trigger_manual(1)` ejecuta la regla (probar desde consola Python)
- [ ] Una regla cron con `hour=X, minute=Y` se registra correctamente en el scheduler (verificar con `automation_engine._scheduler.get_jobs()`)

### 🛑 Para aquí

Commit: `feat: AutomationEngine + APScheduler + tablas automation`. La Sesión 2 implementa endpoints y UI.

---

## SESIÓN 2: Endpoints + UI de Automatizaciones

**Tiempo estimado**: 2-3 horas
**Empieza con**: AutomationEngine funcionando

### Paso 1 — Crear `backend/app/api/endpoints/automation.py`

```
GET /api/automation/rules
    Response: lista de todas las reglas con last_run_at y run_count

POST /api/automation/rules
    Body: { name, description, trigger_type, trigger_config, action_type, action_config, requires_approval }
    Response: AutomationRuleResponse

PUT /api/automation/rules/{id}
    Body: campos a actualizar
    Response: AutomationRuleResponse

DELETE /api/automation/rules/{id}
    Response: { "deleted": true }

POST /api/automation/rules/{id}/activate
    Response: { "activated": true }

POST /api/automation/rules/{id}/deactivate
    Response: { "deactivated": true }

POST /api/automation/rules/{id}/trigger
    Response: { "execution_id": int, "status": "pending" }

GET /api/automation/executions
    Query: ?limit=50
    Response: lista de ejecuciones recientes

GET /api/automation/executions/pending
    Response: solo ejecuciones con status='pending'

POST /api/automation/executions/{id}/approve
    Response: { "executing": true }

POST /api/automation/executions/{id}/reject
    Response: { "rejected": true }
```

Registrar en `backend/app/main.py`:
```python
from app.api.endpoints import automation as automation_router
app.include_router(automation_router.router, prefix="/api")
```

### Paso 2 — Crear `frontend/src/pages/Automation.tsx`

**Vista principal**: tabla de reglas con columnas: Nombre, Trigger, Acción, Estado (toggle activo/inactivo), Última ejecución, N.º ejecuciones, Acciones (ejecutar ahora / eliminar).

**Crear nueva regla** (modal):
- Nombre + descripción
- Tipo de trigger (dropdown): Cron / Interval / Manual
  - Si Cron: campos hora y minuto
  - Si Interval: número + unidad (minutos/horas)
- Tipo de acción (dropdown): Mensaje Telegram / Resumen Email / Tarea a Agente / Consulta IA
- Checkbox: "Requiere aprobación antes de ejecutar"

**Sección "Pendientes de aprobación"**: si hay ejecuciones con `status='pending'`, mostrar banner destacado con botones Aprobar / Rechazar.

**Historial de ejecuciones**: últimas 20 ejecuciones con estado, resultado y timestamp.

### Paso 3 — Añadir enlace en el Sidebar

`frontend/src/components/layout/AppLayout.tsx` (o donde esté el Sidebar): añadir `/automation` con icono de reloj/engranaje.

`frontend/src/App.tsx`: registrar la ruta.

### Bump de versión

- `backend/app/main.py`: `version="0.9.0"`
- `backend/app/core/config.py`: `VERSION = "0.9.0"`
- `frontend/package.json`: `"version": "0.9.0"`

### ✅ Checkpoint Sesión 2 — verificar antes de parar

- [ ] `GET /api/automation/rules` devuelve las 2 reglas de ejemplo (desactivadas)
- [ ] Puedo crear una nueva regla cron desde la UI
- [ ] La regla nueva aparece en el scheduler después de activarla
- [ ] `POST /api/automation/rules/{id}/trigger` ejecuta la regla manualmente
- [ ] Una regla de tipo `telegram_message` envía el mensaje al bot de Telegram
- [ ] Una regla con `requires_approval=true` crea una ejecución `pending` en lugar de ejecutar
- [ ] El banner de "Pendientes de aprobación" aparece cuando hay ejecuciones pendientes
- [ ] Aprobar una ejecución desde la UI la ejecuta correctamente
- [ ] El historial de ejecuciones muestra resultado y estado
- [ ] `GET /` devuelve `"version": "0.9.0"`

### 🛑 Para aquí

Aithera V0.9.0 completada. Commit: `feat: V0.9.0 — Automation Engine con APScheduler`.

**Siguiente fase**: `Fase_8_Orchestrator_V10.md`

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Sesión 1**: `backend/app/db/database.py` (AutomationRule + AutomationExecution), `backend/app/automation/__init__.py`, `backend/app/automation/automation_engine.py`, `backend/app/main.py` (lifespan + startup seed), `backend/requirements.txt`, nueva migración Alembic

**Sesión 2**: `backend/app/api/endpoints/automation.py`, `backend/app/main.py` (registrar router + bump v0.9.0), `frontend/src/pages/Automation.tsx`, `frontend/src/components/layout/AppLayout.tsx` (sidebar link), `frontend/src/App.tsx` (ruta), `frontend/package.json`
