# 23 — Plan de sesiones: bloque ORQUESTRATOR (V1.0, cierre en `0.9.5`)

> **Qué es este bloque**: el Orquestador es el vínculo directo Usuario → Aithera.
> Recibe una orden —por compleja que sea—, la **descompone en objetivos**, lanza
> **varias misiones del TIE en paralelo**, las supervisa, se para a preguntar
> cuando toca, y **consolida** todo en una respuesta. **No puede estar capado en
> nada que Aithera sepa hacer**: si Aithera puede hacerlo, el Orquestador puede
> orquestarlo.
>
> **Decisión de arquitectura (usuario, 2026-07-19)**: el Orquestador es una
> **capa POR ENCIMA del TIE**, no un renombrado del TIE. Ver §0 — es lo que
> cambia respecto a la versión anterior de este documento.
>
> **Consume**: doc 11-B (Orchestrator RFC), doc 14 (TIE, en especial §3.4, §3.6
> y §4.3c), doc 10 (AgentRuntime), doc 18 (WPMS), doc 11-A (Automation Engine),
> doc 19 (MEL), doc 17 (bus de eventos), doc 16 (disciplina modular), doc 15
> (Learner, solo puntos de enganche).
>
> **NO cubre** (planes aparte, decisión explícita del usuario): el **MVP-beta**
> (instalador NSIS, auto-start del backend, onboarding, tag `1.0.0`) y el
> **escáner de hardware** para recomendar modelos locales.
>
> **Regla heredada (docs 11/14/16 + PRINCIPIOS_KARPATHY §2)**: el mejor diseño
> posible con la implementación MÍNIMA funcional. Contratos completos hoy;
> código solo el necesario. Sin sobreingeniería, sin abstracciones de un solo
> uso, sin "flexibilidad" no pedida.

---

## 0. El cambio de arquitectura: por qué el TIE no basta

**El problema, con un caso real del usuario.** Un solo mensaje puede contener:
investigar avances en IA · arrancar el proyecto X · crear 15 canales de YouTube
(con investigación de nicho, animación, estrategia y monetización) · responder
un email concreto · avisar a un amigo por WhatsApp cuando todo termine · y poner
al día del estado del proyecto Open Tibia SaaS.

**Qué pasa hoy** (verificado en el código, no supuesto):

| Límite actual | Dónde está | Consecuencia con ese mensaje |
|---|---|---|
| 1 mensaje = 1 misión = 1 grafo | `pipeline._run_pipeline` crea UNA `Mission` | El planner colapsa 6 objetivos heterogéneos en 2-3 nodos vagos y pierde la mayoría |
| Ejecución secuencial | `executor.run` consume `ready_set()` y ejecuta **un nodo por iteración** (ola=1, por diseño de V1.0) | El email esperaría a que terminen los 15 canales |
| Un gate bloquea la misión entera | `executor.run` retorna con `state="waiting"` | Aprobar el email bloquearía el estado de Open Tibia |
| Sin anidamiento | Un nodo no puede abrir su propia misión | "15 canales" necesita planificar dentro de planificar |

**Por qué el TIE se diseñó así — y por qué no fue un error.** Doc 14 §3.6 lo
dice literal: *"en V1.0 la misión es IMPLÍCITA: 1 query compleja = 1 misión = 1
grafo = 1 fila"*. El TIE v1 es el **motor de UNA misión**, y se construyó con
los ganchos puestos para lo que viene: `Mission` es entidad de primera clase con
`id`/`state`/`source`, `submit_mission()` es entrada programática pública,
`_NODE_TASKS` ya indexa por `mission.id` (soporta varias en vuelo), y el
executor está estructurado para `asyncio.gather` + semáforo *"sin cambiar el
algoritmo"* (doc 14, V1.2). **Lo que falta no es el motor: es quien decide que
ahí hay 6 misiones y no 1.** Eso es este bloque.

**La arquitectura acordada:**

```
Usuario ──► ORQUESTRATOR   (descompone · prioriza · respeta dependencias · consolida)
                 ├── TIE #1  investigar avances IA          ┐
                 ├── TIE #2  responder email                │ concurrentes
                 ├── TIE #3  estado Open Tibia SaaS         ┘
                 ├── TIE #4  desarrollo Proyecto X          (largo)
                 └── TIE #5  serie de 15 canales YouTube    (largo)
                              └── sub-misiones anidadas por canal/estrategia
                 ▼
             consolidación ──► respuesta única al usuario
```

**Las tres decisiones, en tres capas** (esto zanja la duda del usuario sobre
quién elige qué):

| Capa | Decide | Dónde |
|---|---|---|
| **Orquestador** | **qué misiones** hay y en qué orden/paralelo | `app/orchestrator/` (R2) |
| **TIE** | **qué pasos y qué herramientas** dentro de una misión | `app/tie/` (R1 cierra el hueco de tools) |
| **MEL** | **qué modelo** ejecuta cada llamada | `app/mel/` (ya cerrado) |

**Regla de no-regresión (crítica)**: el ~80% de los mensajes son de un solo
objetivo. Para ellos el Orquestador **delega en `tie.handle` sin añadir NI UNA
llamada al LLM ni un milisegundo de latencia** — mismo camino corto, mismo
streaming de hoy. La capa nueva solo se activa cuando de verdad hay varios
objetivos (§R2, detección sin coste).

