# 20 — V0.9 Automation Engine + ApprovalGate — Plan de sesiones

> **Qué es**: la traducción del diseño de Fable 5 (doc 11 parte A) a sesiones de
> código **sin decisiones abiertas**. Opus/Sonnet ejecutan, no deciden — las
> decisiones importantes ya las tomó Fable 5 y aquí se describen al detalle.
>
> **Consume**: doc 11·A (diseño), 17 (Event Bus), 08 (RFC-002 APIs / RFC-007
> lifecycle), 12 (auditoría: httpx A2, cooldown A8), 15·§8 (AutomationLearner),
> 18·§7/§10 (WPMS: WorkspaceAction + eventos), 07·§6 (jobs).
>
> **Base**: v0.8.7 (WPMS cerrado). **Objetivo**: tag v0.9.0.
> **Auditado contra el estado REAL del código**, no solo contra los docs.
> **Artefacto visual**: `scratchpad/automation_v09_plan_sesiones.html`.

---

## 0. Qué es y qué NO es V0.9

El Automation Engine es la capa que hace que Aithera actúe sin que se lo pidas
cada vez: reglas *disparador → condición → acción*, con un **ApprovalGate** que
pide permiso antes de cualquier acción con consecuencias. **El AE no contiene
inteligencia** — ejecuta reglas deterministas; el juicio real llega en V1.0
(Orchestrator) y el aprendizaje en V1.1/V1.2 (Learner).

**Los 4 principios (gobiernan cada línea):**
1. **HITL**: toda acción con efectos pasa por el ApprovalGate o nace desactivada.
2. **Idempotencia**: re-evaluar una regla nunca duplica efectos — dedup por
   `(rule_id, event_key)` en ventana.
3. **Aislamiento**: trigger/condición/acción nuevos = implementar la interfaz,
   cero cambios en el engine. Acción que falla → `mem_error` + siguiente.
4. **Sin polling propio**: el AE reacciona a los eventos que ya emiten el MOS y
   el WPMS; nunca sondea Gmail/Calendar.

**Fuera de alcance de V0.9 (no construir, hay hueco reservado):** creación de
reglas en lenguaje natural, motor auto-optimizante, paralelismo multi-agente,
pre-carga predictiva, el **AutomationLearner real** (V1.2 — en V0.9 solo el stub).
El **Orchestrator** es la Parte B del doc 11 → V1.0, no entra aquí.

---

## 1. Deltas desde que se planificó V0.9 (lo crítico)

V0.9 se diseñó **antes** que V0.85 y V0.87. Desde entonces nacieron piezas que el
AE debe consumir y otras sin sprint asignado. **Todos estos deltas ya están
integrados en los sprints de §3** — se listan aquí para no perder ninguno.

| # | Delta | Sprint |
|---|---|---|
| Δ1 | **Eventos del WPMS (V0.87)** ya emitidos en `app/core/events.py`: `task.created`, `task.status_changed`, `task.closed`, `milestone.completed`, `project.progress_changed` (doc 18 §10). El `EventTrigger` se suscribe sin tocar `app/workspace/`. | A2b |
| Δ2 | **WorkspaceAction (V0.87)** prometida en doc 18 §7. Crear/cerrar/mover tarea vía `workspace_service` (que ya recalcula progreso y emite eventos — el AE nunca a mano). | A3 |
| Δ3 | **Briefing con `workspace` (V0.87)**: `GET /api/memory/briefing` ya trae milestone activo/deadlines/bloqueos. `daily_briefing` lo hereda gratis. | A3/A4 |
| Δ4 | **`lifecycle.py` NUNCA se construyó en V0.85** (doc 11 [Δ 2026-07-13]). Sin él la memoria del MOS crece sin límite. A2a lo **construye** (08 RFC-007) antes de llevarlo a APScheduler. | A2a |
| Δ5 | **httpx sin conexiones persistentes (doc 12 A2)**: cada request de IA abre `AsyncClient` nuevo. Nunca asignado a sprint. | A2a |
| Δ6 | **Cooldown del Gateway por `user_ref` (doc 12 A8)**: Telegram sin rate-limit. Se implementa con `CooldownCondition`. | A2a |
| Δ7 | **`chat_service.answer()` ya existe (V0.85 M4)**: `ChatQueryAction` y el delegado de `AgentTaskAction` lo reutilizan, sin duplicar el pipeline. | A3 |
| Δ8 | **El Gateway es request/respuesta**: el gate necesita push. A1 añade `gateway.notify(channel, target, OutboundMessage)` — mínimo, sin tocar adapters. | A1 |
| Δ9 | **Decision API sin `history()`**: `decision_service` tiene store/search/link_outcome; RFC-002 lista también `history`. | A4 |
| Δ10 | **Stub "Automatizaciones" por proyecto** en `ProjectCard.tsx` (W2c). Se rellena con reglas filtradas por `project_id`. | A3 |

