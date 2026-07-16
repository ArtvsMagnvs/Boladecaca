# 21 — Plan de sesiones detallado: TIE v1 (Task Intelligence Engine) — V1.0

> **Estatus**: plan de trabajo ejecutable, sprint por sprint, del **TIE v1** y
> SOLO del TIE. Deriva de doc 14 (diseño TIE/Cognitive Runtime), doc 11-B
> (Orchestrator = TIE v1, sprints O1-O4), doc 10 (AgentRuntime), doc 16
> (disciplina modular), doc 17 (Event Bus). Mismo rol que el doc 20 tuvo para
> V0.9: aquí las decisiones ya están tomadas (Fable 5 en 14/11-B); esto las
> traduce a tareas concretas para que Opus/Sonnet no tengan que decidir
> arquitectura, solo implementarla.
>
> **Alcance EXCLUSIVO del TIE.** Este documento NO cubre: el **MEL** (doc 19,
> bloque E1-E2 de V1.0 — plan aparte), el **HermesRuntime** (doc 10, V1.1 — plan
> aparte), el **LLL/Learner** (doc 09/15, V1.1 — plan aparte; en V1.0 el TIE solo
> deja los datos que el Learner consumirá), y el **empaquetado MVP-beta** (doc 03
> §5 sprint O5: instalador NSIS, auto-start, onboarding — plan aparte). El TIE es
> el motor cognitivo puro: entender → planificar → ejecutar el grafo → responder.
>
> **Regla heredada (doc 11/14)**: el mejor diseño posible con la implementación
> MÍNIMA funcional. Contratos completos hoy (congelados); código solo el
> necesario para V1.0. Sin sobreingeniería (doc 16).

---

## 1. Auditoría del código real (2026-07-16) — deltas frente a los docs

Antes de planificar, se auditó el estado REAL del repo (v0.9.0). Correcciones a
supuestos de los docs — **críticas para no repetir el patrón "asumir que existe"**
(ya hubo 3 incidentes de migración probada solo en SQLite en el proyecto):

| # | Supuesto del doc | Realidad en el código (v0.9.0) | Consecuencia para el plan |
|---|---|---|---|
| Δ1 | doc 11-B/§B.1: la tabla `orchestrator_traces` con columna `plan` está "ya prevista" | **NO existe** ninguna tabla `orchestrator_traces` ni `orchestrator_*` en `app/db/database.py`. Nunca se creó | **T1 la CREA** con migración Alembic 19.ª (esquema-primero, patrón M1/W1/A1, aplicada al Postgres real en el MISMO paso y verificada) |
| Δ2 | doc 14 §Model Router: `fast_model`/`smart_model` en Settings | **NO existen** en `app/core/config.py` | **T2** añade `TIE_FAST_MODEL`/`TIE_SMART_MODEL` (+ `TIE_CONTEXT_BUDGET_MS`, `TIE_MAX_PARALLEL`, `TIE_ENABLED`) |
| Δ3 | doc 11-B §B.2: `gateway.set_handler(orchestrator.handle)` — un solo punto | **YA existe** `Gateway.set_handler(handler)` (`app/gateway/gateway.py:74`); `MessageHandler = Callable[[MessageEnvelope], Awaitable[Union[str, OutboundMessage]]]` | **T4** hace el switch; `tie.handle` DEBE respetar esa firma exacta (envelope → str \| OutboundMessage) |
| Δ4 | doc 11-B: camino corto reusa el chat actual | `chat_service.answer(message, *, channel, persist_chat_message)` + `ai_manager.chat(message=, system_prompt=)` existen y son el pipeline único (V0.85 M4) | **T1** el camino corto delega en `chat_service.answer()` — cero duplicación; el `chat_message_handler` actual del Gateway es el precedente exacto |
| Δ5 | doc 14 §3.4.4: gates reusan el ApprovalGate de V0.9 | `approval_gate.request_approval(*, kind, title, action_type, action_payload, channel, target)` + `register_executor` + `resolve` + emite `approval.resolved` (`app/automation/approval.py`) | **T3** el executor pide gate con esa firma y se suscribe a `approval.resolved` (via `app/core/events.py`) para reactivar el nodo |
| Δ6 | doc 14 §4.4: el tracer emite `mission.completed` | `app/core/events.py` (`emit`/`subscribe`) existe desde V0.85 M2; el AE ya emite 4 eventos | **T4** el tracer emite `mission.*` por el mismo bus; el Learner (V1.1) se suscribirá |
| Δ7 | doc 14: Decision API registra planes | `decision_service.store_decision(*, title, body, reason, project, impact, mission_id)` + `history(...)` (Δ9 de A4) existen | **T2** el planner registra el plan elegido con `mission_id`; **T3** las aprobaciones de nodo ya escriben decisión vía el gate (A1) |

