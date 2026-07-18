# 23 — Plan de sesiones: bloque ORQUESTRATOR (V1.0, cierre en `0.9.5`)

> **Qué es este bloque**: el Orquestador es el vínculo directo Usuario → Aithera.
> Recibe una orden y la convierte en trabajo real: planifica, crea lo que haga
> falta dentro de Aithera (proyectos, tareas, agentes, automatizaciones, reglas),
> ejecuta con herramientas de verdad, se para a preguntar cuando toca, y avisa
> por el canal que el usuario prefiera. **No puede estar capado en nada que
> Aithera sepa hacer**: si Aithera puede hacerlo, el Orquestador puede orquestarlo.
>
> **Consume**: doc 11-B (Orchestrator RFC), doc 14 (TIE/Cognitive Runtime, en
> especial §3.4 y §4.3c), doc 10 (AgentRuntime), doc 18 (WPMS), doc 11-A
> (Automation Engine), doc 19 (MEL), doc 17 (bus de eventos), doc 16 (disciplina
> modular), doc 15 (Learner, solo puntos de enganche).
>
> **NO cubre** (planes aparte, por decisión explícita del usuario): el **MVP-beta**
> (sprint O5 de doc 11: instalador NSIS, auto-start del backend, onboarding, tag
> `1.0.0`) y el **escáner de hardware** del PC del usuario para recomendar modelos
> locales. Ambos van después de este bloque.
>
> **Regla heredada (docs 11/14/16)**: el mejor diseño posible con la
> implementación MÍNIMA funcional. Contratos completos hoy; código solo el
> necesario. Sin sobreingeniería.

---

## 1. Auditoría del código real (2026-07-18) — deltas frente a los docs

Antes de planificar se auditó el repo real (v0.9.2 + tools + modelos locales).
Esta sección es la más importante del documento: **corrige supuestos de los docs
que, de darse por buenos, harían fracasar el bloque entero.**

