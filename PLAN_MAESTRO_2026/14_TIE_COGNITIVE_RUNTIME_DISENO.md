# 14 — Cognitive Runtime: Task Intelligence Engine (TIE) y ecosistema

> **Origen**: briefing del usuario 2026-07-12 ("Cognitive Runtime Architecture").
> **Gobernado por**: doc 16 (Principios Maestros — NO frameworkitis).
> **Relación con los docs previos**: este documento **ABSORBE** la Parte B del doc 11
> (el "Orchestrator" de V1.0 pasa a ser el **perfil mínimo del TIE — TIE v1**; su
> diseño de 6 componentes sigue vigente palabra por palabra). Consume: 07/08 (MOS),
> 09+15 (Learning), 10 (AgentRuntime/Hermes), 11-A (Automation Engine/ApprovalGate).
> El MOS **no se rediseña aquí** (§4.1 lista los 4 únicos deltas que le pide).
>
> **Regla heredada del doc 11**: el mejor diseño posible con la implementación
> MÍNIMA funcional por versión. Contratos completos hoy; código solo el necesario.

---

## 0. Decisión de encaje en el roadmap (¿antes, durante o después del Automation Engine?)

**Respuesta: las tres, por partes — y el orden de fases NO cambia.**

| Qué | Cuándo | Por qué |
|---|---|---|
| **Contratos del TIE** (`Mission`, `TaskGraph`, `TaskNode`, `AgentRuntime`) | **ANTES** — congelados en este doc; stubs mínimos tocan V0.85 (§4.1) | V0.9 y V1.0 los consumen desde su primer día; definirlos después = migración |
| **Automation Engine** | **V0.9, antes del TIE, sin cambios de posición** | El AE aporta los dos prerrequisitos del TIE: **ApprovalGate** (los gates de nodos del grafo) y **APScheduler** (trabajos programados). Y el AE, por diseño (doc 11-A), no contiene inteligencia — no necesita al TIE para existir |
| **TIE v1 (núcleo)** | **V1.0 — absorbe el slot del Orchestrator** | Mismo alcance que el doc 11-B + el plan formalizado como grafo (§3.4). Desde aquí, `AgentTaskAction` del AE delega en el TIE: el AE dispara, el TIE piensa |
| **TIE v2 (grafo completo)** | V1.2 | Olas paralelas, replan, Cost Manager, Mission Manager persistente |
| **TIE v3 (reflexivo)** | V1.5 | Reflexión mid-mission, routing predictivo, multi-runtime |

La frase normativa del briefing — *"el Automation Engine debe usar el TIE para
planificar y no debe contener inteligencia propia"* — ya era la regla B.4 del doc
11. Queda ratificada: **el AE es músculo reflejo (triggers→condiciones→acciones
deterministas); el TIE es corteza (entender→planificar→ejecutar con juicio); el
Learner es hipocampo (consolidar); el MOS es la memoria misma.**

---

## 1. Benchmark — patrones extraídos

> Síntesis de: JWIKI (`06_AGENTS/` — agent-loops, approval-flows, sub-agents,
> handoffs-delegation, multi-agent-hierarchical, patterns-reflexion/CoT/ToT,
> tool-use — y `01_LANDSCAPE/`), doc 01 (benchmark JARVIS OSS) y conocimiento del
> landscape a 2026. No se copia ningún sistema; se extraen patrones (columna 3) y
> se registra qué se rechaza y por qué (columna 4).

### 1.1 Frameworks de agentes OSS