---

## 1. Auditoría del código real (2026-07-19) — deltas frente a los docs

Antes de planificar se auditó el repo real (`0.9.2` + tools + modelos locales +
multi-proveedor). Esta sección es la más importante del documento: **corrige
supuestos que, de darse por buenos, harían fracasar el bloque entero.**

| # | Supuesto de los docs | Realidad en el código | Consecuencia |
|---|---|---|---|
| **Δ1** | doc 11-B planifica `app/orchestrator/` con 6 componentes (intents, enricher, planner, executor, responder, tracer) y sprints O1-O5 | Esos 6 componentes **YA EXISTEN con otro nombre**: son `app/tie/`, cerrados en `0.9.2`. Doc 21 lo dice literal: *"(Orchestrator = TIE v1, sprints O1-O4)"* | Los O1-O4 de doc 11-B están HECHOS. **`app/orchestrator/` SÍ se crea, pero con otro contenido**: la capa de misiones múltiples (§0), que doc 11-B no contempla. Numeración R1-R7 para no chocar con la muerta |
| **Δ2** | doc 11-B §B.2 paso [4] da por hecho que el runtime USA las tools | **EL TIE NUNCA HA EJECUTADO UNA SOLA TOOL.** `NullRuntime.execute_task` solo llama al ToolManager si el nodo trae `metadata.tool_call`, y **NADIE escribe jamás ese campo** (el planner solo emite `tools: [nombres]`, una whitelist). Grep en todo `app/`: la única aparición es la LECTURA en `runtime.py:150`. **Verificado en vivo**: la misión *"lista los archivos de mi carpeta y dime cuántos hay"* terminó `done`, con **0 tools ejecutadas y 5 archivos inventados** | **R1 es bloqueante.** Sin él las 14 tools son inalcanzables y Aithera alucina con seguridad en toda tarea que requiera una herramienta. Es un fallo de **honestidad**, no solo de funcionalidad |
| **Δ3** | 1 mensaje = 1 misión (doc 14 §3.6) | Correcto hoy, pero **insuficiente** para el uso real (§0) | **R2** crea la capa de descomposición + concurrencia + anidamiento |
| **Δ4** | doc 11-B §B.4: "`AgentTaskAction` del AE delega en el Orchestrator" | Sigue llamando a `agent_manager.create_execution()` (V0.9 A3). Deuda anotada en doc 21 §5, sin hacer | **R4** (cambio de una línea, pero exige R1: delegar a un cerebro que no sabe usar tools no aporta nada) |
| **Δ5** | doc 11-B da por hecho que un agente "ejecuta" tareas | `agent_manager._run_execution()` es el **placeholder de V0.5**: ignora la tarea y ejecuta acciones fijas de demo (`list_dir`, `list_scripts`, `git status`) según las tools asignadas. El propio código dice *"En V0.6 esto vendrá del LLM"* | **R4** lo sustituye por delegación real al TIE. Los agentes heredan las 14 tools y el MEL sin lógica nueva |
| **Δ6** | doc 14 §4.3c diseña el orquestador POR PROYECTO con frontera de autoridad | Solo existe la **columna** `Agent.role` (V0.87 W2e, nullable). Cero lógica, cero enforcement | **R4** lo implementa (delegación + autoridad acotada) |
| **Δ7** | El usuario pide que Aithera cree proyectos/tareas/agentes/automatizaciones/reglas **desde el chat** | **No está diseñado en ningún doc.** Alcance nuevo. Lo que SÍ existe y hay que reusar: `workspace_service`, `agent_manager`, `automation_engine` + `seed_builtin_rules`, `EmailTool.add_auto_reply_rule`, `scheduler_service` | **R3** crea las tools de autogestión. Regla dura: **son ADAPTADORES**, nunca reimplementan lógica de negocio (mismo criterio que `WorkspaceAction`, doc 18 §7) |
| **Δ8** | El usuario pide pausas en hitos "testeables por él" + aviso por Telegram | Existen las piezas: `ApprovalGate` (A1) reanudable, `gateway.notify()` (A1), `NodeState.WAITING_APPROVAL` (T3), permisos pre-autorizados (A3b). **No existe** el concepto de "hito verificable" ni preferencia de canal | **R5** los añade sobre lo que ya hay — sin inventar un mecanismo de pausa nuevo |
| **Δ9** | El usuario pide que el chat sepa todo lo que Aithera puede hacer, sin revelar su código | `chat_service.build_system_prompt()` inyecta memoria y preferencias, pero **nada sobre las capacidades del sistema**. El catálogo de tools ya es introspectable (`tool_manager.list_tools()` → 14 tools/91 acciones) | **R6** genera el mapa de capacidades **DESDE el código** (no una lista a mano que se quede obsoleta) |
| **Δ10** | El usuario pide navegación fluida (buscar, abrir páginas, poner vídeo/música) | `browser` (Playwright real) y `search` (Brave/SerpAPI) existen y están verificados. **Límite real ya medido**: `browser.google_search` funciona en código pero Google bloquea el tráfico headless → buscar se hace con `search`, no con el navegador | **R6** cablea el flujo correcto (search → abrir URL con browser), documentando el límite en vez de fingir |
| **Δ11** | ¿Quién elige la herramienta, el MEL o el TIE? | **El MEL elige MODELOS, no tools** (doc 19 §1). No tiene catálogo de tools ni forma de verlas | **Decidido: la elige el TIE**, y concretamente el **runtime en tiempo de ejecución** (R1), no el planner: los parámetros de una tool dependen del resultado del paso anterior, y fijarlos por adelantado es frágil. El planner sigue acotando QUÉ tools puede tocar cada nodo (`node.tools`) — esa es la frontera de seguridad |

