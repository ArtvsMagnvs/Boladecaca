# 22 — Plan de sesiones detallado: MEL (Model Execution Layer) — V1.0

> **✅ BLOQUE CERRADO (2026-07-18)**: E1 · E1b · E2 · E2b HECHOS. Módulo
> `app/mel/` completo (contratos + registry + catálogo curado + auto-catálogo
> investigado + políticas Economy/Quality/Offline/Custom + Rule Engine + fallback
> + executor + overrides), el SWITCH de call-sites (grep-cero), pantalla
> Inteligencia con personalización + override explícito del usuario/pin de
> proyecto. 3 migraciones (20-22) aplicadas al Postgres real. Suite: 508 passed.
> Verificado en vivo. Detalle por sprint en `CLAUDE.md` §1. Sin bump (sigue
> `0.9.2`). Pendiente aparte: integración Orchestrator + MVP-beta → `1.0.0`.

> **Estatus**: plan de trabajo ejecutable, sprint por sprint, del **MEL v1** y
> SOLO del MEL. Deriva de doc 19 (diseño maestro del MEL, con los deltas de
> 2026-07-18 ya incorporados: auto-investigación de catálogo §5.4 y override
> explícito del usuario §7b), doc 17 (Event Bus, delta `provider.model_configured`),
> doc 14 (TIE/Cognitive Runtime, delta §3.5 — la mitad de la feature de override
> que le toca al TIE). Mismo rol que el doc 21 tuvo para el TIE: las decisiones ya
> están tomadas y verificadas contra el código real; esto las traduce a tareas
> concretas para que Opus/Sonnet no tengan que decidir arquitectura, solo
> implementarla.
>
> **Alcance EXCLUSIVO del MEL v1** (bloque E1-E1b-E2-E2b del roadmap, entre O4 y
> O5 de V1.0 — doc 03 §5). NO cubre: MEL v2 (Learning/Recommendation Engines,
> Custom builder, V1.2 — doc 19 §12), la **integración del Orchestrator de
> proyecto** (doc 14 §4.3c — esqueleto de datos ya existe, la delegación real es
> un plan aparte per CLAUDE.md), ni el MVP-beta (instalador/onboarding, O5). El
> MEL es la capa universal de ejecución de modelos: el resto del sistema pide
> CAPACIDADES, el MEL decide QUÉ MODELO.
>
> **Regla heredada (doc 11/14/16)**: el mejor diseño posible con la
> implementación MÍNIMA funcional. Contratos completos hoy (congelados); código
> solo el necesario. Sin sobreingeniería — en particular: **no se construye
> ninguna infraestructura de navegación web real en este plan** (§1 Δ7).
>
> **Verificación de este plan**: los tres documentos maestros (19/17/14) fueron
> revisados por un agente especializado (Multi-Agent Systems Architect) contra
> el código real ANTES de escribir este plan — 3 hallazgos reales corregidos
> (superficie pública del MEL inconsistente entre docs, hueco del camino corto
> con `model_hint`, cuarto alcance `Agent.agent_type` sin reconciliar). Ver §7.

---

## 1. Auditoría del código real (2026-07-18) — deltas frente a los docs

Antes de planificar, se auditó el estado REAL del repo (v0.9.2, TIE v1 T1-T5
cerrado). Correcciones a supuestos — **críticas para no repetir el patrón
"asumir que existe" que ya costó 3 incidentes de migración en el proyecto**:

| # | Supuesto de los docs | Realidad en el código (v0.9.2) | Consecuencia para el plan |
|---|---|---|---|
| Δ1 | doc 19 da por hecho que el módulo `app/mel/` existe como esqueleto | **NO existe** ningún `app/mel/` — cero archivos, cero tablas. Es diseño puro, nunca empezado a construir | **E1 lo crea todo desde cero**: contratos, registry, decision engine, esquema-primero (migración Alembic 20.ª) |
| Δ2 | doc 19 §5.3/§1.1 asume que `provider.connected`/`provider.model_added` ya se emiten | **NO existen** — verificado en `app/api/endpoints/ai.py` y `app/core/events.py`: ningún endpoint de proveedores emite nada al bus hoy | **E1b** los crea (un solo evento real y necesario: `provider.model_configured` — los demás de doc 19 §5.3 quedan pospuestos a MEL v2, cuando la reconfiguración automática por evento SÍ los necesite; doc 17 regla "sin catálogo especulativo") |
| Δ3 | doc 19 §1.1: `tie/router.py` "queda como shim de una línea que delega en el MEL desde E1" | **Confirmado en código real** (`app/tie/router.py`): ya está literalmente diseñado como fachada de ~30 líneas con el comentario `[Shim del MEL] En T2 delega en ai_manager.chat... E1: esta función se reescribe a mel.complete(...)`. El TIE v1 (T1-T5) se construyó SABIENDO que esto pasaría — cero sorpresas, cero refactor no anticipado | **E2** hace el cambio de una línea exacto que el propio código ya anuncia |
| Δ4 | doc 19 §1.1 dice que `AIManager` "pasa a ser el Provider Registry interno" sin más detalle | Verificado: `AIManager` (`app/ai/ai_manager.py`) ya tiene `current_provider`, `health_check()` cacheado, y **8 providers reales con clientes httpx persistentes** (doc 12 A2, ya cerrado en A2a) — el registry de E1 lo ENVUELVE, no lo reescribe. Cero trabajo de "hacerlo persistente", ya lo es | **E1** el registry es una capa fina de traducción `(capability→política) → ai_manager.chat()`, no una reimplementación |
| Δ5 | doc 14 §3.5 (antes del delta de hoy) no cubría el camino corto para overrides | **Hueco real confirmado por agente especializado**: `AgentTask.model_hint` existe en el contrato (`app/tie/runtime.py`) pero NADA lo rellena en `_short_path`/`handle_stream` (`app/tie/pipeline.py`) ni `NullRuntime.execute_task` lo pasa a `chat_service.answer()` (que hoy ni acepta ese parámetro) | **E2b** cierra esto explícitamente — ver doc 14 §3.5 delta y §3.3 de este plan |
| Δ6 | doc 19 §7b (antes del delta de hoy) no definía cómo se ESCRIBE un pin de proyecto, solo cómo se lee | La API pública del MEL en doc 19 §1.2 no listaba `resolve_model_name`/`set_project_override`/`overrides_for` | **Corregido en doc 19 §1.2 y §7b.1 antes de escribir este plan** (ver cabecera) — E2b los implementa tal como quedaron definidos |
| Δ7 | el usuario pide "una búsqueda automática... con buena skill de investigación" | **Verificado: cero infraestructura de navegación web en Aithera** (`grep` en `app/ai/providers/` y `app/tools/`: sin resultados; `browser.use`/`computer.use` siguen `available=False`, doc 20 A3b) | **E1b usa el conocimiento entrenado del modelo investigador**, no navegación en vivo — mismo método con el que hoy se cura el catálogo de doc 19 §5.1, automatizado y personalizado. Diseño honesto: el informe declara su propio nivel de confianza (§5.4.3) en vez de fingir una investigación que no ocurrió |
| Δ8 | `ApprovalGate.resolve()` — ¿sirve para la confirmación de alcance del override? | Verificado: `resolve(gate_id, approved: bool, note: str = "")` es estrictamente booleano (`app/automation/approval.py:159`) | **E2b NO reusa el ApprovalGate** para esto — es una aclaración conversacional de 2-3 vías (tarea/proyecto/ambiguo), no una aprobación sí/no de algo sensible. Se resuelve con una pregunta de camino corto normal (doc 14 §3.5 delta) |

**Lo que SÍ está listo y el MEL reusa tal cual** (cero trabajo nuevo): `AIManager`
con 8 providers + httpx persistente (doc 12 A2) + health-check cacheado;
`app/core/events.py` (bus, V0.85 M2); `ApprovalGate` (V0.9 A1 — NO se usa en este
plan, pero queda disponible si un futuro override necesitara aprobación real, p.ej.
un modelo de coste muy alto); `decision_service` (Decision API, V0.85 M1 + A4);
`app/tie/router.py` ya diseñado como shim de una línea (Δ3); `TaskNode.model_hint`
con rama "id concreto" (doc 14 §3.2/§3.5, ya en producción); patrón de referencias
cruzadas sueltas sin ForeignKey (`Milestone.project_id`, `Agent.project_id` — doc
18 W1/W2c) que `mel_overrides` reutiliza.

---

## 2. Estructura de código objetivo (doc 19 §1.2, actualizada con los deltas)

```
backend/app/mel/                     ← módulo nuevo (no existe hoy, Δ1)
├── __init__.py     # API pública: mel.complete(), mel.stream(), mel.policies(),
│                   #   mel.decision_trace(id), mel.resolve_model_name(text),
│                   #   mel.set_project_override(...), mel.overrides_for(project_id)
│                   #   NADA más es importable (doc 16)
├── contracts.py    # Capability, ExecutionRequest/Result (+model_override),
│                   #   Policy, DecisionTrace — CONGELADOS (E1)
├── capabilities.py # taxonomía (doc 19 §3, incluye RESEARCH activada) (E1)
├── registry.py     # Provider Registry (envuelve ai_manager, Δ4) +
│                   #   resolve_model_name() (E1 / E2b)
├── policies.py     # Economy/Quality/Offline + compilador (E1); Custom es V1.2
├── decision.py     # Rule Engine (E1) — precedencia override>proyecto>política (E2b)
├── fallback.py     # clasificación de fallos + circuit breakers (E1)
├── executor.py     # ejecución + streaming + registro async de mel_executions (E1)
├── catalog.py      # scores curados por (modelo, capacidad) — dato del repo (E1)
├── research.py     # Auto-Research Catalog (doc 19 §5.4) — job + prompt RESEARCH +
│                   #   mel_capability_reports (E1b)
└── overrides.py    # Override explícito del usuario (doc 19 §7b) — mel_overrides +
                    #   set_project_override/overrides_for (E2b)
```