| Sistema | Idea central | Tomamos | Rechazamos |
|---|---|---|---|
| **LangGraph** | grafo de estado tipo Pregel: nodos-función, supersteps, checkpointer por thread, `interrupt()` HITL, `Send` para fan-out | checkpoint en frontera de nodo; interrupt ≡ ApprovalGate; ejecución por olas; estado explícito serializable | el framework como dependencia (decidido en doc 00 §4); grafo-como-código (queremos grafo-como-datos §1.5); channels/reducers genéricos |
| **AutoGen / AG2** | multi-agente conversacional (GroupChat + manager), núcleo event-driven | mensajes agente↔agente como envelopes (ya lo es el Gateway); el "manager" ≈ routing por capabilities del TIE | charla abierta entre agentes: quema tokens y es no-determinista — nuestros agentes se comunican por resultados de nodos, no por chat |
| **CrewAI** | roles + tareas + crew declarativos; procesos sequential/hierarchical | declarar tarea→agente como DATOS (nuestro `TaskNode.runtime`); plantillas de rol ≈ definición de skill | jerarquías de roles fijas; prompts enormes ocultos en la lib |
| **AutoGPT / BabyAGI / AgentGPT** | bucle autónomo: generar tareas → priorizar → ejecutar → repetir | la lección cautelar más valiosa del landscape: **un bucle sin presupuesto ni validación diverge**. De aquí salen `budget` y stop-conditions obligatorios por misión | el diseño entero (auto-prompting recursivo sin cuarentena) |
| **OpenHands** (ex-OpenDevin) | **event stream** como fuente única de verdad; runtime sandboxed; microagents/skills | el trace del TIE como registro de eventos append-only del que aprende el Learner; disciplina de sandbox ≈ nuestro ToolManager con whitelist | contenedores Docker (un usuario local; nuestra whitelist basta) |
| **OpenManus** | planner + executor separados, multi-agente con browser | confirmación del split plan/act: **planificar jamás ejecuta side effects** (ya regla 11-B) | — |
| **Semantic Kernel** | kernel + plugins-función; sus planners complejos fueron deprecados en favor de function-calling directo | la lección: **para intents simples, dejar que el modelo llame tools directamente vence a un planner** → nuestro "camino corto" (11 B.2) es exactamente eso | DI empresarial, abstracciones .NET-first |
| **LlamaIndex** | RAG-first: query engines, retrieval como centro | presupuestos de retrieval y pipelines de contexto (el MOS ya lo cubre) | agentes como envoltorio de retrieval (el TIE es más que RAG) |
| **Dify** | workflows visuales; el flujo es un JSON editable | **workflow-como-datos validable** — refuerza TaskGraph-as-data | plataforma/BaaS entera |
| **Haystack** | pipelines DAG con componentes de I/O tipado | validación del grafo en construcción (ciclos, tipos) ANTES de ejecutar | — |
| **SmolAgents** | minimalismo radical (~1k LOC); code-as-action | la vara de medir: si nuestro motor de grafos pasa de unas centenas de líneas, sobra algo | code-as-action (el LLM escribe código que se ejecuta — incompatible con principio 4 AOS "la IA razona, Aithera decide") |
| **PydanticAI** | agentes tipados; salida estructurada validada | **toda frontera LLM del TIE devuelve JSON validado contra schema** (el planner emite TaskGraph que se valida o se reintenta) | — |
| **OpenAI Agents SDK** | handoffs, guardrails, sessions, tracing de serie | handoff ≡ routing por `capabilities` entre AgentRuntimes; guardrails ≈ hooks de validación por nodo; tracing first-class (nuestro tracer ya lo era) | — |
| **Claude Agent SDK / Claude Code** | agent loop + subagentes aislados + hooks + permission modes + **skills como documentos declarativos** + compactación de contexto | permission modes ≡ ApprovalGate por herramienta; skills-como-markdown inspira el `definition` de LocalSkill; subagente = contexto aislado con retorno estructurado | — |
| **Hermes (Nous)** | agente auto-mejorable con generación de skills, local-first | ya integrado como runtime intercambiable (doc 10); su learning se captura vía adapters hacia el MOS/LSL | Hermes como núcleo (decisión inviolable doc 10) |

### 1.2 Asistentes personales

| Sistema | Tomamos |
|---|---|
| **OpenClaw** | gateway + envelope channel-agnostic (ya adoptado en V0.8, P2 del doc 00) |
| **Leon** | skills con manifiesto declarativo (trigger/dominio/acción separados) — eco en LocalSkill |
| **Mycroft / OVOS** | messagebus interno de eventos (nuestro `events.py`, doc 16 §4.3, es su versión in-process mínima); umbrales de confianza en intents (ya en 11 B.1: confidence < 0.55 → conversational) |
| **Home Assistant Assist** | su motor de automatizaciones triggers/conditions/actions **valida nuestra arquitectura del AE** (doc 11-A es isomorfo); blueprints compartibles = precedente de la GSN |
| **OpenJarvis** | routing barato/potente + traces (P5, ya adoptado) — detalle en doc 01 |

### 1.3 Sistemas cerrados (patrones observables)

| Sistema | Patrón observable adoptado |
|---|---|
| **ChatGPT Agent / Operator** | plan **visible e interrumpible** en todo momento; takeover del usuario → nuestro kill-switch de misión (§3.4.6) y el streaming de estado (11 B.5) |
| **Claude Code** | plan mode (aprobar plan antes de ejecutar) → UI de aprobación de planes (11, sprint O4); todo-list transparente ≈ vista del TaskGraph en el Hub |
| **Devin** | sesiones de horizonte largo con snapshots; su lección pública: coste por tarea y drift → presupuesto por misión + checkpoints por nodo |
| **Cursor / Windsurf** | la calidad del CONTEXTO vale más que el tamaño del modelo → ratifica que el Context Builder del TIE es una llamada al MOS, no un componente propio |
| **Manus** | misiones asíncronas orientadas a ENTREGABLE (goal → deliverable explícito) → campo `goal` verificable por nodo y `outcome` por misión |

### 1.4 Los 10 patrones ganadores (síntesis) y 5 antipatrones

**Patrones** (todos incorporados en §3):
1. Plan-como-datos: el grafo es JSON serializable, validado contra schema, inspeccionable.
2. Checkpoint en frontera de nodo; reanudar = recalcular el conjunto "ready".
3. HITL como ESTADO de primera clase (`WAITING_APPROVAL`), no como excepción.
4. Modelo barato primero, con umbral de confianza; potente solo si hace falta.
5. Trace/event-stream como fuente de verdad — el Learner aprende de él, no de logs.
6. Skills declarativas, versionadas, con evidencia (doc 09/15).
7. Presupuestos en todo (tokens/tiempo/coste) con stop-conditions por misión.
8. Routing por capabilities entre runtimes (handoffs sin acoplamiento).
9. Salida estructurada validada por schema en TODA frontera LLM.
10. El aprendizaje PROPONE, nunca aplica (cuarentena + evidencia — doc 15).

**Antipatrones** (prohibidos): bucles autónomos sin presupuesto; grafo-como-código
acoplado a un framework; charla libre entre agentes; plataformización (construir
para usuarios que no existen); "reflection theater" (reflexionar sin persistir
consecuencia alguna).