**Lo que YA está listo y este bloque reusa tal cual** (cero trabajo nuevo):
`ToolManager` (14 tools/91 acciones + whitelist por agente + timeout duro + log
de auditoría); `ApprovalGate` reanudable + permisos A3b; `gateway.notify`;
`events.py`; `scheduler_service` (APScheduler); `workspace_service` con sus side
effects y eventos; el MEL completo (política activa, override de tarea, pin de
proyecto, multi-proveedor y modelos locales especializados); el TIE entero
(planner → grafo → executor con checkpoint/gates/kill-switch → responder →
tracer) y su UI de Misiones.

---

## 2. Estructura de código objetivo

```
backend/app/orchestrator/          ← MÓDULO NUEVO (R2): la capa de misiones
├── __init__.py        # API pública: handle(envelope), handle_stream(...), run_status(id)
├── contracts.py       # Objective, OrchestrationRun — CONGELADOS (R2)
├── decomposer.py      # 1 mensaje → N Objectives + dependencias (R2)
├── conductor.py       # lanza/supervisa misiones concurrentes + anidamiento (R2)
├── consolidator.py    # junta resultados → respuesta única (R2)
└── models.py          # tabla orchestration_runs (R2)

backend/app/tie/
├── toolloop.py        # NEW (R1): el bucle elegir→ejecutar→observar, aislado y testeable
├── runtime.py         # MOD (R1): NullRuntime usa el bucle
├── planner.py         # MOD (R1): prompt consciente de las tools reales
├── pipeline.py        # MOD (R2/R5): submit_mission acepta parent/run + checkpoints
├── contracts.py       # MOD (R2): Mission.parent_id + Intent.objectives (append-only)
└── capabilities_map.py # NEW (R6): mapa de capacidades generado DESDE el código

backend/app/tools/
└── aithera_tool.py    # NEW (R3): autogestión — Aithera se opera a sí misma

backend/app/agents/
└── agent_manager.py   # MOD (R4): _run_execution deja de ser el placeholder de V0.5

backend/app/automation/
└── actions.py         # MOD (R4): AgentTaskAction → tie.submit_mission
```

**Disciplina modular (doc 16), no negociable:**
- `app/orchestrator/` importa **solo** la API pública del TIE (`app.tie`), el bus
  (`app.core.events`) y config. **NUNCA** `app.tie.pipeline`/`executor`/internos.
- `app/tie/` **NO** importa `app.orchestrator` (la dependencia es en un solo
  sentido: orquestador → TIE). Un ciclo aquí rompería el arranque.
- `aithera_tool.py` **NO** importa modelos SQL sueltos: habla con
  `workspace_service`, `agent_manager`, `automation_engine` y APIs públicas.
- `toolloop.py` es interno de `app.tie`.
- Todo esto lo vigila `tests/test_module_boundaries.py`, **extendido en cada
  sprint que añada módulo**.

---

## 3. Sprints R1 → R7

### R1 — El bucle de tool-use (cierra Δ2 · **BLOQUEANTE**)

**Objetivo**: que un nodo con herramientas disponibles las USE de verdad, con
datos reales, y que **cuando no pueda, lo diga en vez de inventar**.

**Por qué va primero**: hasta que esto exista, todo lo demás es decorado. Un
Orquestador que reparte misiones a un TIE que alucina multiplica el problema por
N en vez de resolverlo.

**Archivos**: `app/tie/toolloop.py` (NEW), `app/tie/runtime.py` (MOD),
`app/tie/planner.py` (MOD: prompt), `app/core/config.py` (MOD: 2 settings),
`tests/test_tie_toolloop.py` (NEW), `tests/test_module_boundaries.py` (MOD).

**Tareas**:
- **`toolloop.py` — `async def run(task, tools, *, max_iters) -> ToolLoopResult`**:
  1. **Catálogo acotado**: intersección de `task.tools` (whitelist del nodo, la
     pone el planner) con `tool_manager.list_tools()`. Se le pasa al modelo el
     `tool_id`, `action`, `description` y `params` de cada acción **permitida**.
     Si la intersección es vacía → no hay bucle, camino de chat de siempre.
  2. **Elección**: `mel.complete(capability=AGENTIC)` con un prompt que exige
     responder **solo JSON**: `{"tool": {"tool_id", "action", "params"}}` o
     `{"answer": "..."}`. Parseo tolerante (bloques markdown) — **reusar el
     extractor de `planner.py`**, no escribir otro.
  3. **Ejecución**: `tool_manager.execute(..., allowed_tools=task.tools, timeout=...)`.
     La whitelist, el timeout duro, la validación de params y el log de auditoría
     **siguen siendo del ToolManager** — el bucle no los reimplementa.
  4. **Observación**: el resultado (truncado a un tamaño razonable) se inyecta
     como turno siguiente y se repite. Máx `TIE_TOOL_MAX_ITERS` (default **5**).