**Lo que SÍ está listo y el TIE reusa tal cual** (cero trabajo nuevo): el
ApprovalGate persistente/reanudable (V0.9 A1), `app/core/events.py` (bus in-process,
V0.85 M2), `memory_router.context()/search()/store()` con presupuesto de latencia
(MOS V0.85), `decision_service` (V0.85 M1 + A4), `ToolManager` + whitelist (V0.5),
`ai_manager.chat()` (V0.2+), `gateway.set_handler()` + `MessageEnvelope`/
`OutboundMessage` (V0.8), `permission_service` (V0.9 A3b — un nodo con
`approval_required` hereda la auto-resolución por permiso pre-autorizado gratis).

---

## 2. Estructura de código objetivo (doc 14 §3.1)

```
backend/app/tie/                     ← módulo nuevo (no existe hoy)
├── __init__.py     # API pública: tie.handle(envelope), tie.submit_mission(...),
│                   #   contratos. NADA más importable desde fuera (doc 16)
├── contracts.py    # Mission, TaskGraph, TaskNode, NodeState — CONGELADOS (T1)
├── runtime.py      # AgentRuntime(ABC) + NullRuntime + registro {name:runtime} (T1, doc 10)
├── intents.py      # Goal/Intent classifier (barato-siempre) + camino corto (T1)
├── tracer.py       # traces + espejo Decision API + eventos mission.* (T1 base, T4 eventos)
├── enricher.py     # Context Builder → MOS context() con presupuesto de latencia (T2)
├── router.py       # Model Router mínimo (fast/smart) — shim que el MEL absorbe en E1 (T2)
├── planner.py      # Planner → TaskGraph validado por schema (T2)
├── graph.py        # validación DAG (Kahn) + ready-set — el motor propio (T2)
├── executor.py     # loop de olas (tamaño 1) + checkpoint + gates + recovery + kill-switch (T3)
├── responder.py    # Response Builder → OutboundMessage (T4)
└── missions.py     # Mission Manager (V1.2; en V1.0 solo la dataclass, misión implícita) (T1)
```

Disciplina modular (doc 16): API pública SOLO en `__init__.py`; fronteras vigiladas
por `test_module_boundaries.py` extendido (`app.tie.contracts/.runtime/.intents/...`
internos). Igual que MOS/WPMS/Automation.

---

## 3. Sprints T1-T5

### T1 — Esqueleto + contratos congelados + runtime + Intent + camino corto + tracer base

**Objetivo**: el TIE existe como módulo con sus contratos CONGELADOS, el runtime
inyectable (NullRuntime), la clasificación de intención barata, y el camino corto
funcionando de punta a punta (chat conversational/simple → NullRuntime → respuesta)
**sin tocar todavía el Gateway** (el switch es T4). Se crea la tabla de trazas real.

**Archivos**: `app/tie/__init__.py` (NEW), `contracts.py` (NEW), `runtime.py`
(NEW), `intents.py` (NEW), `tracer.py` (NEW, base), `missions.py` (NEW, solo
dataclass), `app/core/config.py` (MOD: `TIE_ENABLED`), `alembic/versions/*_v10_tie_traces.py`
(NEW, migración 19.ª), `app/db/database.py` (MOD: modelo `OrchestratorTrace`),
`tests/test_tie_contracts.py` (NEW), `tests/test_module_boundaries.py` (MOD).

**Tareas**:
- **`contracts.py` CONGELADO** (doc 14 §3.2 literal): `NodeState` (enum, 9 estados:
  PENDING/READY/RUNNING/WAITING_APPROVAL/WAITING_EVENT/DONE/FAILED/SKIPPED/CANCELLED),
  `TaskNode` (identidad+grafo+necesidades+presupuestos+control+estado/resultado —
  todos los campos, cada uno con su versión de activación en comentario),
  `TaskGraph` (id, mission_id, nodes dict, created_by, state), `Mission` (id, goal,
  source, channel, state, graph_ids, presupuestos, outcome, reflection_id). Regla:
  campos no activos con default; nadie los lee hasta su versión. Serializables a
  JSON (dataclasses + helper `to_dict`/`from_dict`).
- **`runtime.py`** (doc 10 §1): `AgentRuntime(ABC)` con `execute_task`/`stream_task`/
  `health_check`/`capabilities`; contratos `AgentTask`/`AgentResult`/`AgentChunk`/
  `RuntimeHealth`. `NullRuntime` (capabilities `{"chat","tool_use_basic"}`):
  `execute_task` delega en `chat_service.answer()` + ejecución simple de una tool
  vía `ToolManager` si el nodo la pide. Registro `_RUNTIMES: dict[str, AgentRuntime]`
  + `get_runtime(name)` + `register_runtime(name, rt)` (el "Agent Factory" = un dict,
  doc 14 §3.1). NullRuntime registrado como `"null"` al importar.