### 1.5 LangGraph a fondo → nuestro Graph Execution Engine propio

Qué hace LangGraph por dentro y qué hacemos nosotros:

| Concepto LangGraph | Qué es | Decisión Aithera |
|---|---|---|
| `StateGraph` + nodos-función | el grafo se define EN código Python; los nodos son funciones que mutan un estado compartido | **Grafo-como-DATOS**: `TaskGraph` es una estructura serializable que produce el Planner (un LLM con schema). Los "nodos-función" son siempre el mismo ejecutor genérico: `runtime.execute_task(node, ...)` |
| Channels + reducers | mecanismo genérico de merge de estado concurrente | NO — sobreingeniería para nuestro caso: cada nodo escribe SOLO su `result`; los dependientes leen resultados de sus dependencias. Sin estado compartido mutable = sin reducers |
| Supersteps (Pregel) | ejecuta en ondas los nodos cuyo input está listo | SÍ (V1.2): olas = `nodos READY` → `asyncio.gather` con semáforo. V1.0: la ola es de tamaño 1 (secuencial) — mismo algoritmo, distinta concurrencia |
| Checkpointer (thread_id) | estado completo persistido por hilo de conversación, permite time-travel | Versión mínima: cada transición de estado de nodo = un UPDATE del JSON del grafo en la fila de la misión/trace. Reanudar = cargar grafo + recomputar READY. Sin time-travel (nadie lo pidió) |
| `interrupt()` | pausa la ejecución esperando input humano, sobrevive a reinicios | ≡ **ApprovalGate de V0.9** (doc 11 A.2) — ya diseñado persistente y reanudable. El TIE lo RECIBE, no lo reimplementa |
| `Send` API | fan-out dinámico (map-reduce) | V1.2+: el Planner puede emitir nodos "template" que el executor expande (p.ej. "para cada email urgente → nodo respuesta"). Diseñado, no implementado antes |
| Conditional edges | ramas según el output de un nodo | V1.0: NO (grafos estáticos post-plan). V1.2: replan de subárbol (§3.4.5) cubre el 90% del valor con la mitad de complejidad |

**Coste del motor propio**: el corazón (validación DAG + Kahn/topological + loop de
olas + transiciones persistidas) son ~200-300 líneas de Python sin dependencias
(ni NetworkX: un dict + in-degree count). Es MENOS código que integrar y fijar
versión de un framework — y es exactamente la parte que queremos poseer.

---

## 2. El ecosistema — mapa de responsabilidades (quién hace qué y qué NUNCA hace)

```
                                USUARIO (cualquier canal)
                                        │
                                   GATEWAY (V0.8) — normaliza; no piensa
                                        │  envelope
                                        ▼
   AUTOMATION ENGINE (V0.9) ─────▶   T I E (V1.0) ◀──────────── contratos congelados aquí
   triggers/condiciones/acciones     entiende → planifica →      │
   deterministas; ApprovalGate;      ejecuta el grafo            │ elige runtime por capabilities
   APScheduler. dispara misiones ──▶ (Goal→Plan→Graph→Exec)      ▼
   NUNCA decide objetivos                │  │              AGENT RUNTIME (doc 10)
                                         │  │              NullRuntime | HermesRuntime | ...
                             contexto ◀──┘  └──▶ tools     ejecuta UN nodo; recibe memoria/
                                 │               (whitelist  tools/gate por inyección
                                 ▼                + gates)   NUNCA gestiona memoria propia
                            M O S (V0.85)
                            recuerda, conecta, destila           LEARNER (V1.0→V1.5, doc 15)
                            NUNCA planifica ni ejecuta  ◀─────── analiza traces/errores/feedback;
                                 ▲                               propone skills/mejoras/docs
                                 │ Skill API                     NUNCA aplica sin validación
                            SKILL SYSTEM (LSL, doc 09)
                            almacena/ejecuta skills versionadas
```

Tabla normativa (extiende el Principio 8 del doc 16):

| Módulo | Hace | NUNCA hace |
|---|---|---|
| MOS | almacenar, indexar, recuperar, resumir, destilar, olvidar | planificar, ejecutar, aprender (el Learner aprende; el MOS guarda lo aprendido) |
| TIE | entender el objetivo, planificar, construir/ejecutar el grafo, enrutar modelo/runtime, monitorizar, trazar | almacenar memoria (delega en MOS), automatizar por tiempo/evento (AE), aprender (Learner), hablar con canales (Gateway) |
| AE | disparar por schedule/evento, evaluar condiciones, ejecutar acciones deterministas, gestionar aprobaciones (ApprovalGate) | decidir objetivos, planificar (delega en TIE), aprender (su Learner de V1.2 es el módulo Learner) |
| AgentRuntime | ejecutar UN nodo/tarea con lo que le inyectan | persistir nada propio; ejecutar tools sin gate |
| Learner | observar, analizar, PROPONER (skills, mejoras, docs, pins) | planificar, aplicar cambios sin validación, tocar canales |
| Skill System | ciclo de vida y ejecución de skills | crear skills por su cuenta (las propone el Learner o el usuario) |
| Gateway | normalizar I/O de canales | cualquier lógica de negocio |

---

## 3. TIE — arquitectura

### 3.1 Los 15 componentes del briefing → realidad sin frameworkitis