- **Límite de seguridad (acordado con el usuario, 2026-07-18)**: el bucle ejecuta
  SOLO acciones con `requires_confirmation=False` (leer, listar, buscar,
  screenshot, procesos…). Si el modelo pide una sensible (enviar email, shell,
  PowerShell, clics de escritorio, borrar), **se rechaza con motivo** y se le
  dice al modelo para que busque otra vía; la respuesta final explica
  honestamente qué no pudo hacerse sin permiso. Las sensibles siguen pasando por
  el gate del plan (T4a) o de nodo (T3).
- **Honestidad estructural**: si tras `max_iters` no hay respuesta fundamentada,
  el nodo devuelve `success=False` con el detalle — **nunca** una respuesta
  inventada. La validación por nodo de T3 ya rechaza "éxito sin salida".
- **Presupuesto y cancelación**: cada iteración cuenta contra `node.budget_ms`;
  el kill-switch de T3 sigue cancelando en vuelo (el bucle debe ser
  `await`-able y propagar `CancelledError` sin tragárselo).
- **`planner.py`**: el prompt pasa a decir que las tools de un nodo **se van a
  usar de verdad**, para que asigne `node.tools` con criterio en vez de
  decorativamente.

**Criterio de éxito verificable (PRINCIPIOS §4)**:
1. Test de regresión del hallazgo → verificar: una tarea *"lista los archivos de
   `<carpeta de prueba>`"* ejecuta `filesystem.list_dir` de verdad (ToolManager
   real) y **los nombres reales aparecen** en la salida.
2. Acción sensible → verificar: `email.send_email` es **rechazada sin ejecutarse**
   y el motivo llega al modelo.
3. Catálogo → verificar: una tool fuera de `node.tools` **no aparece** en el
   prompt ni puede ejecutarse.
4. Sin tools → verificar: camino de chat idéntico al actual (cero regresión).
5. `max_iters` → verificar: el bucle nunca hace más llamadas de las permitidas.

**Done**: la misión que hoy inventa 5 archivos, lista los reales.
**Modelo**: **Opus · Alto** — toca el runtime que ejecuta TODO y define el límite
de seguridad; un fallo aquí es ejecución no autorizada.

---

### R2 — La capa Orquestador: descomposición, concurrencia y anidamiento (cierra Δ3)

**Objetivo**: que un mensaje con varios objetivos se convierta en **varias
misiones del TIE ejecutándose a la vez**, con sus dependencias respetadas, sus
sub-misiones cuando hace falta, y **una sola respuesta** al final.

**Archivos**: `app/orchestrator/` completo (NEW: `__init__.py`, `contracts.py`,
`decomposer.py`, `conductor.py`, `consolidator.py`, `models.py`),
`alembic/versions/*_v10_orchestration_runs.py` (NEW, migración **24.ª**),
`app/tie/contracts.py` (MOD: `Mission.parent_id`, `Intent.objectives`),
`app/tie/pipeline.py` (MOD: `submit_mission` acepta `parent_id`/`run_id`),
`app/main.py` (MOD: EL SWITCH), `app/api/endpoints/orchestrator.py` (NEW),
`tests/test_orchestrator.py` (NEW), `tests/test_module_boundaries.py` (MOD).

**Tareas**:
- **Detección SIN COSTE (clave para no regresionar el 80%)**: `Intent` gana
  `objectives: list[str] = []` (**append-only**, permitido por la regla de
  evolución de contratos). Lo rellena **el clasificador que YA se llama** — cero
  llamadas extra al LLM. `len(objectives) <= 1` → el Orquestador delega en
  `tie.handle` tal cual (mismo camino corto, mismo streaming). `>= 2` → capa
  nueva.
- **`contracts.py` CONGELADO**: `Objective` (id, goal, depends_on,
  needs_decomposition, priority, state, mission_id, outcome) y
  `OrchestrationRun` (id, user_message, objectives, state, outcome, channel).
- **`decomposer.py`**: para el caso multi (y **solo** ese), una llamada
  `mel.complete(capability=REASON)` que devuelve los objetivos con sus
  `depends_on` (ej.: *"avisar a Héctor cuando termine todo"* depende de los
  demás) y marca `needs_decomposition` en los que siguen siendo demasiado
  amplios (ej.: "15 canales de YouTube"). Salida validada; ante fallo o JSON
  inválido → **degrada a una sola misión** (nunca romper).