---

## 2. Arquitectura del módulo

Módulo nuevo `backend/app/automation/` (no existe hoy). Disciplina modular
(doc 16): API pública en `__init__.py`, fronteras vigiladas por
`test_module_boundaries.py`.

```
backend/app/automation/
├── __init__.py     # API pública del módulo
├── triggers.py     # Capa 1: Trigger(ABC).evaluate(ctx) -> TriggerEvent | None
├── conditions.py   # Capa 2: Condition(ABC).check(event, ctx) -> bool + And/Or/Not
├── actions.py      # Capa 3: Action(ABC).execute(event, ctx, gate) -> ActionResult
├── learner.py      # Capa 4: AutomationLearner (STUB V0.9 -> V1.2)
├── engine.py       # evaluación de reglas + APScheduler + auditoría + idempotencia
├── approval.py     # ApprovalGate (primitivo genérico: AE/Orchestrator/Hermes/skills)
├── scheduler.py    # AsyncIOScheduler singleton (APScheduler)
└── rules_builtin.py # las 5 reglas predefinidas (enabled=False)
```

---

## 3. Esquema (migración 18.ª, aditiva) — se hace en A1

Una sola migración crea todo el esquema de V0.9 (patrón "contratos primero" de
M1/W1). **APLICAR AL POSTGRES REAL EN EL MISMO PASO** (`alembic upgrade head`
con `DATABASE_URL` desactivado para leer el `.env`), verificar recuentos
antes/después — ya van 3 incidentes de "migración probada solo en SQLite y nunca
aplicada al Postgres real". Referencias cross-tabla como `Integer` plano
indexado, NO `ForeignKey` (criterio establecido del proyecto).

| Tabla / columna | Campos clave | Para qué |
|---|---|---|
| `automation_rules` **NEW** | id, name, `enabled`(default False), trigger_type, trigger_config(JSON), condition_config(JSON), action_type, action_config(JSON), `project_id`(ix, nullable), cooldown_s, created_at, updated_at | Definición declarativa. `enabled=False` por defecto (HITL). |
| `automation_executions` **NEW** | id, rule_id(ix), trigger_source, `event_key`(ix), status(ix: ok/failed/skipped/waiting_approval), result(Text), error(Text), `checkpoint`(JSON), duration_ms, approved(bool), created_at | Auditoría. `(rule_id, event_key)` = dedup idempotente. `checkpoint` = estado para reanudar tras aprobación. |
| `approvals` **NEW** | `id`(uuid = gate_id), kind, title, summary, action_type, `action_payload`(JSON), status(ix: pending/approved/rejected/expired), channel, target, decision_id, requested_at, resolved_at, expires_at | Store propio del ApprovalGate (genérico). `action_payload` = clausura serializada que se ejecuta al aprobar. Sobrevive a reinicio. |
| `agent_executions.checkpoint_data` **NEW col** | Column(JSON, nullable) | Aditivo. Para que en V1.0 los planes multi-paso del Orchestrator reanuden con el MISMO gate, sin migración nueva. |

**Nota de diseño (por qué un store propio del gate):** doc 11 §A.2 dice
"persiste en `automation_executions.checkpoint` / `agent_executions.checkpoint_data`".
La tabla `approvals` es el **índice genérico** del gate (para listar aprobaciones
pendientes de cualquier origen sin escanear dos tablas); el `checkpoint` de cada
ejecución guarda el estado de reanudación específico. Así el gate es de verdad
reutilizable por el Orchestrator y Hermes — que es lo que exige "el primitivo que
reusa TODO el sistema".

---

## 4. Sprints