- **`intents.py`**: `classify(text, context) -> Intent` con modelo BARATO (via
  `router.fast()` — en T1 hardcode al proveedor activo, T2 lo hace política).
  `Intent {type: query|create|execute|automate|conversational, domain[],
  requires_planning, requires_tools[], requires_memory, confidence}`. Umbral:
  `confidence < 0.55` → forzar `conversational` (fail-safe barato, doc 11 B.1).
  Salida validada por schema (patrón 9). **Camino corto**: si `conversational` o
  (`query` simple sin `requires_planning`) → `NullRuntime` → respuesta. ~80% de
  queries NUNCA ven el planner (doc 14 §6).
- **`tracer.py` (base)**: modelo `OrchestratorTrace` (tabla `orchestrator_traces`) —
  columnas: `id` (uuid), `mission_id`, `channel`, `intent` (JSON), `model_used`,
  `plan` (JSON, el TaskGraph serializado — se actualiza en cada transición desde
  T3), `context_query_id`, `decision_id`, `steps` (JSON con timing/tokens),
  `result`, `outcome`, `created_at`, `updated_at`. `record_start(mission)` /
  `record_intent(...)` / `update_graph(graph)` / `record_end(outcome)`. El espejo
  Decision API + eventos `mission.*` se cablean en T2/T4 (aquí solo la base).
- **Migración 19.ª** (Δ1, esquema-primero): crea `orchestrator_traces`. Aditiva e
  idempotente. **Aplicada al Postgres real en el MISMO paso** (`alembic upgrade
  head` con `DATABASE_URL` real) y verificada con recuentos — la lección dura.
- **`missions.py`**: en V1.0 la misión es implícita (1 query compleja = 1 misión =
  1 grafo = 1 trace). Solo se expone `Mission` (dataclass) y un helper
  `new_mission(goal, source, channel)`. Tabla `missions` = V1.2 (no ahora).
- **`__init__.py`**: API pública `handle` (stub que en T1 solo hace el camino corto;
  T4 lo completa), `submit_mission` (stub), `NullRuntime`, `register_runtime`,
  `get_runtime`, contratos. `__all__` explícito.
- **`config.py`**: `TIE_ENABLED` (bool, default True — permite apagar el TIE y
  volver al `chat_message_handler` legacy si algo va mal en beta).

**Tests** (`test_tie_contracts.py`): contratos serializan/deserializan (round-trip
JSON), `NodeState` completo, intent classifier clasifica conversational vs complejo
(con `ai_manager` fake por monkeypatch — sin credenciales en CI), umbral 0.55 fuerza
conversational, camino corto responde delegando en `chat_service.answer()`,
NullRuntime ejecuta una tarea trivial, registro de runtimes. `test_module_boundaries`:
`app.tie.*` internos, barrel completo.

**Done**: el módulo `app/tie/` existe con contratos congelados; el camino corto
responde a un chat simple end-to-end (verificado con `ai_manager` real en un script);
la tabla `orchestrator_traces` existe en el Postgres real; suite verde. El Gateway
NO usa todavía el TIE (sigue en `chat_message_handler` — el switch es T4).

**Modelo sugerido**: **Opus · Alto** (contratos congelados de 10 años — deben
quedar bien a la primera; migración real).

---

### T2 — Enricher + Router (mínimo) + Planner + Graph (validación DAG)

**Objetivo**: dado un intent complejo, el TIE construye contexto (con presupuesto
de latencia), elige modelo potente, y el Planner emite un **TaskGraph validado por
schema** que `graph.py` valida como DAG (sin ciclos, ids/tools consistentes) antes
de que nada se ejecute. Cero side effects (planificar jamás ejecuta, regla 11-B).

**Archivos**: `app/tie/enricher.py` (NEW), `router.py` (NEW), `planner.py` (NEW),
`graph.py` (NEW), `config.py` (MOD: `TIE_FAST_MODEL`/`TIE_SMART_MODEL`/
`TIE_CONTEXT_BUDGET_MS`), `tracer.py` (MOD: espejo Decision API), `tests/test_tie_planner.py`
(NEW), `tests/test_tie_graph.py` (NEW).