- **`conductor.py`** — el corazón:
  - **Ready-set por dependencias**: lanza los objetivos cuyas `depends_on` están
    `done`. Mismo patrón conceptual que `graph.ready_set()` pero sobre objetivos;
    implementación propia y pequeña (no se fuerza `graph.py`, que opera sobre
    `TaskNode`).
  - **Concurrencia real**: `asyncio.gather` con **semáforo** `ORCH_MAX_CONCURRENT`
    (default **3**) — protege al MEL y a los modelos locales de saturarse.
  - **Aislamiento**: una misión que falla o queda `waiting` en un gate **NO
    bloquea a las demás** (`return_exceptions=True` + estado por objetivo). Esto
    es lo que hoy no se puede hacer y es media razón de ser del bloque.
  - **Anidamiento**: si un objetivo trae `needs_decomposition`, el conductor
    vuelve a llamar al decomposer sobre él y lanza sub-misiones con `parent_id`.
    Profundidad máxima `ORCH_MAX_DEPTH` (default **2**) — límite duro contra
    recursión descontrolada. **El anidamiento lo decide el orquestador, NUNCA un
    nodo**: así la recursión queda acotada en un solo sitio.
  - **Checkpoint**: el estado del run se persiste en `orchestration_runs` en cada
    transición (mismo criterio que el checkpoint por transición de T3) — un
    reinicio no pierde el run.
- **`consolidator.py`**: junta los `outcome` de todas las misiones y redacta UNA
  respuesta con `mel.complete(capability=SUMMARIZE)`, indicando qué quedó
  pendiente de aprobación y qué falló. **Plantilla determinista si el LLM falla**
  (mismo patrón que el responder de T4a y el summarizer de M3: nunca dejar al
  usuario sin respuesta).
- **Migración 24.ª**: `orchestration_runs` + `orchestrator_traces.parent_trace_id`
  y `.run_id` (aditiva, idempotente). **Aplicada al Postgres real en el mismo
  paso y verificada** — la lección dura del proyecto (3 incidentes previos).
- **EL SWITCH** (`main.py`): `gateway.set_handler(orchestrator.handle)`. Con
  `ORCH_ENABLED=false` (kill-switch) queda `tie.handle` exactamente como hoy.
- **Endpoints** `/api/orchestrator`: `GET /runs`, `GET /runs/{id}` (con sus
  misiones y estados), `POST /runs/{id}/cancel`.
- **Eventos** (doc 17): `orchestration.started` / `.objective_completed` /
  `.completed` — metadatos, nunca contenido.

**Criterio de éxito verificable**:
1. Mensaje de 1 objetivo → verificar: **cero** llamadas extra al LLM y misma
   respuesta que hoy (test que cuenta las llamadas).
2. Mensaje de 3 objetivos independientes → verificar: 3 misiones, y el tiempo
   total < suma de los individuales (concurrencia real, con runtimes fake).
3. Objetivo con `depends_on` → verificar: no arranca hasta que su dependencia
   está `done`.
4. Una misión falla → verificar: las otras terminan igual y la consolidación lo
   dice honestamente.
5. Una misión queda en gate → verificar: las demás **no** se bloquean.
6. `needs_decomposition` → verificar: se crean sub-misiones con `parent_id`, y
   `ORCH_MAX_DEPTH` corta la recursión.
7. Fronteras: `app.tie` **no** importa `app.orchestrator` (test).

**Done**: el mensaje-ejemplo del usuario (§0) produce misiones separadas y
concurrentes, con el aviso final dependiendo del resto.
**Modelo**: **Opus · Máximo** — es la arquitectura nueva del bloque, toca dos
contratos congelados (`Mission`, `Intent`), introduce concurrencia real y un
switch en el arranque. Es la sesión con más superficie de fallo del plan.

---

### R3 — Aithera se opera a sí misma (cierra Δ7)

**Objetivo**: que Aithera cree proyectos, tareas, milestones, agentes,
automatizaciones, cron jobs y reglas de email **cuando el usuario se lo pide por
chat o voz**, y que **pregunte si le falta un dato** en vez de inventarlo.

**Archivos**: `app/tools/aithera_tool.py` (NEW), `app/tools/tool_manager.py`
(MOD: registro), `tests/test_aithera_tool.py` (NEW).

**Tareas**:
- **`aithera_tool.py` — tool `aithera`**, con acciones agrupadas:
  - *Workspace*: `create_project`, `create_milestone`, `create_task`,
    `update_task`, `list_projects`, `project_status`.
  - *Agentes*: `create_agent`, `assign_tools`, `list_agents`, `run_agent_task`.
  - *Automatización*: `create_rule` (AE), `create_cron_job` (`scheduler_service`),
    `list_rules`, `toggle_rule`.
  - *Email*: `create_auto_reply_rule` (delega en `EmailTool`).
- **Regla dura — son ADAPTADORES**: cada acción llama al servicio que ya existe
  (`workspace_service.create_task`, `agent_manager.create_agent`,
  `automation_engine`, `scheduler_service`, `EmailTool`). **Cero** lógica de
  negocio nueva, **cero** SQL directo, **cero** recálculo de progreso a mano
  (mismo criterio que `WorkspaceAction` del AE, doc 18 §7). Si una acción
  necesita 30 líneas propias, es señal de que está reimplementando algo: parar y
  reusar.
- **Datos que faltan → preguntar**: cada acción declara sus campos obligatorios;
  si falta uno, devuelve `success=False` con `missing: [...]` y un mensaje claro.
  El bucle de R1 lo lee y el TIE lo convierte en pregunta al usuario. **Nunca
  rellenar con valores inventados.**