> **A2 se divide en A2a + A2b** por carga: los [Δ 2026-07-13] del doc 11 metieron
> en A2 dos trabajos grandes de infra (construir `lifecycle.py` + httpx
> persistente) que no estaban en el sprint original. Se parte igual que W2→W2a-e
> del bloque anterior: **A2a = infraestructura**, **A2b = motor de reglas**.
> Criterio de producto, no capricho.

### A1 — ApprovalGate + esquema + migración del email-confirm

**Objetivo**: el ApprovalGate es EL cimiento (lo reusan V0.9/V1.0/V1.1). Se
construye primero, con su esquema y su prueba de fuego: sobrevivir a un reinicio
del backend.

**Archivos**: `app/automation/approval.py` (NEW), `__init__.py` (NEW), migración
18 (NEW), `db/database.py`, `db/schemas.py`, `gateway/gateway.py`,
`api/endpoints/automation.py` (NEW), `api/endpoints/email_compose.py`, `main.py`.

**Tareas**:
- **Migración 18**: 3 tablas + columna; aplicar al Postgres real; verificar recuentos.
- **Modelos + schemas**: `AutomationRule`, `AutomationExecution`, `Approval`.
- **`ApprovalGate`** (API congelada):
  - `request_approval(*, kind, title, summary, action_type, action_payload, channel, target) -> gate_id`: escribe `Approval(status="pending")`, notifica por el canal de origen, emite `approval.requested`.
  - `resolve(gate_id, approved, note="") -> ApprovalResult`: si aprobado, reconstruye la acción desde `(action_type, action_payload)` y la ejecuta; escribe en Decision API (`store_decision`); emite `approval.resolved`. Idempotente (doble resolve no re-ejecuta).
  - `list_pending()`, `get(gate_id)`.
  - Registro de ejecutores por `action_type` (dict inyectable) para que A3 enchufe las acciones reales sin que el gate importe `actions.py` (evita ciclo).
- **Gateway push (Δ8)**: `gateway.notify(channel, target, OutboundMessage)` — saliente sin envelope entrante. Telegram → botones ✓/✗; el Hub NO recibe push (sondea `GET /api/automation/approvals`).
- **Endpoints** (`automation.py`, `/api/automation`): `GET /approvals`, `POST /approvals/{gate_id}/resolve`. Registrar router en `main.py`.
- **Migrar el email-confirm**: se conserva el contrato congelado `POST /api/email/send` con `confirmed:true` (camino síncrono "ya confirmado"); los envíos iniciados por agente/automatización pasan por `request_approval(kind="email_send", …)`. El flujo "Responder desde alerta" (V0.7) es el precedente.

**Contrato congelado**: `request_approval` / `resolve` / `list_pending` — mismas
firmas que usarán el executor del Orchestrator (V1.0, se suscribe a
`approval.resolved`) y Hermes (V1.1).

**Tests**: `test_approval_gate.py` (request→pending; resolve aprobado→acción +
`decisions`; rechazado→no ejecuta; **reanudación tras reinicio**; idempotencia;
emisión de eventos). `test_email_contracts.py` sigue en verde.

**Done**: el gate persiste una aprobación, el backend se reinicia, y al resolverla
la acción se ejecuta; suite en verde; migración aplicada al Postgres real.

---

### A2a — Infraestructura de jobs: APScheduler + lifecycle.py + httpx

**Objetivo**: APScheduler entra AQUÍ (no antes) como planificador único; se le
migran los jobs asyncio de V0.85, se construye por fin `lifecycle.py`, y se saldan
dos deudas de infra (doc 12).

**Archivos**: `requirements.txt` (+APScheduler), `app/automation/scheduler.py`
(NEW), `app/memory/lifecycle.py` (NEW), `memory/ingestion.py`,
`memory/summarizer.py`, `main.py`, `core/config.py`, `ai/providers/*.py`,
`ai/ai_manager.py`, `gateway/gateway.py`.

**Tareas**:
- **APScheduler**: añadir a `requirements.txt`; `scheduler.py` crea un
  `AsyncIOScheduler` singleton, arrancado/parado en el `lifespan`.
- **Migrar jobs V0.85**: `ingestion` (email+calendario) y `summarizer` (03:30)
  dejan de ser `asyncio.create_task(_loop(...))` y pasan a `scheduler.add_job`
  (interval / cron). Misma función, mejor gestión. Conservar jitter + try/except.
