# 11 — RFC: Automation Engine (V0.9) y Orchestrator (V1.0)

> **Origen**: `FABLE5_PROMPTS/PROMPT_06_AUTOMATION_ORCHESTRATOR.md` +
> `PROMPT_04_ROADMAP_ADAPTATION.md` (integración con el MOS).
> **Regla fundamental**: el MEJOR DISEÑO posible con la implementación MÍNIMA
> funcional por versión. V1.0 = Aithera completa en modo básico; V1.x potencia;
> V2.0+ lleva al límite. Nada de sobreingeniería pre-V1.0.
>
> **Δ 2026-07-12 — Cognitive Runtime (doc 14)**: la **Parte B es ahora el perfil
> mínimo del TIE (Task Intelligence Engine) — "TIE v1"**. Todo su diseño sigue
> vigente con 3 ajustes: (1) el módulo es `backend/app/tie/` (no
> `app/orchestrator/`); (2) `Plan`/`PlanStep` se formalizan como
> `TaskGraph`/`TaskNode` (doc 14 §3.2 — mismos campos + extensiones opcionales;
> `depends_on` ya lo hacía grafo); (3) el executor V1.0 es el Graph Execution
> Engine en modo lineal (ola de tamaño 1) con checkpoint por transición y
> kill-switch (doc 14 §3.4). La Parte A no cambia; su `AutomationLearner` (Capa 4)
> ES el módulo Learner del doc 15. `EventTrigger` se suscribe a
> `app/core/events.py` (nace en V0.85 M2 — doc 07 §6; spec canónica: doc 17).
> Además, el AE emite `automation.rule_fired` y `approval.requested/resolved`
> (semilla de eventos en 17 §4) — datos que ya tiene al cerrar cada ejecución.

---

## PARTE A — Automation Engine (V0.9)

### A.1 Arquitectura (4 capas, diseño completo; implementación escalonada)

```
backend/app/automation/
├── triggers.py     # Capa 1: Trigger(ABC).evaluate(ctx) -> TriggerEvent | None
├── conditions.py   # Capa 2: Condition(ABC) + And/Or/Not composables
├── actions.py      # Capa 3: Action(ABC).execute(event, ctx, gate) -> ActionResult
├── learner.py      # Capa 4: AutomationLearner (STUB en V0.9 → V1.2)
├── engine.py       # evaluación de reglas + APScheduler + auditoría
└── approval.py     # ApprovalGate (primitivo genérico — lo reusa TODO el sistema)
```

**Triggers** — V0.9 implementa `ScheduleTrigger` (cron/interval) y `EventTrigger`
(reactivo: escucha el job de ingesta del MOS y el triaje de email — NUNCA hace su
propio polling a Gmail/Calendar, P07 §6.2). **[Δ 2026-07-15]** `EventTrigger`
también puede suscribirse a los eventos del WPMS ya emitidos desde V0.87
(`app/core/events.py`, doc 18 §10): `task.created`, `task.status_changed`
(`{task_id, from, to}`), `task.closed`, `milestone.completed`,
`project.progress_changed` — el WPMS "emite y sigue" (doc 18 §10), listo para
que V0.9 se suscriba sin tocar `app/workspace/`. Stubs con interfaz definida:
`ConditionTrigger`, `PatternTrigger` (lo alimentará el LLL, V1.2), `MemoryTrigger`
(V1.2), `WebhookTrigger` (V1.x).

**Conditions** — V0.9: `CooldownCondition`, `TimeWindowCondition` + composición
And/Or/Not (la composición es barata y evita rediseño). Stub: `UserStateCondition`.

**Actions** — V0.9: `TelegramMessageAction` (vía Gateway, no vía bot directo),
`EmailSummaryAction`, `ChatQueryAction`, `AgentTaskAction`. **[Δ 2026-07-15]**
`WorkspaceAction` (crear/cerrar/mover tarea, recordatorio de deadline —
prometida en doc 18 §7 fila "Automation Engine", implementación real aquí):
usa la API pública `app.workspace.workspace_service` (`create`/`update`/
`recompute_project_progress` ya hacen su propio recálculo de progreso y
emiten sus propios eventos, doc 18 §8/§10 — el AE nunca recalcula progreso a
mano). Stubs: `SkillExecutionAction` (V1.1, LSL), `CalendarBlockAction`,
`ChainedRuleAction`, `MemoryUpdateAction` (V1.x). Aislamiento: acción fallida
→ `mem_error` + siguiente.

**Learner** — stub completo en V0.9 (`record_feedback/suggest_new_rule/
suggest_rule_improvement` → NotImplementedError("V1.2")). El feedback SÍ se
captura desde V0.9 vía Decision API (ver A.3) — el Learner de V1.2 nace con datos.

### A.2 ApprovalGate — el primitivo genérico (patrón LangGraph `interrupt()`)