**Tareas**:
- **`enricher.py`**: `enrich(query, memory_types=None) -> str` → `memory_router.context()`
  con **presupuesto de latencia DURO** (`asyncio.wait_for(..., TIE_CONTEXT_BUDGET_MS/1000)`,
  default 300 ms — mismo patrón que `chat_service` M4; si excede, contexto vacío,
  el TIE nunca espera). Pre-fetch: el enricher se lanza EN PARALELO con `intents.classify`
  (doc 11 B.2 — `asyncio.gather`), no en serie. Caché 60 s por query similar (dict
  con TTL, sin dependencias). Por-nodo: `node.context_query` + `node.memory_types`.
- **`router.py` (MÍNIMO)**: `fast() -> model_id` / `smart() -> model_id` /
  `choose(node, intent) -> model_id` (respeta `node.model_hint`). Lee
  `TIE_FAST_MODEL`/`TIE_SMART_MODEL` de Settings (Δ2); si vacío, cae al proveedor
  activo del `ai_manager`. Salud vía `ai_manager.health_check()` (cacheado).
  **[Δ doc 19] Diseñado como shim**: `router.py` es una fachada de ~30 líneas para
  que el bloque E1 del MEL (plan aparte) lo convierta en `mel.complete(capability=...)`
  con un cambio de una línea — el TIE conserva su API interna (`router.smart()`), el
  MEL absorbe la política. NO se construye el MEL aquí.
- **`planner.py`**: `plan(goal, intent, context) -> TaskGraph` con modelo POTENTE
  (`router.smart()`). Prompt que pide un grafo de **2-3 nodos** (regla de tamaño:
  >5 para query simple = bug del planner, doc 14 §3.2). Salida del LLM validada
  contra **schema Pydantic** (patrón 9: toda frontera LLM devuelve JSON validado).
  Grafo inválido (schema o validación DAG de `graph.py`) → **1 reintento** del
  planner con el error como feedback → si vuelve a fallar, degradar a camino corto
  + avisar (nunca romper, regla 11-B). Registra el plan elegido en Decision API:
  `decision_service.store_decision(title=goal, body=plan_resumen, reason="plan TIE",
  mission_id=..., impact=...)` + alternativas si las hubo.
- **`graph.py` (el motor propio, doc 14 §1.5/§3.4.1)**: `build(nodes) -> TaskGraph`
  + `validate(graph)`: (1) **Kahn/topological** para detectar ciclos (~40 líneas,
  dict + in-degree, SIN NetworkX), (2) `depends_on` solo a ids existentes, (3)
  `tools` de cada nodo ⊆ catálogo del `ToolManager`, (4) schema Pydantic válido.
  `ready_set(graph) -> list[TaskNode]` = nodos PENDING con todas sus `depends_on`
  en DONE (lo consume el executor en T3). Presupuesto: validación < 10 ms (doc 14 §6).
- **`tracer.py` (MOD)**: `record_plan(decision_id, graph)` — escribe el `plan` JSON
  y enlaza el `decision_id`.

**Tests** (`test_tie_planner.py` + `test_tie_graph.py`): grafo válido de 2-3 nodos
pasa; grafo con ciclo se rechaza (Kahn); nodo con tool inexistente se rechaza; nodo
con `depends_on` a id inexistente se rechaza; planner reintenta 1 vez ante grafo
inválido y degrada si vuelve a fallar (con `ai_manager` fake que devuelve primero
un grafo malo, luego uno bueno); presupuesto de latencia del enricher (con
`context()` lento forzado → contexto vacío, no cuelga); `ready_set` correcto;
plan registrado en Decision API con `mission_id`. Perf: `validate` < 10 ms con un
grafo de 5 nodos.

**Done**: dado un goal complejo, el TIE produce un TaskGraph válido, registrado en
Decision API, en < presupuesto; grafos inválidos se rechazan o se reparan con 1
reintento; verificado con `ai_manager` real en un script (un goal real → grafo de
2-3 nodos coherente). Suite verde. Nada se ejecuta todavía (executor es T3).

**Modelo sugerido**: **Opus · Alto** (el planner —frontera LLM + schema + regla de
tamaño— y el algoritmo DAG son la corrección más delicada del bloque).

---

### T3 — Graph Execution Engine: executor + checkpoint + gates + recovery + kill-switch

**Objetivo**: el corazón. Ejecutar el grafo por olas (tamaño 1 en V1.0), con
checkpoint por transición, gates que pausan/reanudan vía ApprovalGate, recuperación
por degradación, kill-switch, y validación determinista por nodo. Todo el estado
en disco → reanudable tras reinicio.

**Archivos**: `app/tie/executor.py` (NEW), `tracer.py` (MOD: `update_graph` por
transición), `tests/test_tie_executor.py` (NEW).