- **Seguridad**: `create_*`/`toggle_*` son acciones de escritura →
  `requires_confirmation=True`, salvo que el permiso correspondiente esté
  pre-autorizado (A3b lo resuelve solo). Las de lectura (`list_*`, `*_status`)
  no piden confirmación.

**Criterio de éxito verificable**:
1. *"créame un proyecto X con 3 tareas"* → verificar: proyecto y tareas **reales
   en la BD**, con el progreso recalculado por `workspace_service` (no a mano).
2. Falta un dato obligatorio → verificar: `missing` poblado y **nada creado**.
3. Fronteras → verificar: `aithera_tool.py` no importa modelos SQL sueltos (test).
4. Cada acción de escritura pide confirmación salvo permiso pre-autorizado.

**Done**: pedir por chat un proyecto con tareas y agentes lo crea de verdad.
**Modelo**: **Sonnet · Alto** — es trabajo de adaptador, repetitivo y bien
acotado: el diseño está cerrado y los servicios destino ya existen. No hay
decisiones de arquitectura abiertas.

---

### R4 — Agentes reales + el AE delega (cierra Δ4, Δ5, Δ6)

**Objetivo**: que un agente **haga la tarea que le pides** (hoy ignora el texto y
corre una demo de V0.5), que el Automation Engine delegue en el TIE, y que exista
el orquestador **por proyecto** con su frontera de autoridad.

**Archivos**: `app/agents/agent_manager.py` (MOD), `app/automation/actions.py`
(MOD), `app/tie/pipeline.py` (MOD: autoridad por proyecto),
`tests/test_agent_execution.py` (NEW), `tests/test_automation_actions.py` (MOD).

**Tareas**:
- **`agent_manager._run_execution` → delegación real**: sustituir el placeholder
  por `tie.submit_mission(goal=task, source="agent", project_id=agent.project_id)`.
  El resultado de la misión se guarda en `AgentExecution.result`/`tool_calls`.
  **Borrar** el bloque de demo (`list_dir`/`list_scripts`/`git status`) — es
  código muerto que TU cambio deja huérfano (PRINCIPIOS §3).
- **Whitelist del agente = frontera del nodo**: `agent.allowed_tools` debe llegar
  a los nodos de la misión, para que el bucle de R1 no pueda usar una tool que el
  agente no tiene. Sin esto, delegar **amplía** permisos en silencio.
- **`AgentTaskAction`** (AE): `agent_manager.create_execution` →
  `tie.submit_mission(source="automation")`. Fire-and-forget con el `trace_id` en
  el `ActionResult` (una misión puede durar minutos; el AE no puede bloquearse).
  La auditoría del resultado ya la lleva el TIE (`orchestrator_traces` + eventos).
- **Orquestador de proyecto** (doc 14 §4.3c): si un proyecto tiene un agente con
  `role="orchestrator"`, las misiones de ese proyecto se le enrutan, y su
  **autoridad queda acotada** a los agentes de su mismo `project_id` y a las
  carpetas de ese proyecto (`Project.repo_path`). El enforcement es explícito y
  testeado — una autoridad que no se comprueba no existe.

**Criterio de éxito verificable**:
1. Lanzar un agente con la tarea *"cuenta los archivos de `<carpeta>`"* →
   verificar: ejecuta `filesystem.list_dir` real y responde con el número real
   (hoy responde la demo fija).
2. Agente sin `filesystem` en `allowed_tools` → verificar: **no puede** usarla.
3. Una regla del AE con `AgentTaskAction` → verificar: crea una misión real y no
   bloquea al motor.
4. Orquestador de proyecto → verificar: no puede tocar agentes de otro proyecto.

**Done**: un agente hace la tarea real que se le pide, con sus tools y sus
límites.
**Modelo**: **Opus · Alto** — toca permisos y fronteras de autoridad; un fallo
aquí es ampliación silenciosa de privilegios.

---

### R5 — Flujo de trabajo: checkpoints verificables, avisos y cron (cierra Δ8)

**Objetivo**: el flujo que pidió el usuario — el Orquestador planifica, ejecuta,
y **cada vez que completa algo que el usuario puede comprobar, para y avisa** por
el canal que el usuario prefiera.

**Archivos**: `app/tie/contracts.py` (MOD: `TaskNode.checkpoint`),
`app/tie/executor.py` (MOD: pausa en checkpoint), `app/tie/planner.py` (MOD:
marcar checkpoints), `app/orchestrator/conductor.py` (MOD: avisos por run),
`app/core/config.py` (MOD), `frontend/src/pages/Settings.tsx` (MOD: preferencia
de canal), `tests/test_checkpoints.py` (NEW).

**Tareas**:
- **`TaskNode.checkpoint: bool`** (append-only): el planner lo marca en los nodos
  cuyo resultado el usuario **puede verificar** (un entregable, no un paso
  intermedio). El prompt debe explicar esa diferencia con ejemplos.
- **Pausa reusando lo que hay**: un checkpoint alcanzado abre un `ApprovalGate`
  con `kind="tie.checkpoint"`. **No se inventa un mecanismo de pausa nuevo**: el
  gate ya es persistente, reanudable y con auto-resolución por permisos (A3b).