El briefing pide 15 componentes. Aplicando el doc 16 (cada pieza justifica su
existencia), quedan **9 unidades de código, 2 se eliminan por redundantes y 4 se
difieren como políticas/columnas** (no módulos) hasta tener datos:

| Componente pedido | Dónde vive | Versión | Nota |
|---|---|---|---|
| Goal Analyzer | `app/tie/intents.py` | V1.0 | = Intent Classifier (11 B.1) + extracción de objetivo verificable; misiones multi-objetivo en V1.2 |
| Planner | `app/tie/planner.py` | V1.0 | modelo potente solo si `requires_planning`; emite TaskGraph validado por schema |
| Task Graph Builder | salida del Planner + `graph.py` | V1.0 | construir+validar (ciclos, tools existentes, schema) es una función, no un módulo |
| **Graph Execution Engine** | `app/tie/graph.py` + `executor.py` | V1.0 (lineal) → V1.2 (olas) | §3.4 — el corazón propio inspirado en LangGraph |
| Scheduler | dentro de `executor.py` (olas) | V1.2 | el scheduling TEMPORAL es del AE (APScheduler); el TIE solo ordena olas del grafo. Dos schedulers separados a propósito |
| Context Builder | `app/tie/enricher.py` → Context API del MOS | V1.0 | ya diseñado (11 B.1); por nodo usa `node.context_query` |
| ~~Memory Bridge~~ | **ELIMINADO** | — | ya existe: se llama `memory_router` (MOS). Un puente hacia un puente es frameworkitis |
| Reflection Engine | módulo **Learner** (doc 15 §5) | V1.1 → V1.5 | la reflexión con consecuencias persistidas es aprendizaje → vive en el Learner; el executor solo valida resultados por nodo (barato) |
| Recovery Manager | políticas en `executor.py` | V1.0 (degradar) → V1.2 (retry/replan) | §3.4.5 |
| Cost Manager | columnas en nodo/misión + agregación del tracer; política de presupuesto | V1.0 (medir) → V1.2 (imponer) | primero DATOS, luego política — jamás al revés |
| Model Router | `app/tie/router.py` (política sobre `ai_manager`) | V1.0 | fast/smart por nodo (11 B.3) + hint por nodo; cost-aware y stats del Learner en V1.2 |
| ~~Tool Router~~ | **ELIMINADO** | — | ya existe: `ToolManager` + whitelist por nodo (`node.tools`). No hay nada que "rutear" |
| Agent Factory | registro `{nombre: AgentRuntime}` en `runtime.py` | V1.0 | una factoría real solo cuando haya runtimes con construcción costosa (V1.2 multi-instancia) |
| Execution Monitor | `app/tie/tracer.py` + streaming de estado | V1.0 | ya diseñado (11 B.1/B.5); en V1.2 emite `mission.*` events + vista del grafo en el Hub |
| Mission Manager | `app/tie/missions.py` + tabla `missions` | V1.2 | en V1.0 misión ≡ 1 trace (implícita) — ver §3.6 |

Estructura de código resultante (evolución directa de 11 B.1; el módulo se llama
`app/tie/` — "Orchestrator" queda como nombre histórico del pipeline v1):

```
backend/app/tie/
├── __init__.py     # API pública: tie.handle(envelope), tie.submit_mission(...), contratos
├── contracts.py    # Mission, TaskGraph, TaskNode, NodeState (§3.3) — CONGELADOS
├── intents.py      # 1. Goal/Intent (barato-siempre)          [11 B.1 sin cambios]
├── enricher.py     # 2. Context Builder → MOS                 [11 B.1 sin cambios]
├── planner.py      # 3. Planner → TaskGraph validado          [11 B.1 + salida grafo]
├── graph.py        # 4a. estructura + validación DAG + ready-set (motor propio §3.4)
├── executor.py     # 4b. ejecución por olas + checkpoints + gates + recovery
├── router.py       # 5. Model Router (política sobre ai_manager)
├── responder.py    # 6. Response Builder                      [11 B.1 sin cambios]
├── tracer.py       # 7. traces + espejo Decision API + eventos [11 B.1 sin cambios]
├── missions.py     # 8. Mission Manager (V1.2; antes: misión implícita)
└── runtime.py      # AgentRuntime + NullRuntime + registro     [doc 10 sin cambios]
```

### 3.2 Contratos (contracts.py) — CONGELADOS

Regla idéntica a la del MOS: **el contrato completo hoy; cada campo indica desde
qué versión se usa de verdad**. Los campos no activos llevan default y nadie los
lee hasta su versión — cero coste, cero migración futura.