**Tareas** (doc 14 §3.4):
- **Loop de olas** (`executor.py`): `run(graph, mission) -> Mission`. `ready =
  graph.ready_set()`. V1.0: se ejecuta **UNO por iteración** (orden determinista:
  `priority` desc, `id` asc — doc 14 §3.4.2). V1.2 será toda la ola con
  `asyncio.gather` + semáforo `TIE_MAX_PARALLEL`; el código se estructura para que
  ese cambio sea trivial (ola = lista; hoy de longitud 1).
- **Ejecución de nodo**: `runtime = get_runtime(node.runtime or "null")` →
  `runtime.execute_task(AgentTask.from_node(node), memory=memory_router,
  tools=tool_manager, approval_gate=approval_gate)`. El runtime recibe memoria/tools/
  gate POR INYECCIÓN (doc 10 — jamás gestiona los suyos).
- **Checkpoint** (§3.4.3): CADA transición de estado de nodo persiste el grafo
  serializado (`tracer.update_graph(graph)` → UPDATE de `orchestrator_traces.plan`).
  Decenas de UPDATEs por misión — coste trivial (< 20 ms/transición, doc 14 §6).
- **Gates** (§3.4.4, Δ5): nodo con `approval_required=True` → estado
  `WAITING_APPROVAL` + `approval_gate.request_approval(kind="tie.node", title=node.goal,
  action_type="tie_resume", action_payload={"mission_id":..., "node_id":...},
  channel=mission.channel)`. El executor registra un ejecutor `tie_resume` (via
  `approval_gate.register_executor`) y/o se **suscribe a `approval.resolved`**
  (`app/core/events.py`) para reactivar el loop cuando el usuario responde. El nodo
  puede esperar horas/días: el grafo está en disco. **Regalo de A3b**: si el usuario
  pre-autorizó ese `kind` (permiso), el gate se auto-resuelve sin preguntar (con
  rastro) — el TIE no hace nada especial, lo hereda.
- **Recovery V1.0** (§3.4.5, degradar): nodo `FAILED` → sus dependientes (transitivos)
  → `SKIPPED`; el responder entrega lo conseguido + explicación (degradación
  graciosa, regla 11-B); se escribe `mem_error` (`memory_router.store(MemoryType.ERROR,
  source="tie")`). `max_retries`/replan de subárbol = V1.2 (el campo existe, no se usa).
- **Kill-switch** (§3.4.6): `cancel(mission_id)` → nodos `RUNNING` reciben
  cancelación cooperativa (el runtime respeta un `asyncio.Event`/timeout), el resto
  → `CANCELLED`; el responder informa de lo parcial. < 2 s (doc 14 §6). Patrón
  ChatGPT Agent — obligatorio para confianza del usuario.
- **Validación por nodo** (§3.4.7, barato): al terminar un nodo, `validate_result(node)`
  → V1.0 determinista (¿hay `result`? ¿shape correcto contra el schema esperado del
  nodo?). Escribe `node.validation = {"ok":bool,"method":"schema","notes":...}`.
  Verificación LLM opcional = V1.2 (`method="llm"`, solo si el nodo lo declara).
- **Reanudación** (§3.4.3): `resume_pending()` — carga los grafos en estado
  `running|waiting_*` de `orchestrator_traces` y recomputa `ready_set`. Se llamará
  desde el `lifespan` en T4 (aquí se implementa y se testea la función).

**Tests** (`test_tie_executor.py`): grafo lineal de 3 nodos ejecuta en orden;
grafo con 2 ramas independientes ejecuta ambas (aunque en V1.0 sea secuencial, el
ready-set las descubre); nodo con gate → `WAITING_APPROVAL` → al emitir
`approval.resolved` el loop reactiva y termina; nodo FAILED → dependientes SKIPPED
+ `mem_error` escrito + outcome parcial; kill-switch cancela nodos pendientes;
validación por nodo escribe `node.validation`; checkpoint persiste el grafo en cada
transición (contar UPDATEs); `resume_pending()` reconstruye un grafo a medias tras
"reinicio" (nuevo executor lee de la BD). Perf: transición+checkpoint < 20 ms;
overhead del engine por nodo < 50 ms.

**Done**: un grafo de 2-3 nodos con un gate se ejecuta de principio a fin, pausando
en el gate y reanudando al aprobar; un nodo que falla degrada con gracia; el
kill-switch para la misión; todo el estado sobrevive a un reinicio (verificado con
un script contra Postgres real). Suite verde.

**Modelo sugerido**: **Opus · Extra** (es la joya de la corona: máquina de estados +
checkpoint + reanudación + gates asíncronos + kill-switch — la mayor densidad de
correctness del bloque).

---

### T4 — Response Builder + `gateway.set_handler(tie.handle)` + streaming de estado + eventos mission.* + frontend