| # | Supuesto de los docs | Realidad en el código | Consecuencia para el plan |
|---|---|---|---|
| **Δ1** | doc 11-B planifica un módulo `app/orchestrator/` con 6 componentes (intents, enricher, planner, executor, responder, tracer, runtime) y sprints O1-O5 | **YA EXISTE, con otro nombre**: es `app/tie/`, construido en T1-T5 y cerrado en `0.9.2`. Los 6 componentes están, uno a uno. Doc 21 lo dice literal: "(Orchestrator = TIE v1, sprints O1-O4)" | **NO se crea ningún módulo nuevo `orchestrator/`**. Los sprints O1-O4 están HECHOS. Este plan numera **R1-R7** para no chocar con esa numeración muerta. O5 (MVP-beta) queda fuera |
| **Δ2** | doc 11-B §B.2 paso [4]: "executor: por step → runtime.execute_task(step, memory, tools, gate)" — se da por hecho que el runtime USA las tools | **EL TIE NUNCA HA EJECUTADO UNA SOLA TOOL.** `NullRuntime.execute_task` solo llama al ToolManager si el nodo trae `metadata.tool_call` con `tool_id`/`action`/`params`, y **NADIE escribe nunca ese campo**: el planner solo emite `tools: [nombres]` (una whitelist). Grep en todo `app/`: la única aparición es la LECTURA en `runtime.py:150`. **Verificado en vivo**: la misión "lista los archivos de mi carpeta y dime cuántos hay" terminó `done`, con 0 tools ejecutadas y **5 archivos inventados** | **R1 es el sprint más crítico del bloque.** Sin él, las 14 tools son inalcanzables y Aithera alucina con seguridad en toda tarea que requiera una herramienta. Es un fallo de honestidad, no solo de funcionalidad |
| **Δ3** | doc 11-B §B.4: "`AgentTaskAction` del AE delega en el Orchestrator" | `AgentTaskAction` sigue llamando a `agent_manager.create_execution()` (V0.9 A3). La deuda está anotada en doc 21 §5, sin hacer | **R3** hace el cambio (es de una línea, pero exige que R1 exista antes: delegar a un cerebro que no sabe usar tools no aporta nada) |
| **Δ4** | doc 11-B da por hecho que un agente "ejecuta" tareas | `agent_manager._run_execution()` es el **placeholder de V0.5**: ignora la tarea del usuario y ejecuta acciones fijas de demo (`list_dir`, `list_scripts`, `git status`) según qué tools tenga asignadas. Comentario en el propio código: "En V0.6 esto vendrá del LLM" | **R3** lo sustituye por delegación real al TIE. Los agentes heredan así las 14 tools y el MEL sin lógica nueva |
| **Δ5** | doc 14 §4.3c diseña el orquestador POR PROYECTO con su frontera de autoridad | Solo existe la **columna** `Agent.role` (V0.87 W2e, nullable). Cero lógica de delegación, cero enforcement, cero creación guiada — el propio doc lo admite | **R4** lo implementa de verdad (delegación + autoridad acotada + creación guiada) |
| **Δ6** | El usuario pide que Aithera cree proyectos/tareas/agentes/automatizaciones/reglas **desde el chat** | **No está diseñado en ningún doc.** Es alcance nuevo. Lo que SÍ existe y hay que reusar: `workspace_service` (proyectos/tareas/milestones), `agent_manager` (CRUD agentes), `automation_engine` + `seed_builtin_rules` (reglas), `EmailTool.add_auto_reply_rule`, `scheduler_service` (cron) | **R2** crea las tools de autogestión. Regla dura: **son ADAPTADORES**, nunca reimplementan lógica de negocio (mismo criterio que `WorkspaceAction` del AE, doc 18 §7) |
| **Δ7** | El usuario pide pausas en hitos "testeables por el usuario" + aviso por Telegram | Existen las piezas: `ApprovalGate` (A1) reanudable, `gateway.notify()` (A1) para push sin envelope entrante, `NodeState.WAITING_APPROVAL` (T3), permisos pre-autorizados (A3b). **No existe** el concepto de "hito verificable" ni la preferencia de canal de notificación | **R5** los añade sobre lo que ya hay — sin inventar un mecanismo de pausa nuevo |
| **Δ8** | El usuario pide que el chat sepa todo lo que Aithera puede hacer, sin revelar su código | `chat_service.build_system_prompt()` inyecta memoria del MOS y preferencias, pero **nada sobre las capacidades del propio sistema**. El catálogo de tools ya es introspectable (`tool_manager.list_tools()` → 14 tools/91 acciones) | **R6** genera el "mapa de capacidades" DESDE el código (no una lista escrita a mano que se quede obsoleta) y lo inyecta acotado |
| **Δ9** | El usuario pide navegación fluida (buscar, abrir páginas, poner vídeo/música) | `browser` (Playwright real) y `search` (Brave/SerpAPI) existen y están verificados. **Limitación real ya medida**: `browser.google_search` funciona en código pero Google bloquea el tráfico headless → buscar se hace con `search`, no con el navegador | **R6** cablea el flujo correcto (search → abrir URL con browser), documentando el límite en vez de fingir que Google funciona |
| **Δ10** | ¿Quién elige la herramienta, el MEL o el TIE? | **El MEL elige MODELOS, no tools** (doc 19 §1: "el resto del sistema pide CAPACIDADES, el MEL decide QUÉ MODELO"). No tiene ni catálogo de tools ni forma de verlas | **Decidido: la elección de tool es del TIE.** Concretamente del **runtime** en tiempo de ejecución (R1), no del planner: los parámetros de una tool dependen del resultado del paso anterior, y planificarlos por adelantado es frágil. El planner sigue acotando QUÉ tools puede tocar cada nodo (`node.tools`), que es la frontera de seguridad |

**Lo que YA está listo y este bloque reusa tal cual** (cero trabajo nuevo):
`ToolManager` con 14 tools/91 acciones + whitelist por agente + timeout duro +
log de auditoría; `ApprovalGate` reanudable + permisos A3b; `gateway.notify`;
`events.py`; `scheduler_service` (APScheduler); `workspace_service` con sus side
effects y eventos; el MEL completo (política activa, override de tarea, pin de
proyecto, modelos locales especializados); el TIE entero (planner→grafo→executor
con checkpoint/gates/kill-switch→responder→tracer) y su UI de Misiones.

---

## 2. Estructura de código objetivo