```python
class NodeState(str, Enum):
    PENDING = "pending"                  # aún con dependencias sin cumplir
    READY = "ready"                      # dependencias DONE; elegible para ejecutar
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"  # en manos del ApprovalGate (persiste/reanuda)
    WAITING_EVENT = "waiting_event"        # V1.2 — espera un evento (AE flows)
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"                  # dependencia falló y la política fue degradar
    CANCELLED = "cancelled"              # kill-switch del usuario


@dataclass
class TaskNode:
    # — identidad y grafo (V1.0) —
    id: str
    goal: str                        # objetivo imperativo y VERIFICABLE del nodo
    depends_on: list[str] = field(default_factory=list)   # las aristas: el grafo ES esto
    # — qué necesita (V1.0; None = decide el executor con defaults) —
    context_query: str | None = None      # memoria requerida → Context API del MOS
    memory_types: list[str] | None = None # filtro de tipos MOS para el contexto
    skills: list[str] = field(default_factory=list)       # skills LSL recomendadas (V1.1)
    tools: list[str] = field(default_factory=list)        # whitelist de tools DEL NODO
    runtime: str | None = None            # agente recomendado ("null"|"hermes"|...) (V1.1)
    model_hint: str | None = None         # "fast" | "smart" | id concreto
    # — prioridad y presupuestos (medir V1.0; imponer V1.2) —
    priority: int = 0
    budget_tokens: int | None = None
    budget_ms: int | None = None
    est_duration_ms: int | None = None
    est_cost: float | None = None
    # — control (V1.0) —
    approval_required: bool = False       # → ApprovalGate (V0.9)
    max_retries: int = 0                  # política real en V1.2
    # — estado y resultado (los escribe SOLO el executor) —
    state: NodeState = NodeState.PENDING
    confidence: float | None = None       # confianza del planner en el nodo
    result: dict | None = None            # salida estructurada del runtime
    validation: dict | None = None        # {"ok": bool, "method": "schema|llm|user", "notes": str}
    tokens: int | None = None             # coste real medido
    cost: float | None = None
    duration_ms: int | None = None
    error: str | None = None


@dataclass
class TaskGraph:
    id: str
    mission_id: str
    nodes: dict[str, TaskNode]            # el grafo completo, serializable a JSON
    created_by: str                       # "planner" | "user" | "automation" | "learner"
    state: str = "draft"                  # draft|approved|running|done|failed|cancelled
    # invariantes (validadas al construir): DAG sin ciclos; depends_on solo a ids
    # existentes; tools de cada nodo ⊆ catálogo ToolManager; schema Pydantic válido.


@dataclass
class Mission:
    id: str
    goal: str                             # el objetivo del usuario, con entregable explícito
    source: str                           # "user" | "automation" | "learner"
    channel: str | None                   # canal de origen (para responder por él)
    state: str = "running"                # running|waiting|done|failed|cancelled
    graph_ids: list[str] = field(default_factory=list)   # V1.0: exactamente 1
    budget_tokens: int | None = None      # imponer en V1.2
    spent_tokens: int = 0
    outcome: str | None = None            # resumen del resultado (lo escribe el responder)
    reflection_id: str | None = None      # → aprendizaje post-misión (doc 15 §4)
```

Mapeo con el doc 11-B: `Plan` → `TaskGraph`; `PlanStep {id, description, tool,
params, depends_on[], can_parallelize, approval_required}` → `TaskNode` (description
→ goal; tool/params → tools + result contract; can_parallelize desaparece: la
paralelizabilidad se DERIVA del grafo, no se declara). La regla de tamaño se
mantiene: **2-3 nodos por defecto; >5 para una query simple = bug del planner.**

Persistencia: V1.0 — el JSON del grafo vive en `orchestrator_traces` (columna
`plan`, ya prevista) y se actualiza en cada transición. V1.2 — tablas `missions` y
`task_graphs` propias (migración mecánica: el shape ya es este).

### 3.3 Flujo completo (el pipeline del briefing, aterrizado)

```
Usuario (o AE, o Learner)
  ↓ envelope / submit_mission(goal, source)
TIE.intents  — clasifica (barato) + pre-fetch de contexto en paralelo (11 B.2)
  ↓ conversational/simple ──▶ CAMINO CORTO: NullRuntime → respuesta  (~80% de queries; sin grafo)
  ↓ complejo
TIE.planner  — (potente) emite TaskGraph validado; Decision API registra plan+alternativas
  ↓ si algún nodo approval_required de alto impacto → UI plan-approval (sprint O4)
TIE.executor — loop de olas: READY → gate? → runtime.execute_task(node, memory, tools, gate)
  │             cada transición → checkpoint (persistir grafo) + streaming de estado al canal
  │             nodo DONE → validation hook → resultado disponible para dependientes
  ↓ grafo done/failed/cancelled
TIE.responder — sintetiza outcome → Gateway → usuario
TIE.tracer   — trace completo + espejo Decision API + emite `mission.completed`
  ↓ (evento, asíncrono — fuera del critical path)
LEARNER      — Mission Learning (doc 15 §4): qué funcionó, qué recordar, qué skill proponer
  ↓ propuestas validadas (cuarentena doc 15 §3)
MOS          — consolida: skills (LSL), decisiones, contexto de proyecto, pins
  ↓
Knowledge Evolution (doc 15 §7) — dedup, contradicciones, obsolescencia
  ↓
PRÓXIMA MISIÓN — el planner y el router arrancan con mejor contexto, mejores skills
                 y estadísticas de modelo/herramienta (el bucle se cierra)
```

### 3.4 Graph Execution Engine — especificación

1. **Construcción/validación** (`graph.py`): al recibir el grafo del planner —
   chequeo de ciclos (Kahn), ids consistentes, tools existentes en el catálogo,
   schema Pydantic. Grafo inválido → 1 reintento del planner con el error como
   feedback → si falla, degradar a camino corto + avisar. Nada se ejecuta antes
   de validar (planning sin side effects, regla 11-B).
2. **Loop de ejecución** (`executor.py`): `ready = nodos PENDING con todas sus
   depends_on en DONE`. V1.0: se ejecuta UNO por iteración (orden determinista:
   prioridad desc, id asc). V1.2: toda la ola con `asyncio.gather` + semáforo
   (`TIE_MAX_PARALLEL`, default 3).