**Objetivo**: cerrar el pipeline (respuesta sintetizada al usuario) y hacer **el
switch**: desde aquí el chat de Electron y Telegram fluye por el TIE. Streaming de
estado ("analizando → planificando → paso 1/3"), eventos `mission.*`, y la UI de
aprobación de planes + vista de misión.

**Archivos**: `app/tie/responder.py` (NEW), `__init__.py` (MOD: `handle` completo +
`submit_mission`), `tracer.py` (MOD: eventos `mission.*`), `app/main.py` (MOD:
`gateway.set_handler(tie.handle)` + `resume_pending()` en lifespan), `app/api/endpoints/tie.py`
(NEW), frontend: `pages/Missions.tsx` o integración en Chat/Hub (NEW), `lib/api.ts`
(MOD), `App.tsx`/`Sidebar.tsx` (MOD), `tests/test_tie_handle.py` (NEW).

**Tareas**:
- **`responder.py`**: `build(mission, graph) -> OutboundMessage` — sintetiza el
  `outcome` de la misión (modelo según complejidad, `router`) a partir de los
  `result` de los nodos DONE; en degradación, explica lo conseguido y lo que no.
  Escribe `mission.outcome` y lo espeja en el tracer.
- **`tie.handle(envelope) -> str | OutboundMessage`** (Δ3): el punto de entrada
  channel-agnostic. Firma EXACTA de `MessageHandler`. Flujo (doc 14 §3.3):
  `intents.classify` ∥ `enricher.enrich` → camino corto (NullRuntime → respuesta) o
  `planner.plan` → `graph.validate` → (gate de plan si algún nodo `approval_required`
  de alto impacto) → `executor.run` → `responder.build` → tracer. `submit_mission(goal,
  source, channel)` — entrada programática (AE V1.0, WPMS) que salta el intent
  (ya sabe que es una misión).
- **EL SWITCH** (`main.py`, Δ3): `gateway.set_handler(tie.handle)` en el `lifespan`
  (tras arrancar MOS/Gateway/AE). Desde aquí el chat pasa por el TIE. **El camino
  corto DEBE preservar el comportamiento actual del chat** (mismo `chat_service.answer`)
  — ~80% de queries idénticas. Guard: si `TIE_ENABLED=False`, no se hace el switch
  (queda el `chat_message_handler` legacy). Además: `resume_pending()` en el lifespan
  (reanuda grafos a medias tras reinicio).
- **Streaming de estado** (doc 11 B.5): primer feedback ≤ 1 s. Para `/api/chat/stream`
  (Electron, el camino real de `Chat.tsx`) el TIE emite estados ("analizando…",
  "planificando…", "paso 1/3…") antes del resultado. Para Telegram, un mensaje de
  progreso o el resultado final (sin streaming — el adapter no lo necesita). El
  camino corto NO paga esto (responde directo, como hoy).
- **Eventos `mission.*`** (Δ6, doc 17 §4): `mission.started {mission_id, source}`,
  `mission.completed {mission_id, ok, duration_ms, nodes}`, `mission.failed`,
  `mission.cancelled` — emitidos por el tracer. Metadatos, nunca contenido. El
  Learner (V1.1) se suscribirá; el Hub puede sondear.
- **`api/endpoints/tie.py`** (`/api/tie`): `GET /missions` (activas + recientes),
  `GET /missions/{id}` (estado + grafo), `POST /missions/{id}/cancel` (kill-switch),
  `POST /missions/{id}/approve-plan` (aprobar el plan antes de ejecutar), `GET
  /missions/{id}/graph` (nodos + estados para pintar).
- **Frontend**: UI de **aprobación de plan** (análoga al plan-mode de Claude Code —
  ver los 2-3 pasos antes de ejecutar, Aprobar/Rechazar) + **vista de misión**
  (nodos del TaskGraph con su estado, botón kill-switch, streaming del progreso).
  Se integra en el Chat (cuando una query dispara una misión compleja) y/o una
  tarjeta en el Hub. `lib/api.ts` extendido (tipos Mission/TaskGraph/TaskNode +
  métodos). Ítem de Sidebar si procede.
- **[Δ doc 14 §4.3c] Routing al orquestador de proyecto (HOOK, ligero)**: si el
  envelope/misión trae `source="workspace"` + `project_id` y el proyecto tiene un
  `Agent` con `role="orchestrator"` (columna ya existe desde W2e), el planner
  delega primero en ese orquestador. **Alcance honesto**: se implementa el HOOK de
  routing + la frontera de autoridad (solo agentes de ESE `project_id`, solo
  carpetas de ese proyecto — Principio 5 acotado). La creación guiada del orquestador
  al crear un proyecto (UI) se DIFIERE — es la pieza de menor prioridad del bloque;
  el TIE funciona completo sin ella. Documentar el diferimiento.