```
backend/app/tie/
├── runtime.py         # MOD (R1): NullRuntime gana el BUCLE DE TOOL-USE real
├── toolloop.py        # NEW (R1): el bucle aislado y testeable (elegir→ejecutar→observar)
├── capabilities.py    # NEW (R6): mapa de capacidades generado DESDE el código
├── planner.py         # MOD (R1/R4): prompt consciente de tools reales y del orquestador
├── pipeline.py        # MOD (R4/R5): delegación al orquestador de proyecto + checkpoints
└── (resto sin cambios)

backend/app/tools/
└── aithera_tool.py    # NEW (R2): autogestión — Aithera opera sobre sí misma

backend/app/agents/
└── agent_manager.py   # MOD (R3): _run_execution deja de ser el placeholder de V0.5

backend/app/automation/
└── actions.py         # MOD (R3): AgentTaskAction → tie.submit_mission
```

Disciplina modular (doc 16): `aithera_tool.py` NO importa modelos SQL sueltos —
habla con `workspace_service`, `agent_manager`, `automation_engine` y las APIs
públicas de cada módulo. `toolloop.py` es interno de `app.tie`.

---

## 3. Sprints R1 → R7

### R1 — El bucle de tool-use (cierra Δ2, el hueco crítico)

**Objetivo**: que un nodo con herramientas disponibles las USE de verdad, con
datos reales, y que **cuando no pueda, lo diga en vez de inventar**.

**Archivos**: `app/tie/toolloop.py` (NEW), `app/tie/runtime.py` (MOD),
`app/tie/planner.py` (MOD, prompt), `tests/test_tie_toolloop.py` (NEW).

**Tareas**:
- **`toolloop.py`**: `run(task, tools, max_iters)` — construye el catálogo de
  acciones REALMENTE disponibles para ese nodo (intersección de `node.tools` con
  `tool_manager.list_tools()`, con sus params), se lo pasa al modelo vía
  `mel.complete(capability=AGENTIC)`, parsea `{"tool": {...}}` o `{"answer": "..."}`,
  ejecuta por el ToolManager (whitelist + timeout + auditoría intactos), inyecta
  la observación y repite. Máx 5 iteraciones (`TIE_TOOL_MAX_ITERS`).
- **Límite de seguridad acordado con el usuario (2026-07-18)**: el bucle ejecuta
  SOLO acciones con `requires_confirmation=False` (leer, listar, buscar,
  screenshot, procesos…). Si el modelo pide una sensible (enviar email, shell,
  PowerShell, clics de escritorio, borrar), **se rechaza con motivo** y el bucle
  se lo dice al modelo para que busque otra vía; el resultado final explica
  honestamente qué no se pudo hacer sin permiso. Las sensibles siguen pasando por
  el gate del plan (T4a) o del nodo (T3).
- **Honestidad estructural**: si tras `max_iters` no hay respuesta fundamentada,
  el nodo devuelve `success=False` con el detalle — **nunca** una respuesta
  inventada. La validación por nodo de T3 ya rechaza "éxito sin salida".
- **Presupuesto**: cada iteración cuenta contra `node.budget_ms`; el kill-switch
  de T3 sigue cancelando en vuelo.

**Tests**: el **test de regresión del hallazgo** (una tarea "lista los archivos
de X" DEBE ejecutar `filesystem.list_dir` y sus datos deben salir en la
respuesta — con un ToolManager real sobre una carpeta de prueba); acción
sensible rechazada sin ejecutarse; catálogo acotado a `node.tools`; sin tools
disponibles → camino de chat de siempre; el bucle nunca supera `max_iters`.

**Done**: la misión que hoy inventa 5 archivos, lista los reales.
**Modelo**: **Opus · Alto** (toca el runtime que ejecuta TODO y define el límite
de seguridad; un fallo aquí es ejecución no autorizada).

---

### R2 — Aithera se opera a sí misma (cierra Δ6)

**Objetivo**: todo lo que el usuario puede hacer en la UI, puede pedirlo por chat
(o voz): "créame un proyecto para X con estas tareas", "hazme un agente que
revise el email cada mañana", "avísame cada lunes a las 9".