Disciplina modular (doc 16): API pública SOLO en `__init__.py`; fronteras
vigiladas por `test_module_boundaries.py` extendido (`app.mel.*` internos). El
MEL **no importa** `app.tie`/`app.automation`/`app.memory`/`app.workspace` —
solo `app.core.events`, `app.core.config`, y `app.ai.ai_manager` (Δ4, exclusivo
del `registry.py`). El `learning.py`/`recommender.py` de doc 19 §1.2 (v2) NO se
crean en este plan — quedan fuera de alcance (MEL v2, V1.2).

---

## 3. Sprints E1 → E2b

### E1 — Contratos + capacidades + registry + Rule Engine + fallback/breakers + políticas

**Objetivo**: el MEL existe como módulo con sus contratos CONGELADOS, envuelve
`ai_manager` como Provider Registry, decide con un Rule Engine determinista
(<1 ms), tiene respaldos con circuit breakers, y compila las 3 políticas
automáticas (Economy/Quality/Offline) al primer arranque. **Sin conectar
todavía a nadie** (el switch de `tie/router.py` es E2).

**Archivos**: `app/mel/__init__.py` (NEW), `contracts.py`, `capabilities.py`,
`registry.py`, `policies.py`, `decision.py`, `fallback.py`, `executor.py`,
`catalog.py` (NEW, todos), `alembic/versions/*_v10_mel_schema.py` (NEW,
migración 20.ª — `mel_executions`), `app/db/database.py` (MOD si hace falta
columna auxiliar; `mel_executions` puede vivir como tabla propia del módulo,
igual que `orchestrator_traces` del TIE), `tests/test_mel_contracts.py`,
`tests/test_mel_decision.py`, `tests/test_module_boundaries.py` (MOD).

**Tareas**:
- **`contracts.py` CONGELADO** (doc 19 §2, con el campo `model_override` del
  delta): `Capability` (enum append-only, doc 19 §3 — incluye `RESEARCH` ya
  activada, Δ7/E1b la usa), `ExecutionRequest` (capability, prompt/messages,
  system_prompt, constraints, context_tags, policy_override, model_override),
  `ExecutionResult` (text, ok, error, served_by, usage, decision_id), `Policy`,
  `DecisionTrace`.
- **`capabilities.py`**: la taxonomía completa de doc 19 §3 (CLASSIFY, EXTRACT,
  SUMMARIZE, DRAFT, CHAT, REASON, CODE, ANALYZE, + RESEARCH/VISION/AGENTIC
  reservadas) + tabla de mapeo call-site→capability (la usa E2 al migrar).
- **`registry.py`**: envuelve `ai_manager` (Δ4) — `list_available()` (providers
  configurados + salud cacheada), `is_local(model)`, `resolve_model_name(text)`
  (§7b.2 — fuzzy-match contra `(provider, model)` reales; usado por E2b pero
  el método se define aquí porque pertenece al registry).
- **`policies.py`**: compilador (doc 19 §5.2) — al primer arranque o si no hay
  políticas persistidas, compila Economy/Quality/Offline desde `catalog.py` +
  `registry.list_available()`; persiste en tabla `mel_policies` (JSON
  versionado, `pristine=true`). Activa por defecto: Economy si hay ≥1 local
  sano, si no Quality.
- **`decision.py`** (Rule Engine, doc 19 §9.1): `decide(req) -> DecisionTrace`
  — lookup O(1) de la cadena de la política activa → primer candidato viable
  (breaker cerrado, no exhausted) → elegido. Ring buffer de 500 traces en
  memoria. **La rama de precedencia de `model_override`/proyecto se ESCRIBE
  aquí pero queda inactiva hasta E2b** (el campo existe en el contrato desde
  E1, con default `None` — nadie lo usa todavía, cero coste).
- **`fallback.py`** (doc 19 §8): tabla de clasificación de fallos → acción
  (9 filas de la tabla del doc) + circuit breakers en memoria por proveedor
  (closed→open≥3 fallos/60s→half-open tras 90s).
- **`executor.py`**: `mel.complete(req)`/`mel.stream(req)` — decide (Rule
  Engine) → ejecuta vía registry → si falla, aplica fallback → registra en
  `mel_executions` (async, fuera del hot path) → devuelve `ExecutionResult`.