**Tests** (`test_tie_handle.py`): `tie.handle` con firma de `MessageHandler` (envelope
→ str); camino corto por `handle` responde idéntico a `chat_service.answer`; query
compleja por `handle` planifica+ejecuta; `submit_mission` salta el intent; eventos
`mission.*` se emiten (monkeypatch de `emit`); endpoints HTTP (missions/cancel/
approve-plan) responden; el switch en un `TestClient` no rompe `/api/chat`.

**Done**: el chat de Electron y Telegram pasa por el TIE sin romper nada (camino
corto idéntico); una query compleja muestra el plan, se aprueba, ejecuta con
streaming de estado, y responde; el kill-switch para desde la UI; verificado EN
VIVO contra el backend + frontend reales (click-through). Suite verde.

**Modelo sugerido**: **Opus · Alto** (el switch del handler es alto riesgo — todo
el chat pasa a depender del TIE; el camino corto debe quedar idéntico).

---

### T5 — Tests de contrato + perf + verificación en vivo + cierre del bloque TIE

**Objetivo**: blindar, medir, verificar de punta a punta contra el sistema real, y
cerrar el bloque TIE (SIN bump a 1.0.0 — eso es el cierre de V1.0 completo, tras
MEL + MVP-beta, planes aparte).

**Archivos**: `tests/test_tie_perf.py` (NEW), `tests/test_tie_e2e.py` (NEW),
`CLAUDE.md` (MOD), `PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md` (MOD, marcar TIE v1
hecho), este doc 21 (MOD, marcar T1-T5 cerrados).

**Tareas**:
- **Tests de contrato**: contratos congelados (round-trip, ningún campo cambió de
  firma), `test_module_boundaries` completo (`app.tie.*` internos, barrel), `tie.handle`
  respeta `MessageHandler`.
- **Tests de perf** (doc 14 §6): validación de grafo < 10 ms; transición+checkpoint
  < 20 ms; overhead del engine por nodo < 50 ms; reanudación de grafos al arrancar
  < 500 ms; kill-switch < 2 s. Camino corto no paga el coste del planner (medir que
  una query conversational NO invoca `planner.plan`).
- **Suite completa verde** (351 de v0.9.0 + los nuevos de T1-T5, sin regresión).
- **Verificación EN VIVO contra el Postgres + frontend reales** (la disciplina del
  proyecto — script contra `DATABASE_URL` real + click-through en navegador):
  (a) camino corto — un chat simple sigue respondiendo idéntico a través del TIE;
  (b) misión compleja real — goal → planner → grafo de 2-3 nodos → executor → gate →
  aprobar → responder → outcome coherente, todo con datos reales del usuario;
  (c) kill-switch para una misión a medias; (d) reanudación — matar el backend con
  una misión en `waiting_approval`, relanzar, y que la misión siga viva.
- **CLAUDE.md + docs**: nueva sección del TIE en §1 (detalle por sprint, mismo
  estilo que MOS/WPMS/AE), §4/§5 (módulo `app/tie/`, tabla `orchestrator_traces`),
  marcar TIE v1 hecho en el roadmap. **Nota de auditoría** (pedida siempre al cerrar
  bloque): que `orchestrator_traces` se CREÓ aquí (no existía pese al doc 11); que
  el MEL/Hermes/MVP-beta siguen pendientes como planes aparte.
- **Cierre**: commit del bloque TIE. **Bump a `0.9.2`** (decisión del usuario
  2026-07-16): el desarrollo de V1.0 se hace por bloques —TIE (`0.9.2`) → MEL →
  Orchestrator/integración → MVP-beta, que es el que cierra la fase en `1.0.0`.
  El TIE queda en `0.9.2` en las 3 ubicaciones sincronizadas + los 3 `.bat`. El
  tag `v1.0.0-beta` es el cierre de V1.0 COMPLETO, no de este bloque. (Durante
  T1-T4 la versión se mantiene en `0.9.0`; solo T5 hace el bump al cerrar.)

**Tests**: `test_tie_perf.py` (los 5 presupuestos), `test_tie_e2e.py` (pipeline
completo con `ai_manager` fake determinista: intent → plan → grafo → executor con
gate → responder).

**Done**: TIE v1 blindado, medido, verificado en vivo, documentado. Bloque cerrado
con commit. El siguiente plan (aparte) es el MEL (E1-E2) o el cierre MVP-beta (O5),
a decisión del usuario.

**Modelo sugerido**: **Sonnet · Alto** (verificación y blindaje — menos diseño
novel, más rigor de pruebas y documentación).

---

## 4. Eventos que emite el TIE (doc 17 §4)