- **Aviso por el canal preferido**: `gateway.notify()` al canal configurado
  (Telegram si el usuario lo eligió, si no la UI). Preferencia en `Config`
  (`notify_channel`), patrón de A3b — sin migración. Fail-soft: si el canal falla,
  la misión sigue y el aviso queda en la UI.
- **Cron desde el chat**: `aithera_tool.create_cron_job` (R3) conectado a
  `scheduler_service.add_cron_job`, con la regla persistida para que sobreviva a
  un reinicio.

**Criterio de éxito verificable**:
1. Plan con un checkpoint → verificar: la misión **pausa ahí** y notifica.
2. Aprobar → verificar: continúa desde donde estaba (reanudación de T3).
3. Canal Telegram configurado → verificar: llega el mensaje (o degrada sin romper
   si falla).
4. Cron creado por chat → verificar: existe en APScheduler y sobrevive a un
   reinicio.

**Done**: una misión larga se detiene en cada entregable, avisa, y espera.
**Modelo**: **Opus · Alto** — coordina gates, notificaciones y scheduler; los
fallos aquí son "se quedó parado para siempre" o "no avisó", difíciles de
detectar en tests.

---

### R6 — Aithera se conoce + navegación fluida (cierra Δ9, Δ10)

**Objetivo**: que el chat sepa **todo lo que Aithera puede hacer** (sin revelar
su código) y que buscar/abrir/reproducir en la web sea fluido.

**Archivos**: `app/tie/capabilities_map.py` (NEW), `app/services/chat_service.py`
(MOD: system prompt), `tests/test_capabilities_map.py` (NEW).

**Tareas**:
- **Mapa generado DESDE el código**, nunca escrito a mano: recorre
  `tool_manager.list_tools()` (14/91), las políticas del MEL, las acciones del AE
  y los servicios del WPMS, y produce un resumen **corto** en lenguaje natural.
  Una lista a mano se queda obsoleta en la siguiente sesión; ésta no.
- **Frontera de confidencialidad**: el mapa describe **capacidades**, nunca rutas
  de archivo, nombres de módulo, esquema de BD ni prompts internos. Test explícito
  que falla si aparece `app/`, `.py` o un nombre de tabla.
- **Presupuesto de tokens**: el mapa se inyecta **resumido** (tope duro de
  caracteres) y **cacheado** — no puede comerse el contexto del chat en cada
  mensaje.
- **Navegación fluida**: documentar y cablear el flujo correcto —
  `search.search_web` para buscar (Brave/SerpAPI) → `browser.open_url` para abrir
  el resultado. **No** usar `browser.google_search` (Google bloquea headless,
  medido en la auditoría de tools). Para vídeo/música: buscar → abrir la URL.

**Criterio de éxito verificable**:
1. *"¿qué sabes hacer?"* → verificar: enumera capacidades reales (email,
   calendario, navegador, escritorio, agentes, automatizaciones…).
2. *"¿cómo estás hecha por dentro?"* → verificar: **no** revela módulos, rutas ni
   esquema.
3. Añadir una tool nueva → verificar: aparece en el mapa **sin tocar el mapa**.
4. *"busca X y ábremelo"* → verificar: usa `search` y luego `browser`.

**Done**: Aithera explica lo que puede hacer, y el mapa se actualiza solo.
**Modelo**: **Sonnet · Alto** — introspección + prompt, bien acotado y sin
decisiones de arquitectura abiertas.

---

### R7 — Cierre: contratos, rendimiento, verificación en vivo y bump `0.9.5`

**Objetivo**: blindar el bloque y cerrarlo con honestidad.

**Archivos**: `tests/test_orchestrator_e2e.py` (NEW),
`tests/test_orchestrator_perf.py` (NEW), `tests/test_module_boundaries.py` (MOD),
`CLAUDE.md`, `PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md`, los 3 sitios de
versión + los `.bat`.

**Tareas**:
- **E2E con la cadena REAL** (mismo criterio que `test_tie_e2e` de T5): un solo
  punto fake, la frontera del LLM; todo lo demás real (decomposer → conductor →
  TIE → toolloop → ToolManager → consolidator).
- **Perf**: overhead del orquestador sobre el camino de 1 objetivo **< 50 ms**
  (la regla de no-regresión de §0, medida); concurrencia real demostrada con
  runtimes fake; `ORCH_MAX_CONCURRENT` respetado.
- **Auditoría de cierre** (feedback permanente del usuario): TODOs/stubs, imports
  muertos, fronteras modulares, cadena de migraciones, superficie pública vs.
  docs. Informe completo con lo que quedó **diferido a propósito**.
- **Cierre**: bump `0.9.2` → **`0.9.5`** en las 3 ubicaciones sincronizadas
  (`backend/app/core/config.py`, `backend/app/main.py` ×2,
  `frontend/package.json`) + los 3 `.bat`. CLAUDE.md y roadmap al día. Tag
  `v0.9.5`.

**Criterio de éxito verificable**: suite completa verde; overhead medido;
verificación en vivo contra el Postgres real **con limpieza confirmada**; informe
entregado.
**Modelo**: **Opus · Alto** — la auditoría de cierre exige criterio para
distinguir deuda real de alcance diferido.

---

## 4. Modelo y esfuerzo por sesión