- Cualquier tool/step puede declararse `requires_approval`.
- La ejecución se PERSISTE en estado `waiting_approval` (tabla
  `automation_executions.checkpoint` / `agent_executions.checkpoint_data`) y se
  reanuda o cancela con la respuesta — sobrevive a un reinicio del backend.
- Notificación por el canal de origen vía **Gateway** (Hub toast / Telegram con
  botones ✓/✗) — el gate no sabe de canales (envelope de V0.8).
- La confirmación de envío de email (V0.7) **se migra a este mecanismo** — deja de
  ser caso especial. El diseño del flujo "Responder desde alerta" es el precedente.
- Cada resolución escribe en **Decision API** (`decisions`): así el sistema
  acumula qué aprueba/rechaza el usuario → materia prima del Learner y del LLL.

### A.3 Integración con el MOS (obligatoria, P04 §2)

| Punto | API MOS | Detalle |
|---|---|---|
| `daily_briefing` | `GET /api/memory/briefing` + `context()` | **sin llamadas en caliente a Gmail** — consume lo que la ingesta de V0.85 ya indexó. **[Δ 2026-07-15]** desde V0.87 el mismo JSON trae `workspace` (milestone activo, deadlines, alta prioridad, bloqueos, actividad reciente — `workspace_service.briefing_snapshot`, doc 18 §7): sin llamadas nuevas, la regla `daily_briefing` de V0.9 hereda esos datos gratis |
| Resultado de cada regla | `Memory API.add(type=AUTOMATION)` | historial de automatizaciones |
| Aprobación/rechazo | `Decision API.store_decision()` | aprendizaje de preferencias |
| Error de acción | `Memory API.add(type=ERROR)` | base de errores para el LLL |

### A.4 Reglas predefinidas V0.9 (desactivadas por defecto — HITL)

`daily_briefing` (digest+agenda+tareas → Hub y/o Telegram, hora configurable),
`system_monitor` (backend/BD/proveedores, cooldown 5 min, estilo Mark-XLVII),
`urgent_email_alert` (EventTrigger sobre el triaje: urgente → Telegram),
`email_summary`, `agent_task` (delegación genérica).

### A.5 Modelos + criterios de calidad

Tablas `automation_rules` y `automation_executions` (una migración; ejecuciones con
trigger origen, resultado, duración, si hubo aprobación). Calidad exigida (P06 §4):
trigger nuevo = implementar interfaz, cero cambios en engine; condiciones
composables; acciones aisladas; **idempotencia** (re-evaluar una regla no duplica
efectos — dedup por `(rule_id, event_key)` en ventana); auditoría completa.
APScheduler entra AQUÍ (no antes): los jobs asyncio de V0.85 (ingesta, summarizer)
se migran a APScheduler en un sprint de V0.9 (misma función, mejor gestión).

**[Δ 2026-07-13, hallazgo de cierre de V0.85]** `lifecycle.py` (compactación,
08 RFC-007: dedup semántico + presupuesto `MEMORY_BUDGET_MB` + roll-up) **NO
se construyó en V0.85** — no estaba en la fila M5 de doc 07 §10 (se comprobó
literalmente al cerrar la fase) y quedó fuera a propósito. Este párrafo hablaba
de "migrar" ese job asumiendo que ya existía: es un error de redacción, no una
decisión — corregido aquí. **A2 debe CONSTRUIR `lifecycle.py` primero** (con el
diseño ya completo de 08 RFC-007), y solo entonces llevarlo a APScheduler junto
con ingesta/summarizer. Sin esto, la memoria del MOS crece sin límite.

**[Δ 2026-07-13]** También entra en A2, por ser el mismo tipo de trabajo de
infraestructura (jobs/engine): **httpx con conexiones persistentes** (doc 12
A2 — un `AsyncClient` por proveedor IA, creado lazy y cerrado en shutdown, en
vez de abrir uno nuevo por request). Identificado en la auditoría original
(doc 12), nunca asignado a un sprint concreto hasta ahora — quedaba solo en la
tabla de prioridades de doc 12, sin ningún sprint de este documento
apuntándole. Corregido para que no se pierda.

## PARTE B — Orchestrator (V1.0)

### B.1 Los 6 componentes

```
backend/app/orchestrator/
├── intents.py      # 1. Intent Classifier — SIEMPRE modelo barato (Ollama>MiniMax)
├── enricher.py     # 2. Context Enricher — memory_router.context() ANTES de decidir
├── planner.py      # 3. Task Planner — modelo potente SOLO si requires_planning
├── executor.py     # 4. Execution Engine — ejecuta el plan, persiste estado
├── responder.py    # 5. Response Builder — sintetiza (modelo según complejidad)
├── tracer.py       # 6. Trace & Learn — orchestrator_traces + espejo en MOS
└── runtime.py      # AgentRuntime + NullRuntime (contratos en doc 10)
```

**Intent**: `{type: query|create|execute|automate|conversational, domain[],
requires_planning, requires_tools[], requires_memory, confidence}`. Umbral: si
`confidence < 0.55` → tratar como conversational (fail-safe barato).