**Archivos**: `app/tools/aithera_tool.py` (NEW), `app/tools/tool_manager.py`
(MOD: registro), `tests/test_aithera_tool.py` (NEW).

**Acciones** (todas ADAPTADORES sobre servicios existentes — cero lógica nueva):
| Acción | Delega en | Permiso (A3b) |
|---|---|---|
| `create_project` / `update_project` / `archive_project` | `workspace_service` | `workspace.write` |
| `create_milestone` / `complete_milestone` | `workspace_service` | `workspace.write` |
| `create_task` / `update_task` / `close_task` | `workspace_service` (con sus side effects y eventos) | `workspace.write` |
| `create_agent` / `update_agent` / `assign_tools` / `assign_skills` | `agent_manager` | `agent.execute` |
| `create_automation_rule` / `toggle_rule` | `automation_engine` + modelos del AE | `automation.rules` |
| `create_email_rule` | `EmailTool.add_auto_reply_rule` | `email.send` |
| `schedule_job` (cron: cada X min/h, diario a las HH:MM) | `scheduler_service` + `ScheduleTrigger` | `automation.rules` |
| `list_capabilities` | `capabilities.py` (R6) | — (lectura) |

- **Todas son `requires_confirmation=True`** salvo las de lectura: crear cosas en
  el sistema del usuario es un cambio de estado real. Con el permiso
  pre-autorizado (A3b) el gate se auto-resuelve dejando rastro — el mecanismo ya
  existe, aquí solo se usa.
- **Preguntar ante la duda** (petición del usuario): si faltan datos esenciales
  (p.ej. crear una tarea sin saber a qué proyecto), la acción devuelve un
  `needs_input` con la pregunta concreta en vez de inventar valores; el pipeline
  lo convierte en una pregunta por el camino corto (mismo patrón que la
  aclaración de alcance del override, E2b).

**Tests**: cada acción crea la entidad REAL y dispara los mismos eventos que la
UI; `needs_input` cuando falta lo esencial; permiso denegado → no se crea nada.

**Done**: "créame un proyecto 'Web nueva' con 3 tareas y un agente que las
revise" produce el proyecto, las tareas y el agente reales.
**Modelo**: **Sonnet · Alto** (muchas acciones, pero todas son adaptadores de
APIs ya probadas; el riesgo es de amplitud, no de profundidad).

---

### R3 — Agentes reales: `agent_manager` → TIE, y el AE → `submit_mission` (cierra Δ3, Δ4)

**Objetivo**: matar el placeholder de V0.5. Un agente con una tarea ejecuta una
misión real del TIE, con sus tools, su modelo y su frontera.

**Archivos**: `app/agents/agent_manager.py` (MOD), `app/automation/actions.py`
(MOD), `tests/test_agent_execution.py` (NEW).

**Tareas**:
- `_run_execution()` pasa a: construir el goal desde la tarea del usuario →
  `tie.submit_mission(goal, source="agent", project_id=agent.project_id)` →
  persistir el outcome y los `tool_calls` reales en `AgentExecution`. Se
  conservan `status`/`started_at`/`completed_at` y la cancelación (el
  kill-switch del TIE ya existe).
- **El agente aporta su contexto**: `allowed_tools` acota el catálogo del bucle
  (R1), `system_prompt` va al nodo, el modelo del agente se traduce a
  `model_hint` (el MEL ya sabe resolverlo, E2b).
- `AgentTaskAction` → `tie.submit_mission(..., source="automation")`. **Decisión
  de diseño**: se lanza en segundo plano y la acción devuelve el `mission_id` —
  una misión puede tardar minutos y el AE no puede bloquear su regla; el TIE ya
  tiene su propio rastro (`orchestrator_traces` + eventos `mission.*`), así que
  el outcome es auditable sin que el AE espere.

**Tests**: un agente con `filesystem` ejecuta una tarea real y sus `tool_calls`
quedan registrados; el placeholder ya no existe (test que falla si vuelve);
`AgentTaskAction` crea misión y no bloquea.

**Done**: la pantalla de agente (W2d/W2e) muestra pasos y resultados REALES.
**Modelo**: **Opus · Medio** (sustituye un motor de ejecución vivo; poco código,
alto impacto).

---