- **Migración 20.ª**: `mel_executions` (capability, provider, model, ok,
  latencia, tokens, coste, reintentos, fallback_reason, decision_id,
  context_tags) + `mel_policies` (JSON versionado). Aditiva, aplicada al
  Postgres real en el mismo paso y verificada (la lección dura del proyecto,
  ya 3 incidentes previos por saltarse este paso).

**Tests**: contratos serializan/deserializan; Rule Engine determinista (misma
request + mismo estado ⇒ mismo modelo); circuit breaker abre a 3 fallos y
cierra tras sonda exitosa; compilador de políticas nunca produce cadena vacía
(con 1 solo proveedor, cadena de longitud 1, válido); `resolve_model_name`
resuelve nombres coloquiales reales y devuelve `None` ante uno inexistente;
`test_module_boundaries`: `app.mel.*` internos, barrel completo, nadie fuera de
`app/mel/` importa `ai_manager`/providers directamente salvo `registry.py`.

**Done**: `mel.complete(ExecutionRequest(capability=CHAT, prompt="hola"))`
responde de verdad contra el proveedor activo, con `DecisionTrace` consultable;
las 3 políticas están compiladas y persistidas; nada del resto del sistema
llama al MEL todavía (el switch es E2). Suite verde.

**Modelo sugerido**: **Opus · Alto** (contratos congelados + Rule Engine +
fallback son la base de todo lo demás — deben quedar bien a la primera).

---

### E1b — Catálogo auto-investigado por modelo conectado (doc 19 §5.4)

**Objetivo**: activar la capacidad `RESEARCH` de verdad — cuando el usuario
conecta o cambia un modelo, un job investiga sus capacidades reales (con el
conocimiento entrenado del mejor modelo disponible, Δ7 — sin navegación web) y
genera un informe consultable, con confianza declarada, que desplaza (nunca
sustituye de golpe) los scores curados del catálogo. Refresco cada 14 días.

**Archivos**: `app/mel/research.py` (NEW), `app/api/endpoints/ai.py` (MOD:
emitir `provider.model_configured`), `app/core/config.py` (MOD:
`MEL_RESEARCH_REFRESH_DAYS`, default 14), `alembic/versions/*_v10_mel_research.py`
(NEW, migración 21.ª — `mel_capability_reports`), `app/api/endpoints/mel.py`
(NEW, mínimo: `GET /api/mel/capability-report`), `tests/test_mel_research.py`.

**Tareas**:
- **Evento `provider.model_configured`** (doc 17 delta): `POST /configured` y
  `PUT /configured/{provider}` de `ai.py` emiten el evento cuando el
  `(provider, model)` resultante es nuevo o distinto — NO en
  activate/test/delete (nada que investigar ahí). Un `emit()` de una línea en
  cada endpoint, patrón ya usado en todo el proyecto.
- **`research.py`**: se suscribe a `provider.model_configured` (idempotente:
  si ya hay un informe de ese `(provider, model)` con <14 días, no hace nada).
  `investigate(provider, model)`: llama a `mel.complete(capability=RESEARCH,
  prompt=<pide scores 0-100 + justificación + confianza por cada capacidad de
  §3, JSON validado>)` — el Rule Engine (ya construido en E1) elige el mejor
  modelo disponible para RESEARCH, excluyendo el propio candidato investigado
  si es evitable. Parsea, valida contra schema, descarta con log si el JSON es
  inválido (nunca rompe el flujo de configurar un proveedor — best-effort,
  igual que toda escritura a memoria en el proyecto).
- **`mel_capability_reports`** (migración 21.ª): `provider, model, capability,
  score, rationale, confidence, researched_by_model, created_at`. Un informe
  con `confidence="bajo"` se guarda pero el compilador de políticas (E1) lo
  pondera menos al desplazar el score curado (mismo principio que el
  aprendizaje real de doc 19 §9.2: prior + cambio acotado, aunque el ciclo
  completo de aprendizaje con evidencia acumulada es MEL v2 — aquí solo se
  aplica un desplazamiento simple de un solo informe, sin historial).
- **Job de refresco** (APScheduler, cada `MEL_RESEARCH_REFRESH_DAYS` días):
  re-investiga TODOS los `(provider, model)` configurados actualmente (no solo
  los nuevos) — los proveedores cambian de versión sin avisar. Mismo patrón de
  job que `lifecycle.py`/`tie` mission cleanup: micro-batch, nunca bloquea el
  arranque, registra su propia ejecución.
- **`GET /api/mel/capability-report`**: devuelve, por modelo conectado, el
  resumen legible (prosa corta por modelo, agregando sus capacidades) — la
  pantalla Inteligencia → Modelos (E2b la construye del lado frontend,
  reutilizando este endpoint) lo consume.

**Tests**: el evento dispara la investigación (con `ai_manager`/`mel.complete`
fake, determinista, sin red); idempotencia (segunda config del mismo modelo en
<14 días no reinvestiga); JSON inválido no rompe el endpoint de configurar
proveedor; el job de refresco re-investiga modelos ya conocidos; el score
desplaza el catálogo curado con `confidence` baja pesando menos.