3. **Checkpoint**: CADA transición de estado persiste el grafo serializado (un
   UPDATE por transición; decenas por misión — coste trivial). Reanudar tras
   reinicio = cargar grafos en estado `running|waiting_*` en el lifespan y
   recomputar READY. Es el mismo patrón de persistencia/reanudación del
   ApprovalGate (11 A.2) aplicado al grafo entero.
4. **Gates**: nodo con `approval_required` → `WAITING_APPROVAL` + ApprovalGate
   (V0.9, reusado tal cual). La resolución (evento `approval.resolved`) reactiva
   el loop. El nodo puede esperar horas/días: el grafo está en disco.
5. **Recovery** (política por versión): V1.0 — nodo FAILED → dependientes SKIPPED
   + responder entrega lo conseguido + explicación (degradación graciosa, regla
   11-B) + `mem_error`. V1.2 — `max_retries` con backoff; si agota, **replan de
   subárbol**: el planner recibe el grafo + el fallo y re-emite SOLO los nodos
   no-DONE (los DONE son inmutables — no se repite trabajo).
6. **Kill-switch**: el usuario puede cancelar una misión desde el Hub/Telegram en
   cualquier estado → nodos RUNNING reciben cancelación cooperativa (timeout del
   runtime), el resto → CANCELLED, el responder informa de lo parcial. (Patrón
   ChatGPT Agent §1.3 — obligatorio para confianza del usuario.)
7. **Validación por nodo** (validation hook, barato): al terminar un nodo, se
   valida el `result` — V1.0: contra schema/reglas deterministas (¿hay output?
   ¿shape correcto?); V1.2: verificación LLM barata SOLO si el nodo la declara
   (`validation.method="llm"`). El resultado se escribe en `node.validation` —
   materia prima del Learner, jamás teatro.

### 3.5 Model Router + Cost Manager (políticas, no módulos)

- **Router V1.0** (= 11 B.3): `fast_model`/`smart_model` en Settings; intent y
  camino corto usan fast; planner usa smart; cada nodo puede traer `model_hint`.
  Salud del proveedor vía `ai_manager` (health-check cacheado existente).
- **Router V1.2**: se añade la estadística del Learner (`model_stats` por
  dominio/tipo de nodo: éxito, latencia, coste — doc 15 §4) como tercer input.
  La política sigue siendo una función pura de ~30 líneas: `choose(node, intent,
  stats, health) → model_id`. Si algún día hace falta más, será porque los DATOS
  lo digan.