### R4 — Orquestador de proyecto (cierra Δ5, doc 14 §4.3c al pie de la letra)

**Objetivo**: cada proyecto puede tener su director de orquesta, con autoridad
acotada.

**Archivos**: `app/tie/pipeline.py` (MOD), `app/tie/planner.py` (MOD),
`app/tools/aithera_tool.py` (MOD: `create_orchestrator`),
`frontend/.../ProjectPopup.tsx` (MOD: ofrecer crearlo),
`tests/test_project_orchestrator.py` (NEW).

**Tareas**:
- **Delegación**: misión con `project_id` → si existe un `Agent` con
  `role="orchestrator"` y ese `project_id`, el pipeline delega en él antes de
  crear nada suelto (doc 14 §4.3c).
- **Frontera de autoridad (enforcement REAL, no comentario)**: el orquestador
  solo puede operar sobre agentes con su mismo `project_id` (nunca de otro
  proyecto ni `NULL`), y sus tools de filesystem/git quedan acotadas a
  `Project.repo_path` y carpetas añadidas. Se implementa como validación en el
  punto de ejecución, con test que intenta cruzar la frontera y falla.
- **Creación guiada**: al crear un proyecto, ofrecer crear su orquestador (mismo
  formulario de agente + flag). Nunca automático sin preguntar.
- **Equipos de agentes** (petición del usuario): el orquestador puede PROPONER
  un equipo para el proyecto (roles sugeridos según el objetivo) y, si el usuario
  acepta, crearlos con sus skills vía R2. La propuesta pasa por gate.

**Tests**: delegación cuando existe orquestador; frontera de autoridad
(intentar tocar un agente de otro proyecto → rechazado); propuesta de equipo no
crea nada sin aprobación.

**Done**: un proyecto con orquestador recibe la misión y reparte entre SUS
agentes, sin tocar nada de otro proyecto.
**Modelo**: **Opus · Alto** (frontera de seguridad + delegación; el enforcement
mal hecho es una fuga de autoridad entre proyectos).

---

### R5 — Flujo de trabajo: checkpoints verificables y avisos (cierra Δ7)

**Objetivo**: el flujo completo que pidió el usuario — orden → planificación con
milestones/tareas/agentes → ejecución → **parada en cada hito que el usuario
puede comprobar** → aviso por el canal elegido.

**Archivos**: `app/tie/contracts.py` (MOD: campo append-only), `app/tie/executor.py`
(MOD), `app/tie/pipeline.py` (MOD), `app/api/endpoints/tie.py` (MOD),
`frontend/.../Missions.tsx` (MOD), `tests/test_tie_checkpoints.py` (NEW).

**Tareas**:
- **`TaskNode.checkpoint: bool`** (extensión append-only del contrato congelado,
  con default `False` — permitido por la regla de evolución). El planner lo marca
  en los nodos cuyo resultado el usuario puede verificar (un entregable, no un
  paso interno). Al completarse un nodo `checkpoint`, la misión **pausa** y pide
  confirmación para seguir, mostrando lo hecho.
- **Reutiliza el mecanismo existente**: la pausa es el mismo `WAITING_APPROVAL`
  + `ApprovalGate` de T3 (kind `tie.checkpoint`), con su reanudación por evento y
  su recuperación tras reinicio. **Cero mecanismos nuevos de pausa.**
- **Notificaciones**: al abrir un gate/checkpoint, avisar por el canal preferido
  del usuario vía `gateway.notify()` (A1). Preferencia nueva en Ajustes: qué
  avisar (todo / solo lo que requiere decisión / nada) y por dónde (Telegram /
  solo en la app). El usuario puede responder desde Telegram para aprobar.
- **Cron desde el chat**: `schedule_job` (R2) permite "cada lunes a las 9
  revísame el email" — el AE + APScheduler ya lo soportan.

**Tests**: nodo checkpoint pausa y notifica; aprobar continúa desde donde estaba;
rechazar deja la misión parada con lo conseguido; preferencia "nada" no notifica.

**Done**: una misión larga se detiene en cada entregable, avisa por Telegram y
continúa al aprobar — sobreviviendo a un reinicio del backend.
**Modelo**: **Opus · Alto** (toca el executor y el contrato congelado).