| Sprint | Contenido | Modelo | Esfuerzo | Por qué |
|---|---|---|---|---|
| **R1** | Bucle de tool-use + límite de seguridad | **Opus** | **Alto** | Runtime que ejecuta todo; un fallo = ejecución no autorizada |
| **R2** | Capa Orquestador: descomposición, concurrencia, anidamiento | **Opus** | **Máximo** | Arquitectura nueva, 2 contratos congelados, concurrencia real, switch de arranque |
| **R3** | Tools de autogestión de Aithera | **Sonnet** | **Alto** | Adaptadores sobre servicios ya existentes; diseño cerrado |
| **R4** | Agentes reales + AE delega + autoridad por proyecto | **Opus** | **Alto** | Permisos y fronteras; fallo = ampliación silenciosa de privilegios |
| **R5** | Checkpoints verificables + avisos + cron | **Opus** | **Alto** | Gates + notificaciones + scheduler; fallos difíciles de ver en tests |
| **R6** | Autoconocimiento + navegación fluida | **Sonnet** | **Alto** | Introspección + prompt, bien acotado |
| **R7** | E2E + perf + auditoría + cierre `0.9.5` | **Opus** | **Alto** | Criterio para separar deuda real de alcance diferido |

**Nota para las sesiones con modelo inferior (R3, R6)**: ambas tienen el diseño
cerrado en este documento, servicios destino ya existentes y criterios de éxito
verificables punto por punto. **No requieren decisiones de arquitectura.** Si al
ejecutarlas aparece una decisión de diseño no contemplada aquí, la regla es
**parar y preguntar** (PRINCIPIOS §1), no improvisar.

---

## 5. Eventos del bloque (doc 17)

| Evento | Emite | Payload | Sprint |
|---|---|---|---|
| `orchestration.started` | orchestrator | `{run_id, n_objectives}` | R2 |
| `orchestration.objective_completed` | orchestrator | `{run_id, objective_id, ok}` | R2 |
| `orchestration.completed` | orchestrator | `{run_id, ok, duration_ms}` | R2 |
| `tie.tool_used` | tie (toolloop) | `{mission_id, tool_id, action, ok}` | R1 |
| `mission.checkpoint_reached` | tie (executor) | `{mission_id, node_id}` | R5 |

Regla de doc 17: **metadatos, nunca contenido**. Un evento se añade cuando su
consumidor existe — nada especulativo.

---

## 6. Matriz de conexión (qué toca este bloque y qué NO)

| Sistema | Qué hace este bloque | Qué NO |
|---|---|---|
| **TIE** | Le añade el bucle de tools (R1) y lo invoca N veces en paralelo (R2) | No lo reescribe: planner/executor/gates/tracer siguen igual |
| **MEL** | Lo usa para elegir modelo (AGENTIC en R1, REASON y SUMMARIZE en R2) | No lo toca. El MEL **no** elige tools (Δ11) |
| **AE** | `AgentTaskAction` delega en el TIE (R4) | No cambia triggers, conditions ni el motor de reglas |
| **WPMS** | `aithera_tool` crea proyectos/tareas vía `workspace_service` (R3) | No duplica su lógica ni recalcula progreso |
| **MOS** | El TIE ya lo consulta por el enricher | Sin cambios |
| **ApprovalGate** | Reusado para checkpoints (R5) | No se crea un mecanismo de pausa nuevo |
| **Gateway** | `set_handler(orchestrator.handle)` (R2) + `notify` (R5) | Los adapters no se tocan |
| **Learner** | Los eventos y trazas quedan como materia prima | No se construye (V1.1) |
| **Hermes** | El registro de runtimes sigue abierto | No se construye (V1.1) |

---

## 7. Criterios de cierre del bloque

1. **La prueba del hallazgo**: *"lista los archivos de mi carpeta"* devuelve los
   archivos **reales**. Cero alucinación en tareas con herramienta.
2. **La prueba del mensaje múltiple** (§0): varios objetivos → misiones
   concurrentes, dependencias respetadas, una respuesta consolidada.
3. **La prueba de no-regresión**: un mensaje simple responde igual de rápido que
   hoy, con streaming, y **sin llamadas extra al LLM**.
4. **La prueba de autogestión**: pedir por chat un proyecto con tareas y agentes
   lo crea de verdad.
5. **La prueba del agente**: un agente ejecuta la tarea real que se le pide, con
   sus tools y sus límites.
6. **La prueba de honestidad**: cuando algo no se puede hacer (sin permiso, sin
   tool, sin datos), Aithera **lo dice** — nunca lo finge.
7. Suite completa verde · fronteras modulares vigiladas · migración 24.ª aplicada
   y verificada contra Postgres real · verificación en vivo con limpieza
   confirmada · informe de auditoría entregado.
8. Bump a **`0.9.5`** + tag `v0.9.5`.

---

*Documento reescrito el 2026-07-19 tras la decisión de arquitectura del usuario:
el Orquestador es una capa POR ENCIMA del TIE, con misiones concurrentes y
anidadas. La versión anterior asumía Orquestador ≈ TIE y no cubría el caso real
de un mensaje con varios objetivos. Los 11 deltas de la auditoría del código real
se conservan y se amplían (Δ3 nuevo).*