- **Construir `lifecycle.py`** (Δ4, diseño en 08 RFC-007) — `MemoryLifecycleManager`,
  job nocturno post-summarizer, micro-batch ≤500 items/noche:
  1. dedup semántico (similitud >0.97 mismo tipo → merge conservando metadata más rica);
  2. roll-up (resumen del nivel superior si falta — el diario ya lo hace el summarizer);
  3. prune (borra items cuyo resumen superior ya existe, salvo `pinned=true` / `category=urgente` respondidos);
  4. archive (escribe al vault Markdown antes de podar COLD).
  - Presupuesto `MEMORY_BUDGET_MB` (default 512): si se supera, aprieta ventanas
    (30d→21d…) empezando por el tipo más voluminoso y avisa en el Hub. Cada prune
    escribe una línea en `MemoryJobRun`. Emite `memory.compacted {pruned, merged, tier}`.
  - Políticas: `mem_decision`/`mem_skill` NUNCA se compactan;
    `mem_error`/`mem_automation` detalle 90 días.
- **httpx persistente** (Δ5, doc 12 A2): un `AsyncClient` por proveedor, creado
  lazy y cerrado en shutdown, en vez de `async with httpx.AsyncClient(...)` por
  request. Tocar los 5 providers + el health-check del `ai_manager`. Timeout
  sigue por-request.
- **Cooldown del Gateway** (Δ6, doc 12 A8): rate-limit por `user_ref` en
  `Gateway.dispatch` (reusa `CooldownCondition` de A2b).
- **Settings**: `MEMORY_BUDGET_MB=512`, `MEMORY_LIFECYCLE_HOUR=4`,
  `AUTOMATION_ENABLED=true`.

**Tests**: `test_lifecycle.py` (dedup fusiona; prune respeta `pinned`; presupuesto
aprieta ventanas; `mem_decision` intacta; escribe `MemoryJobRun`).
`test_startup_time.py` sigue en verde (APScheduler no bloquea el arranque).

**Done**: ingesta/summarizer bajo APScheduler; `lifecycle.py` poda un corpus de
prueba respetando pinned y presupuesto; providers reusan conexión; suite en verde.

---

### A2b — Motor de reglas + Triggers + Conditions

**Objetivo**: el corazón del AE. Evalúa reglas con disparadores por horario y por
evento, y condiciones composables. Aún sin acciones reales (eso es A3) — la acción
se resuelve por el registro que A3 rellena.

**Archivos**: `app/automation/engine.py` (NEW), `triggers.py` (NEW),
`conditions.py` (NEW), `core/events.py` (solo suscripción), `main.py`.

**Tareas**:
- **`Trigger(ABC)`** con `evaluate(ctx) -> TriggerEvent | None`:
  - `ScheduleTrigger` (cron/interval) — se registra como job APScheduler (A2a).
  - `EventTrigger` — se suscribe a `app/core/events.py`: `memory.ingested`,
    `email.triaged` (V0.85) **y los del WPMS (Δ1)**: `task.created`,
    `task.status_changed`, `task.closed`, `milestone.completed`,
    `project.progress_changed`. El `event_key` sale del payload (ej. `email_id`,
    `task_id`) para la idempotencia.
  - Stubs con interfaz: `ConditionTrigger`, `PatternTrigger` (LLL, V1.2),
    `MemoryTrigger` (V1.2), `WebhookTrigger` (V1.x).
- **`Condition(ABC)`** con `check(event, ctx) -> bool` + `And/Or/Not`:
  `CooldownCondition` (ventana por `rule_id`), `TimeWindowCondition`. Stub:
  `UserStateCondition`.
- **`engine.py`**: carga reglas `enabled=True`; por cada trigger que dispara,
  evalúa condiciones; si pasan → resuelve la acción por el registro
  `action_type -> executor` (vacío en A2b → escribe `skipped` con motivo). Escribe
  siempre una fila `automation_executions`. **Idempotencia**: antes de actuar,
  comprueba que no exista ya una ejecución `ok` con el mismo `(rule_id, event_key)`
  en la ventana.
- Arrancar el engine en el `lifespan` (tras APScheduler y tras registrar los
  adapters del Gateway).

**Contrato congelado**: `Trigger.evaluate(ctx)`, `Condition.check(event, ctx)` —
trigger/condición nuevos = implementar la interfaz, **cero cambios en el engine**
(P06 §4).