---

### R6 — Aithera se conoce + navegación fluida (cierra Δ8, Δ9)

**Objetivo**: el chat sabe qué puede hacer y qué no, sin destapar su código; y
buscar/abrir/reproducir en la web es fluido.

**Archivos**: `app/tie/capabilities.py` (NEW), `app/services/chat_service.py`
(MOD), `app/tools/browser_tool.py` (MOD menor), `tests/test_capabilities.py` (NEW).

**Tareas**:
- **`capabilities.py`**: genera el mapa DESDE el código en vivo —
  `tool_manager.list_tools()` (14 tools/91 acciones), las páginas/funciones de la
  app, el estado de las integraciones (Google/Telegram/búsqueda conectados o no)
  y los permisos activos. **Generado, no escrito a mano**: una tool nueva aparece
  sola, sin que el prompt se quede obsoleto.
- **Frontera de confidencialidad (explícita del usuario)**: el mapa describe
  CAPACIDADES en lenguaje de usuario ("puedo leer y enviar emails", "puedo abrir
  páginas web"), nunca rutas de archivos, nombres de módulos, esquema de BD ni
  fragmentos de código. Regla en el system prompt + test que verifica que el
  bloque inyectado no contiene rutas ni nombres de clase.
- **Presupuesto**: el mapa se inyecta RESUMIDO (agrupado por área) para no comerse
  la ventana de contexto; el detalle de una tool concreta se consulta bajo demanda.
- **Navegación fluida**: flujo `search` (Brave/SerpAPI) → `browser.open_url` para
  abrir el resultado; reproducir vídeo/música = abrir la URL del servicio y usar
  los controles de la página. **Se documenta el límite real ya medido**:
  `browser.google_search` está bloqueado por Google en headless — el buscador es
  `search`, no el navegador.

**Tests**: el mapa incluye las 14 tools; una tool nueva aparece sin tocar el
prompt; el bloque inyectado no filtra rutas/módulos; flujo search→abrir.

**Done**: "¿qué sabes hacer?" responde con capacidades reales y actuales;
"búscame X y ábrelo" funciona de una tirada.
**Modelo**: **Sonnet · Alto** (mucha superficie, poca profundidad algorítmica;
la parte delicada —la frontera de confidencialidad— se blinda con un test).

---

### R7 — Cierre: tests de contrato, perf, verificación en vivo y bump `0.9.5`

**Archivos**: `tests/test_orquestrator_e2e.py` (NEW), `tests/test_tie_perf.py`
(MOD), docs (CLAUDE.md, doc 03, doc 11, doc 14), versión en las 3 ubicaciones
sincronizadas + los 3 `.bat`.

**Tareas**:
- **E2E con la cadena real** (mismo criterio que T5): un solo punto fake (la
  frontera del LLM), todo lo demás real — orden del usuario → plan → creación de
  proyecto/tareas/agente → ejecución con tools reales → checkpoint → aprobación →
  respuesta final.
- **Perf**: el bucle de tool-use no puede degradar el camino corto (~80% de las
  queries no lo tocan); presupuesto por iteración medido.
- **Auditoría de cabos sueltos** (obligatoria al cerrar bloque): docs 11/14/18
  actualizados contra el código real; anotar lo que quede diferido.
- **Verificación EN VIVO** contra el Postgres y los proveedores reales, con
  limpieza posterior confirmada.
- **Bump `0.9.2` → `0.9.5`** (decisión del usuario) + tag.

**Modelo**: **Opus · Alto** (cierre de bloque: es donde se cazan las
inconsistencias entre piezas).

---

## 4. Eventos (doc 17)

| Evento | Dirección | Cuándo |
|---|---|---|
| `mission.*` (started/completed/failed/cancelled) | ya se emiten (T4a) | sin cambios |
| `mission.checkpoint_reached` | **nuevo (R5)** | nodo `checkpoint` completado → notificación |
| `tool.executed` | **nuevo (R1)**, `{tool_id, action, ok, duration_ms}` | materia prima del Learner (doc 15) para `tool_stats` |
| `agent.execution_started/completed` | **nuevo (R3)** | la UI de agente deja de sondear a ciegas |
| `approval.requested/resolved` | ya existen (A1) | el checkpoint los reutiliza |

Regla de doc 17 respetada: un evento se añade **cuando su consumidor existe**.

---

## 5. Matriz de conexión (qué toca este bloque y qué NO)

| Sistema | Qué hace este bloque | Qué queda fuera |
|---|---|---|
| **ToolManager (14 tools)** | R1 las hace por fin alcanzables; R2 añade `aithera` | Tools nuevas de dominio |
| **MEL** | Consumidor: el bucle pide capacidad `AGENTIC`; los locales especializados ya reparten | MEL v2 (Learning/Recommendation, V1.2) |
| **WPMS** | R2 lo opera desde el chat; R4 el orquestador por proyecto | Vistas nuevas del Workspace |
| **Automation Engine** | R3 `AgentTaskAction`→misión; R2 crea reglas y cron desde el chat | Learner del AE (V1.2) |
| **MOS** | Sin cambios: el contexto ya llega por el enricher; los errores a `mem_error` | Compactación avanzada |
| **ApprovalGate + permisos** | R1 respeta el límite; R5 reutiliza el gate para checkpoints | Permisos nuevos |
| **Gateway/Telegram** | R5 usa `notify()` para avisos y aprobación remota | Canales nuevos |
| **Learner (V1.1)** | Deja `tool.executed` + trazas como materia prima | El Learner en sí |
| **Hermes (V1.1)** | El bucle vive en `NullRuntime`; Hermes traerá el suyo sin tocar el executor | HermesRuntime |
| **MVP-beta (O5)** | — | **Plan aparte**: instalador, auto-start, onboarding → `1.0.0` |
| **Escáner de hardware** | — | **Plan aparte**: recomendar modelo local por CPU/GPU/RAM |

---

## 6. Modelo y esfuerzo por sesión

| Sprint | Contenido | Modelo | Esfuerzo |
|---|---|---|---|
| **R1** | Bucle de tool-use + límite de seguridad | **Opus** | **Alto** |
| **R2** | Tools de autogestión de Aithera | **Sonnet** | **Alto** |
| **R3** | agent_manager → TIE + AE → submit_mission | **Opus** | **Medio** |
| **R4** | Orquestador de proyecto + frontera de autoridad | **Opus** | **Alto** |
| **R5** | Checkpoints verificables + notificaciones + cron | **Opus** | **Alto** |
| **R6** | Autoconocimiento + navegación fluida | **Sonnet** | **Alto** |
| **R7** | E2E + perf + auditoría + cierre `0.9.5` | **Opus** | **Alto** |

**Por qué Opus en R1/R4/R5**: son los tres sprints donde un error tiene
consecuencias reales — ejecutar una acción no autorizada (R1), cruzar la frontera
de autoridad entre proyectos (R4), o romper el contrato congelado del executor
(R5). R2 y R6 son amplios pero mecánicos sobre APIs ya probadas.

---

## 7. Criterios de cierre del bloque

1. **Cero alucinación con herramientas**: toda tarea que requiera una tool la
   ejecuta de verdad o explica por qué no pudo. El test de regresión del Δ2 pasa.
2. **Aithera se opera a sí misma** desde el chat: proyectos, tareas, milestones,
   agentes (con skills y tools), automatizaciones, reglas de email y cron jobs.
3. **Los agentes ejecutan de verdad**: el placeholder de V0.5 ya no existe.
4. **Orquestador por proyecto** con frontera de autoridad **probada**.
5. **Flujo completo con paradas**: la misión se detiene en cada hito verificable,
   avisa por el canal elegido, y reanuda tras aprobación (incluso tras reinicio).
6. **El chat conoce sus capacidades** sin filtrar código.
7. Suite verde, `tsc`/`build` limpios, verificación en vivo con limpieza, docs al
   día, **tag `v0.9.5`**.

---
*Plan 2026-07-18. Construido tras auditar el código real (10 deltas frente a los
docs, uno de ellos crítico: el TIE nunca había ejecutado una tool). Consume docs
11-B, 14, 10, 18, 11-A, 19, 17, 16. NO cubre MVP-beta (O5) ni el escáner de
hardware — planes aparte, por decisión del usuario.*