Metadatos, nunca contenido. Consumidores: el Learner (V1.1, Mission Learning), la
telemetría/Runtime Intelligence (V2.0+, `subscribe("*")`), el Hub (sondeo).

| Evento | Payload | Se emite en |
|---|---|---|
| `mission.started` | `{mission_id, source, channel}` | T4 |
| `mission.completed` | `{mission_id, ok, duration_ms, nodes}` | T4 |
| `mission.failed` | `{mission_id, error, partial}` | T4 |
| `mission.cancelled` | `{mission_id, at_node}` | T4 |

(Reusa `approval.requested/resolved` de V0.9 A1 para los gates de nodo — el TIE no
emite eventos de aprobación propios.)

---

## 5. Matriz de conexión futura (cabos que NO se dejan sueltos)

| Pieza del TIE v1 | Se conecta con… | Cómo queda preparada ahora |
|---|---|---|
| `router.py` | **MEL** (doc 19, V1.0 E1 — plan aparte) | Fachada de ~30 líneas; E1 la convierte en `mel.complete(capability=...)` con 1 línea. El TIE conserva `router.smart()` |
| `runtime.py` (`AgentRuntime`) | **HermesRuntime** (doc 10, V1.1 — plan aparte) | Interfaz congelada + registro `{name:runtime}`; V1.1 registra `"hermes"` sin tocar el executor |
| tracer `mission.completed` | **Learner** (doc 15, V1.1 — plan aparte) | Evento ya emitido; el Learner se suscribe. El TIE deja `orchestrator_traces` + `mem_error` como materia prima del LLL análisis 1 |
| `AgentTaskAction` (AE, V0.9) | `tie.submit_mission()` | Único punto de delegación; en V1.0 la acción cambia `agent_manager.create_execution` por `tie.submit_mission(goal, source="automation")` — **esto se hace en el plan del MEL/cierre o en un delta del AE, NO en el TIE puro** (se anota aquí para no perderlo) |
| Nodo `approval_required` | ApprovalGate (V0.9) + permisos (A3b) | Reusado tal cual; auto-resolución por permiso pre-autorizado heredada gratis |
| `WAITING_EVENT` (NodeState) | AE flows (V1.2) | Estado ya en el enum; sin lógica en V1.0 |
| Routing a orquestador de proyecto | WPMS (`Agent.role`, W2e) | Hook de routing + frontera de autoridad en T4; creación guiada diferida |
| Streaming de estado + vista de misión | Hub avanzado (V1.5, doc 13 AVCS) | La vista del TaskGraph en T4 es la semilla; el AVCS la potencia después |

**Deuda anotada (no del TIE puro, para no perderla)**: (1) migrar `AgentTaskAction`
a `tie.submit_mission` (delta del AE, cuando el TIE esté vivo); (2) MEL E1-E2 (plan
aparte); (3) MVP-beta O5: auto-start, instalador, onboarding (plan aparte); (4)
LLL análisis 1 sobre `orchestrator_traces` (plan del Learner, V1.1).

---

## 6. Tabla de modelo y esfuerzo recomendados por sprint

| Sprint | Contenido | Modelo | Esfuerzo |
|---|---|---|---|
| **T1** | Esqueleto + contratos congelados + runtime + intent + camino corto + tracer/migración | **Opus** | **Alto** |
| **T2** | Enricher + router mínimo + planner + validación DAG | **Opus** | **Alto** |
| **T3** | Executor (olas=1) + checkpoint + gates + recovery + kill-switch + reanudación | **Opus** | **Extra** |
| **T4** | Responder + `set_handler` (el switch) + streaming + eventos + frontend | **Opus** | **Alto** |
| **T5** | Tests de contrato + perf + verificación en vivo + cierre del bloque | **Sonnet** | **Alto** |

Estimación: 5 sesiones (frente a las 5-6 de O1-O5 del doc 11, de las que aquí se
excluyen el MEL y el empaquetado MVP-beta, y se añade la estructura de grafo del
doc 14 — que es el MISMO trabajo que el executor secuencial ya previsto, mejor
estructurado, doc 14 §5).

---

*Plan derivado de doc 14 (TIE/Cognitive Runtime, Fable 5 2026-07-12) + doc 11-B
(Orchestrator = TIE v1) + doc 10 (AgentRuntime) + doc 16 (disciplina) + doc 17
(eventos). Auditado contra el código REAL (v0.9.0), no solo contra los docs — ver
§1 (deltas: `orchestrator_traces` NO existía, `set_handler` SÍ, sin settings
fast/smart). Alcance EXCLUSIVO del TIE: MEL, Hermes, Learner y MVP-beta son planes
aparte. Regla rectora: mejor diseño, implementación mínima funcional. HITL siempre.*