- **Cost V1.0**: medir siempre (`tokens/cost/duration` por nodo, agregado por
  misión en el tracer). **Cost V1.2**: presupuesto por misión (`budget_tokens`);
  al 80% → aviso en el streaming de estado; al 100% → pausa + gate ("llevo X
  tokens, ¿continúo?"). Presupuesto default por `source`: automation < user.

### 3.6 Mission Manager

- **V1.0**: misión implícita — 1 query compleja = 1 misión = 1 grafo = 1 fila de
  trace. `Mission` existe como dataclass (contratos §3.2) pero no hay tabla.
- **V1.2**: tabla `missions` + `tie.submit_mission()` público; misiones
  multi-grafo (replan encadena grafos bajo la misma misión); misiones de larga
  duración creadas por el AE (`MissionAction` sustituye a `AgentTaskAction` para
  flujos complejos); panel de misiones en el Hub (activas, esperando aprobación,
  historial); reanudación tras reinicio (§3.4.3).
- **V1.5**: misiones recurrentes con memoria de misión previa (el Learner inyecta
  "la última vez esto falló por X") y priorización entre misiones concurrentes.

---

## 4. Integraciones

### 4.1 TIE ↔ MOS — y los 4 únicos deltas que este diseño pide al MOS

El TIE consume el MOS EXCLUSIVAMENTE por sus APIs públicas (doc 08 RFC-002):
`context()` (enricher y por-nodo), `search/store` (resultados de nodos con
`source="tie"`), Decision API (planes y aprobaciones), Skill API (V1.1). El estado
de ejecución (grafos, misiones) **NO vive en el MOS** — es estado operativo del
TIE en SQL (Principio 8: el MOS recuerda conocimiento, no ejecuta ni gestiona
ejecuciones). Al MOS solo llegan los DESTILADOS: outcome, decisiones, errores,
aprendizajes.

**Deltas para V0.85 (avisar antes de empezar el MOS — ya aplicados a los docs 07/09):**

| # | Delta | Dónde | Coste |
|---|---|---|---|
| 1 | `LocalSkill` +2 campos de linaje: `derived_from: list[str]`, `superseded_by: str \| None` (Skill Evolution, doc 15 §6) | doc 09 §1.1 → stub `skill_store.py` de M1 | 2 campos en metadata del stub |
| 2 | tabla `decisions` + columna `mission_id (str, null, ix)` | doc 07 §5 → migración de M1 | 1 columna nullable |
| 3 | `app/core/events.py` (pub/sub in-process; spec canónica: **doc 17**); la ingesta emite `memory.ingested` / `email.triaged` | doc 07 §6 → sprint M2 | ≤80 líneas + 2 emits |
| 4 | disciplina modular: API pública en `app/memory/__init__.py` + `test_module_boundaries.py` | doc 16 §4 → sprint M1 | ~1 h |
| — | **Lo que NO cambia**: `IMemoryStore`, `MemoryRouter`, `MemoryType` (sin tipos nuevos), ingesta, summarizer, briefing, compactación, posición de V0.85 en el roadmap | | |

### 4.2 TIE ↔ Automation Engine

- **El AE dispara; el TIE piensa.** Desde V1.0, `AgentTaskAction` delega en
  `tie.submit_mission(goal, source="automation")` (ratifica 11 B.4). Las demás
  acciones del AE (telegram_message, email_summary...) siguen siendo deterministas
  y NO pasan por el TIE — meter un LLM donde basta una plantilla viola la Regla
  de Oro.
- El AE puede: crear misiones (V1.0), programar trabajos (APScheduler, suyo),
  esperar eventos (`events.py`), reanudar procesos (ApprovalGate persistente),
  interrumpir (kill-switch expuesto por el TIE), encadenar (V1.2
  `ChainedRuleAction` + `WAITING_EVENT` en nodos).
- Frontera dura: el AE no importa `ai_manager` ni construye prompts. Si una regla
  "necesita redactar", su acción delega en el TIE con un goal.

### 4.3 TIE ↔ AgentRuntime (doc 10, sin cambios)

El "Agent Factory" del briefing es el registro `{nombre: AgentRuntime}` +
selección por `capabilities` (11 B, doc 10 §1). El runtime ejecuta UN nodo con
memoria/tools/gate inyectados. V1.0: NullRuntime. V1.1: HermesRuntime. V1.2:
multi-instancia por perfil. Nada del doc 10 cambia; solo la ruta del módulo
(`app/orchestrator/runtime.py` → `app/tie/runtime.py`).

### 4.3b TIE ↔ WPMS (doc 18)

El WPMS (V0.87) da el QUÉ; el TIE produce el CÓMO. Una Task del Workspace puede
"enviarse al TIE" → `tie.submit_mission(goal=task.title+desc, source="workspace")`;
el TIE la divide en un TaskGraph cuyos nodos son pasos de ejecución EFÍMEROS (no
son Tasks del WPMS — no se persisten en el Workspace). Al cerrar, el TIE escribe
`mission_id` en `task.links`. El planner usa `priority`+`due_date`+`depends_on`
del WPMS como señales; el enricher inyecta contexto de proyecto vía
`context(memory_types=[PROJECT])`. Frontera dura: el TIE no edita el Workspace
(eso es del usuario o del AE vía `WorkspaceAction`); solo lo lee y anota el enlace.

### 4.4 TIE ↔ Learner (doc 15)

Contacto en exactamente 3 puntos, todos asíncronos y fuera del critical path:
(1) el tracer emite `mission.completed` → Mission Learning; (2) el Learner
publica `model_stats`/`tool_stats` que el router lee (V1.2); (3) las skills que
el Learner valida aparecen en la LSL y el planner las recomienda en `node.skills`
(V1.1). El Learner JAMÁS modifica un grafo en vuelo.

---

## 5. Incorporación por versión

| Componente | V0.85 | V0.9 | V1.0 (TIE v1) | V1.1 | V1.2 (TIE v2) | V1.5 (TIE v3) |
|---|---|---|---|---|---|---|
| Contratos (contracts.py) | diseño | diseño | ✅ congelados en código | ✅ | ✅ | ✅ |
| Intents + camino corto | — | — | ✅ | ✅ | ✅ | ✅ +predictivo |
| Planner → TaskGraph | — | — | ✅ (2-3 nodos) | ✅ | ✅ +replan | ✅ +multi-obj |
| Graph engine | — | — | ✅ lineal (ola=1) | ✅ | ✅ olas paralelas | ✅ |
| Checkpoint/resume | — | (ApprovalGate A1) | ✅ por transición | ✅ | ✅ +reanudación lifespan | ✅ |
| Gates por nodo | — | ✅ primitivo nace | ✅ reusado | ✅ | ✅ | ✅ |
| Recovery | — | — | degradar | degradar | ✅ retry+replan subárbol | ✅ |
| Model Router | — | — | ✅ fast/smart+hint | ✅ | ✅ +stats Learner | ✅ cost-aware pleno |
| Cost | — | — | medir | medir | ✅ presupuestos duros | ✅ |
| Missions | — | — | implícita (=trace) | implícita | ✅ tabla+panel+AE | ✅ recurrentes |
| Validación por nodo | — | — | schema/determinista | ✅ | ✅ +LLM opcional | ✅ |
| Kill-switch | — | — | ✅ | ✅ | ✅ | ✅ |
| Eventos (`mission.*`) | (events.py nace) | ✅ AE los usa | ✅ emite | ✅ Learner consume | ✅ | ✅ |
| Runtimes | — | — | NullRuntime | +Hermes | +multi-instancia | +nativo si procede |

Sprints V1.0: los O1-O5 del doc 11 se mantienen tal cual con dos ajustes de
alcance — O1 incluye `contracts.py` + `graph.py` (validación DAG); O3 el executor
es el loop de olas (tamaño 1) con checkpoint por transición y kill-switch. Coste
estimado sin cambios (5-6 sesiones): el grafo lineal es el MISMO trabajo que el
executor secuencial que ya estaba previsto, con mejor estructura de datos.

## 6. Performance (hereda doc 12 §4; nuevos presupuestos)

| Operación | Target | Máximo |
|---|---|---|
| Validación de grafo (build) | < 10 ms | 50 ms |
| Transición de estado + checkpoint | < 20 ms | 100 ms |
| Overhead del engine por nodo (sin contar el trabajo del nodo) | < 50 ms | 200 ms |
| Reanudación de grafos al arrancar | < 500 ms | 2 s |
| Kill-switch → nodos parados | < 2 s | 10 s |

Los presupuestos de intent/enrich/plan/feedback del doc 12 §4 siguen vinculando.
El camino corto garantiza que el ~80% de interacciones NUNCA paga el coste del
planner ni del grafo — el usuario del chat no nota que el TIE existe (Principio 16).

## 7. Revisión crítica obligatoria (el arquitecto hostil)

1. **¿Sobreingenierizado?** En el briefing, sí — y se ha recortado: Memory Bridge
   y Tool Router eliminados (eran nombres, no componentes); Mission Manager
   diferido a V1.2 (V1.0: misión=trace); Scheduler propio del TIE reducido a olas
   (el temporal es del AE); Cost Manager reducido a columnas+política; Agent
   Factory reducido a un dict. 15 componentes → 9 unidades de código.
2. **¿Qué faltaba en el briefing?** Validación de resultados por nodo (§3.4.7),
   kill-switch de misión (§3.4.6), reintento-del-planner ante grafo inválido, y
   presupuestos de overhead del propio engine (§6). Añadidos.
3. **¿Qué simplificar aún?** El grafo V1.0 es lineal degenerado — misma estructura
   de datos, cero concurrencia. Si en V1.2 los datos muestran que casi ningún plan
   tiene ramas paralelas reales, las olas se quedan en el cajón sin coste hundido.
4. **¿Dependencias innecesarias?** Cero nuevas: ni LangGraph ni NetworkX (Kahn en
   ~40 líneas). El TIE depende solo de MOS/tools/ai/gateway por APIs públicas.
5. **¿Cuellos de botella?** (a) el planner LLM (≤3 s presupuesto; el camino corto
   lo evita en ~80%); (b) `context()` bajo carga (presupuesto+caché ya en 11 B.2);
   (c) el cuello REAL y deseado: el humano en los gates — por diseño (HITL).
   El checkpoint por transición es trivial (decenas de UPDATEs por misión).
6. **¿Cientos de agentes?** No es el caso de uso (un usuario — Principio 6 AOS).
   El semáforo de olas + presupuesto por misión acota. Si llegara: el grafo es
   datos serializables — repartible sin rediseño. No se construye hoy (P14).
7. **¿Miles de skills?** Problema del Skill System/Learner, no del TIE: búsqueda
   semántica escala; el caché RAM completo deja de valer >~2k skills → LRU parcial
   (nota en doc 15 §6). El anti-proliferación es el merge/dedup del Learner.
8. **¿Años de memoria?** RFC-007 (compactación) ya lo cubre. El riesgo real es
   calidad de recuperación, no volumen → se añade un benchmark periódico de
   retrieval con corpus sintético a la suite perf (doc 12 §6).
9. **¿Riesgos del aprendizaje automático?** Tratados en doc 15 §10 (contaminación,
   bucles de retroalimentación, privacidad, coste, confianza del usuario).
10. **¿Rediseñar algo por completo?** No estructuralmente. La mayor tentación era
    un runtime de grafos genérico multi-tenant "para el futuro" — rechazado: es
    exactamente el Ferrari convertido en Kubernetes (doc 16, Regla de Oro).
11. **¿Existe una arquitectura claramente superior?** Para UN usuario local, la
    convergencia observable del landscape (OpenHands, LangGraph, Claude Code,
    Agents SDK) es: trace-como-verdad + plan-como-datos + gates + routing barato/
    potente. Es esta. La alternativa "sin planner, todo function-calling" (SK
    moderno) está INCORPORADA como camino corto — el híbrido domina a ambas puras.
12. **¿Qué cambiaría un arquitecto principal de OpenAI/Anthropic/Microsoft?**
    (a) Exigiría **evals**: una suite de misiones canónicas de regresión (mission
    evals) que corra antes de cada release — ADOPTADO para V1.2 (doc 15 §9);
    (b) guardrails tipados en toda frontera LLM — ya adoptado (patrón 9);
    (c) mataría el Cost Manager hasta tener datos de coste reales — ya hecho
    (medir V1.0, imponer V1.2); (d) pediría que el grafo fuera visible al usuario
    — adoptado (streaming de estado + vista en Hub V1.2).

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| El planner emite grafos malos (demasiados nodos, goals vagos) | schema + regla de tamaño + reintento con feedback + camino corto como fallback; mission evals (V1.2) |
| Deriva de misiones largas (drift estilo Devin) | checkpoints + presupuesto + validación por nodo + kill-switch |
| El TIE se convierte en god-module | fronteras del doc 16 §4 vigiladas por test; Learner/AE/MOS fuera de él |
| Doble mantenimiento Orchestrator/TIE en docs | resuelto: 11-B queda como perfil v1; este doc es la fuente para lo demás; notas cruzadas añadidas |
| Latencia percibida en queries simples | camino corto sin grafo (~80%) + streaming de estado inmediato |

---
*Diseño 2026-07-12 (Fable 5). Absorbe 11-B (Orchestrator = TIE v1). Compañeros:
15 (Learning System), 16 (principios). Deltas al MOS: §4.1 — aplicados a 07/09.*