**Tests**: `test_automation_isolation.py` (trigger nuevo no toca el engine; And/Or/Not;
idempotencia; una regla que lanza excepción no mata al engine ni a otras).
`test_event_trigger.py` (emitir `task.closed` dispara la regla suscrita).

**Done**: una regla de horario y una por evento (WPMS) disparan, evalúan
condiciones e idempotencia, y registran su ejecución; suite en verde.

---

### A3 — Acciones + reglas predefinidas + UI

**Objetivo**: 5 acciones reales (aisladas), 5 reglas predefinidas **desactivadas
por defecto**, y la interfaz para ver/activar reglas, ver historial y resolver
aprobaciones pendientes.

**Archivos**: `app/automation/actions.py` (NEW), `rules_builtin.py` (NEW),
`api/endpoints/automation.py`, `frontend/src/pages/Automation.tsx` (NEW),
`lib/api.ts`, `App.tsx`, `Sidebar.tsx`, `Workspace/ProjectCard.tsx`.

**Las 5 acciones** (`Action(ABC).execute(event, ctx, gate) -> ActionResult`):

| Acción | Qué hace · con qué API existente |
|---|---|
| `TelegramMessageAction` | Envía por el Gateway (`gateway.notify`), no por bot directo. |
| `EmailSummaryAction` | Resume el inbox del día vía `email_service` / digest existente. Sin llamada caliente a Gmail. |
| `ChatQueryAction` | Reusa `chat_service.answer()` (Δ7) — mismo pipeline del chat, sin duplicar. |
| `AgentTaskAction` | Delega en `agent_manager.execute`. **Único punto de delegación**: en V1.0 se cambia por `orchestrator.handle` sin tocar nada más (doc 11 §B.4). |
| `WorkspaceAction` (Δ2) | Crear/cerrar/mover tarea, recordatorio de deadline — vía `workspace_service` (que ya recalcula progreso y emite eventos; el AE NUNCA a mano). |

Stubs con interfaz: `SkillExecutionAction` (V1.1), `CalendarBlockAction`,
`ChainedRuleAction`, `MemoryUpdateAction` (V1.x). Toda acción con efectos declara
`requires_approval` → pasa por el gate de A1.

**Las 5 reglas predefinidas** (`rules_builtin.py`, todas `enabled=False`):
- `daily_briefing`: digest + agenda + tareas → Hub y/o Telegram (hora
  configurable). Lee `GET /api/memory/briefing` — ya trae `workspace` (Δ3).
- `system_monitor`: backend/BD/proveedores, cooldown 5 min (estilo Mark-XLVII).
- `urgent_email_alert`: `EventTrigger` sobre `email.triaged` urgente → Telegram.
- `email_summary` · `agent_task` (delegación genérica).

**UI**:
- `Automation.tsx` + ruta `/automation` + ítem en `Sidebar`: lista de reglas
  (toggle activar/desactivar — HITL), historial (`automation_executions`),
  aprobaciones pendientes (`GET /api/automation/approvals` con ✓/✗).
- `api.ts`: tipos + métodos (`getRules`, `toggleRule`, `getExecutions`,
  `getApprovals`, `resolveApproval`).
- **Rellenar el stub por proyecto (Δ10)** en `ProjectCard.tsx`: la sección
  "Automatizaciones" muestra las reglas con `project_id` de ese proyecto.

**Done**: se activa `daily_briefing` desde la UI, dispara a la hora, y (si requiere
aprobación) aparece en pendientes y se resuelve; una `WorkspaceAction` cierra una
tarea real y el progreso se recalcula solo; verificado en vivo contra el backend real.

---

### A4 — Integración MOS + Learner stub + cierre (tag v0.9.0)

**Objetivo**: el AE deja rastro en la memoria (para que el Learner de V1.1/V1.2
nazca con datos), se cierra el contrato de la Decision API, se congela el stub del
AutomationLearner, y se remata el bloque.

**Archivos**: `app/automation/learner.py` (NEW), `engine.py`, `actions.py`,
`services/decision_service.py`, `api/endpoints/automation.py`, `CLAUDE.md`, docs
PLAN_MAESTRO, `main.py`, `config.py`, `package.json`, `.bat`.

**Tareas**:
- **Memoria de automatización/error** (doc 11 §A.3): resultado de cada regla →
  `memory_router.store(type=AUTOMATION)`; acción fallida →
  `memory_router.store(type=ERROR)` (los `MemoryType.AUTOMATION`/`ERROR` ya están
  reservados en `interfaces.py`, solo usarlos).