**Done**: conectar un proveedor real en Ajustes dispara una investigación real
en segundo plano (verificado en vivo contra el backend real — un
`(provider, model)` nuevo produce un informe consultable en minutos); el
endpoint del informe responde con datos reales. Suite verde.

**Modelo sugerido**: **Sonnet · Alto** (integración de un job + un evento +
una tabla — patrón ya repetido muchas veces en el proyecto, menos diseño
novel que E1).

---

### E2 — Migración de call-sites + wizard + pantalla Políticas

**Objetivo**: el resto del sistema deja de hablar con `ai_manager` directamente
y pasa a pedir capacidades al MEL. El switch exacto que `tie/router.py` ya
anuncia en su propio comentario (Δ3) se activa.

**Archivos**: `app/tie/router.py` (MOD: shim de una línea → `mel.complete`),
`app/services/chat_service.py` (MOD: `answer()`/`build_system_prompt` vía MEL —
**y gana el parámetro `model_override`, ver E2b/doc 14 §3.5 delta, aunque no se
active hasta E2b**), `app/services/email_service.py` o donde vivan
`llm_triage`/`generate_ai_reply`/`extract_meeting_datetime` (MOD), `app/memory/
summarizer.py` (MOD: intenta `policy_override="offline"` primero, como ya
documenta doc 19 §4), `frontend/.../Settings.tsx` (MOD: pestaña "Inteligencia"
mínima — política activa + 1 clic para cambiarla, doc 19 §11 punto 1 recortado
a lo mínimo viable), `tests/test_mel_migration.py`.