**Plan** (serializable SIEMPRE — puede esperar aprobación horas y reanudarse):
`PlanStep {id, description, tool, params, depends_on[], can_parallelize,
approval_required}`. **Regla de tamaño**: preferir 2-3 steps; >5 steps para una
query simple = bug de planificación, no feature (P07 §6.3).

**Execution Engine V1.0**: secuencial (el campo `can_parallelize` existe; el
paralelismo real por olas llega en V1.2). Planning SIN side effects: nada se
ejecuta hasta plan aprobado/completo. Step con `approval_required` → ApprovalGate
(el de V0.9, reusado tal cual). Fallo de step → `mem_error` + degradación graciosa
(devolver lo conseguido + explicación).

**Tracer**: tabla `orchestrator_traces` (intent, modelo usado, plan JSON,
context_query_id, decision_id, steps con timing/tokens, resultado) + espejo
resumido en `Memory API (DECISION)` para que el LLL la analice. Cada plan elegido
→ `Decision API.store_decision(plan, alternativas)`.

### B.2 Flujo completo (el pipeline de V1.0)

```
query → [pre-fetch de contexto en paralelo mientras clasifica]
  [1] enricher.context(query, 800 tok)         (≤300ms; caché 60s por query similar)
  [2] Intent Classifier (barato) + contexto → intent
  [3] conversational/simple → NullRuntime.execute_task() → respuesta   (camino corto)
      complejo → Task Planner (potente) → plan → Decision API
  [4] executor: por step → gate si procede → runtime.execute_task(step, memory, tools, gate)
                → Memory API.add(resultado)
  [5] Response Builder → usuario   [6] tracer.record(todo)
```

**Enganche**: `gateway.set_handler(orchestrator.handle)` — un solo punto, cero
cambios en adapters (diseñado así desde V0.8). El chat de Electron y Telegram pasan
a ser el Orchestrator sin tocarlos.

### B.3 Alcance V1.0 (MVP) vs stubs vs excluido

- **V1.0**: 6 componentes, NullRuntime, routing por complejidad (`fast_model`/
  `smart_model` en Settings), traces completos, Decision API, LLL básico (doc 09),
  camino corto conversational sin planner.
- **Stubs**: HermesRuntime (V1.1), paralelismo (V1.2), backtracking/replan (V1.2),
  plan negotiation (V1.2).
- **Excluido de diseño hasta V2.0+**: natural-language rule creation, self-optimizing
  engine, multi-agent parallelism, predictive pre-loading.

### B.4 Integración AE ↔ Orchestrator

Desde V1.0, **el Orchestrator es el único punto de entrada para tareas no
triviales**: `AgentTaskAction` del Automation Engine delega en él (no en el chat
handler). Ejemplo: email urgente → regla → AgentTaskAction → Orchestrator (intent,
contexto de la persona, plan de 3 steps, gate para notificar) → "Miguel pregunta por
el presupuesto Q3; sueles responderle el mismo día; ¿redacto borrador?".

### B.5 Performance (presupuestos vinculantes — doc 12 §5)

Intent ≤ 500 ms local / 1.5 s cloud; enrichment ≤ 300 ms (pre-fetch + caché);
planning ≤ 3 s; primer feedback al usuario ≤ 1 s (streaming del estado: "analizando →
planificando → paso 1/3..."); gate notificado ≤ 500 ms; trigger eval ≤ 10 ms.

## Sprints

| Fase | Sprint | Contenido |
|---|---|---|
| V0.9 | A1 | ApprovalGate + persistencia/reanudación + migración email-confirm al gate + tests |
| V0.9 | A2 | engine + APScheduler (migrando jobs V0.85) + Schedule/EventTrigger + condiciones + modelos/migración |
| V0.9 | A3 | 4 acciones + reglas predefinidas + UI (lista reglas, historial, aprobaciones pendientes) |
| V0.9 | A4 | integración MOS (briefing sin Gmail caliente, Decision/Error Memory) + idempotencia + cierre (tag v0.9) |
| V1.0 | O1 | contratos (`runtime.py`, doc 10) + Intent Classifier + camino corto + traces |
| V1.0 | O2 | Enricher (pre-fetch+caché) + Planner + Decision API |
| V1.0 | O3 | Executor secuencial + gates + `gateway.set_handler(orchestrator)` |
| V1.0 | O4 | Response Builder + LLL básico + UI aprobación de planes + contratos/perf tests |
| V1.0 | O5 | **cierre MVP**: pulido e2e, auto-start backend (doc 12 B6), instalador beta, tag v1.0 |

---
*Diseño 2026-07-09 (Fable 5). Consume: 07/08 (MOS), 09 (LLL), 10 (AgentRuntime).
El ApprovalGate de A.2 es EL primitivo que reusan Orchestrator, Hermes y skills.*