- **Decision API completa (Δ9)**: añadir `history(...)` a `decision_service`
  (RFC-002 la lista y falta). Cada aprobación/rechazo ya escribe en `decisions`
  desde A1 — verificar que el saldo alimenta al futuro Learner.
- **AutomationLearner stub** (`learner.py`): `record_feedback` /
  `suggest_new_rule` / `suggest_rule_improvement` → `NotImplementedError("V1.2")`.
  Interfaz congelada; el feedback real ya se captura vía Decision API desde V0.9.
- **Eventos del AE**: emitir `automation.rule_fired {rule_id, trigger, ok,
  duration_ms}` al cerrar cada ejecución (doc 17 §4). (`approval.requested/resolved`
  ya en A1, `memory.compacted` ya en A2a.)
- **Idempotencia final**: endurecer el dedup con casos límite (reinicio a mitad de
  ejecución, evento repetido).
- **Cierre**: bump `0.8.7 → 0.9.0` (3 ubicaciones + .bat + CLAUDE.md); auditoría de
  cabos sueltos en PLAN_MAESTRO (marcar V0.9 cerrada; revisar que doc 14/15
  apuntan bien al AE); commit + `git tag v0.9.0` + push.

**Tests**: `test_automation_mos.py` (regla ok escribe `mem_automation`; acción
fallida escribe `mem_error`; aprobación escribe `decisions` y aparece en
`history()`). Suite completa en verde (sin regresión sobre los 260 de v0.8.7 + los
nuevos de A1-A4).

**Done**: el AE deja rastro consultable en MOS/Decision; el stub del Learner tiene
su interfaz; versión 0.9.0 taggeada y subida; CLAUDE.md y PLAN_MAESTRO al día.

---

## 5. Eventos que emite el AE (doc 17 §4)

Metadatos, nunca contenido. Consumidores: el Learner (V1.1), la telemetría/Runtime
Intelligence (V2.0+, vía `subscribe("*")`).

| Evento | Payload | Se emite en |
|---|---|---|
| `automation.rule_fired` | `{rule_id, trigger, ok, duration_ms}` | A4 |
| `approval.requested` | `{gate_id, action}` | A1 |
| `approval.resolved` | `{gate_id, action, resolution}` | A1 |
| `memory.compacted` | `{pruned, merged, tier}` | A2a |

---

## 6. Matriz de conexión futura (cabos que NO se dejan sueltos)

| Pieza de V0.9 | Se conecta con… | Cómo queda preparada ahora |
|---|---|---|
| ApprovalGate | V1.0 Orchestrator · V1.1 Hermes/skills | Contrato congelado en A1; `agent_executions.checkpoint_data` ya existe; executor V1.0 se suscribe a `approval.resolved`. |
| `AgentTaskAction` | V1.0 Orchestrator (doc 11 §B.4) | Único punto de delegación; en V1.0 se cambia `agent_manager.execute` por `orchestrator.handle`. |
| `EventTrigger` | V1.2 PatternTrigger/MemoryTrigger (LLL) | Stubs con interfaz definida; el bus ya transporta los eventos. |
| AutomationLearner (stub) | V1.2 (reglas sugeridas) | Interfaz congelada; feedback ya en `decisions` desde V0.9. |
| `WorkspaceAction` | WPMS (V0.87) — ya vivo | Usa `workspace_service`; el AE nunca recalcula progreso ni emite eventos del WPMS a mano. |
| `automation.rule_fired` + `memory.compacted` | V2.0+ Runtime Intelligence | Ya en el bus; el colector futuro se engancha con `subscribe("*")`. |

**Deuda opcional (doc 12 A5):** `email_processing.py` (1017 líneas) puede
dividirse cuando A2a/A3 toquen la ingesta/email — "cuando se toque, no antes". No
bloquea V0.9.

---

*Plan derivado de doc 11·A (Fable 5, 2026-07-09) + docs 17, 08 (RFC-002/007), 12,
15·§8, 18·§7/§10. Auditado contra el estado REAL del código (v0.8.7), no solo
contra los docs. Regla rectora: el mejor diseño posible con la implementación
mínima funcional. HITL siempre. Sin sobreingeniería pre-V1.0.*