**Tareas**:
- **Migrar los ~9 call-sites** (doc 19 §12 E2, tabla de doc 19 §3 "call-sites
  reales hoy"): cada uno pasa de `ai_manager.chat(...)` a
  `mel.complete(ExecutionRequest(capability=X, ...))`. Se hace UNO POR UNO,
  verificado en vivo cada vez (mismo patrón de disciplina que toda migración
  de este proyecto) — no un cambio masivo de una vez.
- **`tie/router.py`**: el cambio de una línea que el propio archivo ya
  documenta en su comentario — `complete()` pasa a delegar en
  `mel.complete(ExecutionRequest(capability=capability, prompt=prompt,
  system_prompt=system_prompt))`. `fast()`/`smart()` quedan como hints de
  compatibilidad (nadie nuevo los llama; se retiran cuando E2 confirme que
  nada los usa).
- **Pantalla Políticas v1** (doc 19 §11, recortada — el builder Custom es
  V1.2): 3 tarjetas (Economy/Quality/Offline), la activa destacada, tabla
  capacidad→cadena por tarjeta, selector de política activa. Sin "Actividad"
  ni "Recomendaciones" todavía (V1.2).
- **Wizard**: NO se construye aquí — se integra en el sprint O5 (MVP-beta,
  plan aparte) tal como ya dice doc 19 §12; E2 solo deja el compilador (ya
  construido en E1) listo para que el wizard lo invoque.

**Tests**: cada call-site migrado produce el MISMO resultado observable que
antes (test de regresión por call-site — p.ej. el triaje de email sigue
categorizando igual); `tie/router.py` delega de verdad en `mel.complete`
(verificado con un mock que confirma la llamada, no solo que "no rompe");
suite completa sin regresión.

**Done**: los ~9 call-sites hablan con el MEL, no con `ai_manager` directo
(verificado por grep: cero `ai_manager.chat(` fuera de `app/mel/registry.py`);
la pantalla Políticas muestra la configuración real; verificado en vivo
contra el backend real (un mensaje de chat real, un triaje real, pasan por el
MEL y responden igual que antes). Suite verde.

**Modelo sugerido**: **Opus · Alto** (el switch es alto riesgo — todo el
sistema pasa a depender del MEL; cada call-site debe quedar idéntico en
comportamiento observable).

---

### E2b — Override explícito del usuario + confirmación de alcance (doc 19 §7b + doc 14 §3.5 delta)

**Objetivo**: si el usuario nombra un modelo concreto, esa elección manda sobre
el MEL — con el alcance (tarea vs. proyecto) confirmado, nunca asumido. Cierra
también el hueco real del camino corto detectado en la auditoría (Δ5).

**Archivos**: `app/mel/overrides.py` (NEW), `app/mel/decision.py` (MOD:
precedencia), `app/mel/__init__.py` (MOD: expone `resolve_model_name`/
`set_project_override`/`overrides_for`), `alembic/versions/*_v10_mel_overrides.py`
(NEW, migración 22.ª — `mel_overrides`), `app/tie/contracts.py` (MOD: `Intent`
gana `explicit_model: {name, scope} | None`, campo append-only), `app/tie/
intents.py` (MOD: prompt del clasificador detecta la petición), `app/tie/
pipeline.py` (MOD: rama `scope=="unspecified"` → pregunta de alcance sin gate;
`scope=="task"` → `TaskNode.model_hint` / `AgentTask.model_hint`; `scope==
"project"` → `mel.set_project_override`), `app/services/chat_service.py` (MOD:
`answer()` acepta y reenvía `model_override`), `app/tie/runtime.py` (MOD:
`NullRuntime.execute_task/stream_task` pasa `task.model_hint` a
`chat_service.answer(model_override=...)`), `frontend/.../Settings.tsx` (MOD:
pantalla Inteligencia → Modelos con informe de capacidades E1b + overrides
activos, borrables), `tests/test_mel_overrides.py`, `tests/test_tie_explicit_model.py`.

**Tareas**:
- **`overrides.py`**: `mel_overrides` (id, scope="project", project_id ix sin
  ForeignKey — mismo patrón que `Milestone.project_id`, capability nullable,
  model_id, source="user_explicit", created_at). `set_project_override(...)`/
  `overrides_for(project_id)` — expuestos en el barrel del MEL.
- **`decision.py` (MOD)**: precedencia real ahora activa —
  `req.model_override` (si presente) → `overrides_for(context_tags.project_id)`
  si hay pin de proyecto para esa capacidad → cadena de la política. Modelo no
  disponible → `ExplicitModelUnavailable` tipado (nunca sustitución silenciosa).
- **`Intent.explicit_model`** (doc 14 §3.5 delta): el clasificador (mismo
  prompt de siempre, sin llamada extra) detecta `{name, scope}` cuando el
  mensaje nombra un modelo. `scope` ∈ "task"|"project"|"unspecified".
- **Resolución de nombre**: `pipeline.py` llama a `mel.resolve_model_name(name)`
  ANTES de decidir nada — nombre no resuelto → responde con lo que sí hay
  configurado (nunca inventa un id).
- **`scope=="unspecified"`**: NO planifica/ejecuta ese turno — responde con la
  pregunta de alcance por el camino corto normal (sin ApprovalGate, Δ8). La
  respuesta del usuario en su siguiente mensaje ya trae contexto suficiente
  (el clasificador ve el historial reciente vía `chat_service.
  build_system_prompt`, sin estado nuevo). Ambigüedad persistente → alcance
  conservador (tarea única) + aviso de que puede pedir "para todo el proyecto".
- **`scope=="task"`, camino complejo**: `TaskNode.model_hint` = id resuelto (ya
  funciona en el executor, cero código nuevo ahí).
- **`scope=="task"`, camino corto** (cierra Δ5): `_short_path`/`handle_stream`
  pasan el id resuelto a `AgentTask.model_hint` → `NullRuntime` lo reenvía a
  `chat_service.answer(model_override=...)` → `ExecutionRequest.model_override`.
- **`scope=="project"`**: `mel.set_project_override(project_id, model_id,
  capability=None)` + registro en Decision API (`decision_service.
  store_decision`, mismo patrón que el planner con sus planes).
- **Pantalla Inteligencia → Modelos**: informe de capacidades (E1b) + lista de
  overrides de proyecto activos con botón borrar (nunca oculto).

**Tests** (`test_mel_overrides.py`): precedencia real
(override > proyecto > política); `ExplicitModelUnavailable` ante modelo no
disponible; `set_project_override`/`overrides_for` CRUD; `resolve_model_name`
con nombres coloquiales reales y uno inexistente.
(`test_tie_explicit_model.py`): el clasificador detecta `explicit_model` en
mensajes reales tipo prueba (`ai_manager` fake); `scope="unspecified"` responde
con la pregunta y NO crea misión ni ejecuta nada; `scope="task"` en camino
corto llega de verdad a `ExecutionRequest.model_override` (mock que lo
confirma, cerrando Δ5 con una prueba explícita); `scope="project"` llama a
`set_project_override` con el `project_id` correcto; nombre no resuelto
responde con las opciones reales, nunca inventa un id.

**Done**: pedir "usa DeepSeek para esto" en un mensaje simple hace que ESE
mensaje responda con DeepSeek de verdad (camino corto, Δ5 cerrado); pedir
"a partir de ahora todo este proyecto con Claude" pausa, pregunta si hace
falta, y al confirmar, las siguientes misiones de ese proyecto usan Claude sin
volver a preguntar; un nombre inventado responde con las opciones reales.
Verificado en vivo contra el backend real. Suite verde.

**Modelo sugerido**: **Opus · Alto** (toca el clasificador congelado del TIE +
la precedencia del Rule Engine del MEL a la vez — dos contratos congelados
tocándose en el mismo sprint, exige más cuidado que un sprint de un solo módulo).

---

## 4. Eventos que emite/consume el MEL (doc 17, con el delta de hoy)

| Evento | Dirección | Payload | Se usa en |
|---|---|---|---|
| `provider.model_configured` | emite (`source="ai"`) | `{provider, model}` | E1b — dispara la investigación |
| `mission.completed`/`mission.failed` (TIE) | consume (futuro, MEL v2) | — | NO en este plan — el Learning Engine que lo consumiría es V1.2 |
| `model.call_completed` (ya existía, doc 17 V1.0) | el MEL pasa a ser quien lo emite en la práctica (antes lo hacía implícitamente `ai_manager`) | `{provider, model, tokens, duration_ms, ok, purpose}` | Observabilidad general — sin cambio de contrato, solo cambia el emisor de facto tras E2 |

No se activan en este plan (quedan en doc 19 §5.3 para MEL v2, cuando la
reconfiguración automática por evento los necesite de verdad): `provider.
connected`/`provider.disconnected`/`provider.model_removed` — doc 17 regla
"sin catálogo especulativo": un evento se añade cuando su consumidor existe.

---

## 5. Matriz de conexión — TIE v1/v2/v3, Orchestrator, y todo lo demás

Verificado uno por uno contra el código y los docs reales, no asumido:

| Conector | Estado hoy | Qué hace este plan | Qué queda para después |
|---|---|---|---|
| **MEL ↔ TIE v1** (`tie/router.py`) | El shim YA existe, diseñado desde T2 sabiendo que esto pasaría (Δ3) | **E2**: el cambio de una línea que el propio código anuncia. **E2b**: `Intent`/`AgentTask`/`chat_service` ganan el camino del override explícito | — |
| **MEL ↔ TIE v2** (V1.2, doc 14 §3.5 "Router V1.2") | No construido — TIE v2 en sí no tiene plan de sesiones todavía | Nada en este plan directamente — pero el Rule Engine (E1) ya deja el punto de extensión: `model_stats`/`tool_stats` del Learner como tercer input de `decide()`, sin rediseño (doc 19 §9.2: MEL v2 = mismo `mel.complete()`, el Learning Engine solo reordena cadenas offline) | MEL v2 (V1.2, plan aparte) — Learning + Recommendation Engines sobre `mel_executions` + `model_stats` compartida con el Learner |
| **MEL ↔ TIE v3** (V1.5, "routing predictivo") | No construido | Nada — TIE v3 consumirá `DecisionTrace`/`served_by` que el MEL YA expone desde E1 (observabilidad, doc 19 §2) sin que el MEL necesite cambiar nada | Diseño de TIE v3 completo, cuando llegue V1.5 |
| **MEL ↔ Automation Engine** | El AE nunca ha importado `ai_manager` (frontera dura ya vigente, doc 11-A) | Ninguna conexión directa — el AE dispara `tie.submit_mission()` (doc 14 §4.2, ya construido); el MEL solo ve `ExecutionRequest`s que le llegan indirectamente vía el TIE. Confirmado: el MEL tampoco importa `app.automation` (doc 19 §13.1, frontera verificada) | — (nada pendiente, ya está bien cerrado) |
| **MEL ↔ Learner** | La tabla `model_stats` no existe (V1.1/V1.2) | Nada en este plan — doc 19 §9.2 ya diseña que el Learning Engine del MEL y el Learner ESCRIBEN la MISMA tabla, columnas distintas, cero solape de código | Construcción de `model_stats` (Learner V1.1) + Learning Engine (MEL v2) |
| **MEL ↔ WPMS** | `Project`/`Milestone` existen; `TaskNode.model_hint` y `Mission.project_id` ya pasan el dato | **E2b**: `mel_overrides.project_id` (entero suelto, mismo patrón) + `overrides_for(project_id)` consultado cuando la misión trae `source="workspace"` | — |
| **MEL ↔ "Orquestador de proyecto"** (doc 14 §4.3c, `Agent.role="orchestrator"`) | **Columna reservada, SIN lógica** — confirmado por grep: cero código de delegación real hoy | **Nada específico** — y es la decisión correcta: cuando ese orquestador exista (plan aparte, "integración Orchestrator" per CLAUDE.md), será OTRO caller de `tie.submit_mission`/`AgentRuntime`, exactamente como el AE o el usuario directo. El MEL nunca sabe quién originó la `ExecutionRequest` más allá de `context_tags` — no necesita casos especiales | La integración real del orquestador de proyecto (plan aparte, no MEL) |
| **MEL ↔ Hermes Runtime** (doc 10, V1.1) | NullRuntime es el único runtime hoy | Nada — un `AgentRuntime` nuevo (Hermes) ejecuta un nodo con lo que le inyectan (doc 10, principio ya vigente); si Hermes necesita un modelo, pide una capacidad al MEL igual que NullRuntime, por la misma `chat_service`/API. Sin caso especial | Registro de `"hermes"` en el Agent Factory (V1.1, plan aparte) |
| **MEL ↔ `Agent.agent_type`** (selección de modelo por agente, WPMS W2e) | Ya existe en la UI, sin conectar a ejecución real (NullRuntime no lo consulta) | **E2b, nota de precedencia only** (doc 19 §7b.1 delta): override explícito > modelo del Agent > pin de proyecto > política. No se activa código nuevo porque V1.0 no tiene agentes ejecutando nodos todavía | Activación real cuando V1.1 tenga runtimes que sí lean `Agent.agent_type` |
| **MEL ↔ Voz (STT/TTS)** | `app/voice/` con selección propia (ElevenLabs/eSpeak/Kokoro) | Ninguna — exclusión explícita ya en doc 19 §1 ("NO gestiona voz... capa `voice/` propia, con su propia selección") | Posible capacidad `VOICE` futura (doc 19 §12 V1.5+, "solo si aporta") |
| **MEL ↔ Gateway/canales** | El Gateway normaliza I/O, no toca modelos | Ninguna — ni directa ni indirecta; el Gateway nunca ha sabido de proveedores IA | — |

---

## 6. Tabla de modelo y esfuerzo recomendados por sprint

| Sprint | Contenido | Modelo | Esfuerzo |
|---|---|---|---|
| **E1** | Contratos + capacidades + registry + Rule Engine + fallback/breakers + políticas | **Opus** | **Alto** |
| **E1b** | Catálogo auto-investigado (evento + job + informe + refresco) | **Sonnet** | **Alto** |
| **E2** | Migración de ~9 call-sites + switch de `tie/router.py` + pantalla Políticas | **Opus** | **Alto** |
| **E2b** | Override explícito + confirmación de alcance (MEL + TIE a la vez) | **Opus** | **Alto** |

Estimación: 4.5-5 sesiones (frente a las 2-3 del doc 19 original — el
crecimiento es íntegramente las dos peticiones explícitas del usuario de esta
sesión, documentado en doc 19 §12 "Nota de alcance"). Mismo bloque del
roadmap (V1.0, entre O4 y O5); no se mueve de fase.

---

## 7. Verificación de este plan (trazabilidad)

Antes de escribir este documento, se leyeron completos: doc 19 (MEL, incluidos
los deltas de hoy), doc 17 (Event Bus), doc 14 (TIE/Cognitive Runtime,
completo — no solo el Model Router), doc 15 (Learning System, para confirmar
`model_stats` compartida), doc 03 (Roadmap, posición exacta de E1-E2 y de TIE
v2/v3), doc 21 (plan de sesiones del TIE, ya cerrado, como referencia de
formato). Se verificó contra el código real (no asumido): `app/tie/router.py`,
`app/tie/contracts.py`, `app/tie/runtime.py`, `app/tie/pipeline.py`,
`app/automation/approval.py`, `app/automation/models.py`, `app/core/events.py`,
`app/api/endpoints/ai.py`, `app/db/database.py` (`AIProviderConfig`,
`Milestone.project_id`, `Agent.project_id`/`agent_type`), `app/ai/providers/`
y `app/tools/` (confirmar ausencia de navegación web real).

Un agente especializado (**Multi-Agent Systems Architect**, del catálogo
curado en `AGENTES_ESPECIALIZADOS.md`) revisó adversarialmente los tres
documentos editados contra el código real ANTES de que este plan se
escribiera. Encontró 3 hallazgos reales, los 3 corregidos en doc 19/doc 14
antes de continuar (ver §1 Δ5/Δ6, y la nota de `Agent.agent_type` en doc 19
§7b.1): superficie pública del MEL inconsistente entre docs 19/14 (corregido:
`resolve_model_name`/`set_project_override`/`overrides_for` ahora en la lista
de §1.2), el camino corto sin forma de aplicar un override de alcance "tarea"
(corregido: doc 14 §3.5 delta ahora lo cubre explícitamente, con test dedicado
en E2b), y un cuarto alcance (`Agent.agent_type`) no reconciliado (corregido:
nota de precedencia en doc 19 §7b.1). Ningún hallazgo bloqueante.

---

*Plan derivado de doc 19 (MEL, Fable 5 2026-07-13 + deltas 2026-07-18) + doc 17
(Event Bus) + doc 14 (TIE/Cognitive Runtime) + doc 16 (disciplina modular).
Auditado contra el código REAL (v0.9.2), no solo contra los docs — ver §1
(8 deltas). Alcance EXCLUSIVO del MEL v1: MEL v2, TIE v2/v3, Hermes, Learner e
integración del Orchestrator de proyecto son planes aparte. Regla rectora:
mejor diseño, implementación mínima funcional. Honestidad sobre lo que existe
y lo que no (Δ7: sin navegación web real, declarado explícitamente en el
propio informe generado, nunca fingido).*
