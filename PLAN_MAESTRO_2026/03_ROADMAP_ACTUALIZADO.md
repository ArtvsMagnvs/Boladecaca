# Roadmap definitivo — V0.8 → V2.0+ (Plan Maestro 2.0)

> Reescrito 2026-07-09 (Fable 5) integrando los diseños de `FABLE5_PROMPTS/` 01-07.
> **Revisión 2026-07-12**: Cognitive Runtime integrado — **14** TIE (absorbe el
> Orchestrator de 11-B como "TIE v1") · **15** Learning System (extiende 09) ·
> **16** Principios Modulares (NO frameworkitis — gobierna a todos). El ORDEN de
> fases no cambia; cambian contenidos de V1.0/V1.2/V1.5 y 4 deltas menores en V0.85.
> Los principios 1-8 del AOS siguen vigentes e inviolables. Documentos de diseño:
> **07** MOS V0.85 · **08** MOS arquitectura completa · **09** LSL/LLL · **10** Hermes
> · **11** Automation+Orchestrator · **12** Auditoría/optimización · **13** AVCS
> (sistema visual) · **14** TIE/Cognitive Runtime · **15** Learning System ·
> **16** Principios Modulares · **17** Event Bus/Observabilidad · **18** WPMS/Workspace · **19** MEL/Model Execution Layer.
>
> **La estrella polar**: V1.0 es un **MVP bien hecho — completamente autónomo y
> distribuible a usuarios BETA** — alcanzable en semanas, no meses. Todo lo que no
> sea necesario para eso se diseña hoy (contratos/stubs) y se implementa después.

---

## 0. Filosofía ACI (la capa por encima del roadmap)

- **ACI (Aithera Cognitive Infrastructure)**: memoria + skills + tools +
  automatización + orquestación. Diseñada para sobrevivir a cualquier LLM o runtime.
- **Principios Modulares (doc 16)**: cada gran sistema (MOS, TIE, Learner, AE,
  Skills, Gateway, AVCS) es una librería interna del monorepo — API pública por
  `__init__.py`, llamadas directas en memoria (nunca HTTP interno), fronteras
  vigiladas por `test_module_boundaries.py`. Prioridad sobre todo RFC.
- **MOS (Memory Operating System)**: el subsistema de memoria de la ACI (docs 07/08).
  **La memoria pertenece a Aithera, nunca al runtime.** El MOS recuerda; jamás
  planifica ni ejecuta.
- **TIE (Task Intelligence Engine, doc 14)**: el cerebro de planificación/ejecución
  — entiende el objetivo, produce un **TaskGraph** (plan-como-datos) y lo ejecuta
  con checkpoints, gates y presupuestos. V1.0 = "TIE v1" (el Orchestrator de 11-B).
- **Learner (Aithera Learning System, doc 15)**: observa traces/errores/feedback y
  PROPONE skills, mejoras y conocimiento — siempre con cuarentena de validación.
  Nunca aplica nada solo.
- **`AgentRuntime`** (doc 10): el mecanismo de extensión para motores de agentes —
  Hermes, futuros runtimes o uno nativo son implementaciones intercambiables, igual
  que los 8 proveedores del AIManager.
- **Autosuficiencia local** (doc 09): Aithera sin red = completa. La red (GSN/CIE,
  V2.0+) amplifica; jamás es prerrequisito.
- **Adaptabilidad tecnológica** (08 RFC-006): toda capa de memoria puede cambiar de
  motor (Chroma→Qdrant→lo que venga) con dual-write + tests de contrato, sin tocar
  a los consumidores. **Compactación** (08 RFC-007): la memoria se destila, no crece
  sin límite.

## 1. ✅ HECHO — V0.7.x y V0.8 (estado real del código)

- **V0.7.3 Email Assistant TERMINADO**: 7 routers, triaje 2 etapas, autonomía
  gradual, ai_prompt, digest, responder desde alertas, 120+ tests.
- **V0.8**: Gateway + MessageEnvelope (patrón OpenClaw) · canal Telegram ·
  hardening (CORS, DPAPI para API keys y token TG) · B21 (reasoning filter) ·
  voz (STT Whisper, TTS multi-proveedor, conversación continua) · Hub responsivo.
- Pendientes menores heredados: PIN/token de red y cliente Web+PWA → **post-V1.0**.

## 2. V0.82 / V0.83 — Voz + Hub: **AVCS Fase 0 "Génesis"** (diseño: doc 13)

Última puesta a punto de voz y Hub, con el nacimiento del **Aithera Visual
Consciousness System** (especificación completa en `13_AVCS_DISENO_MAESTRO.md`):

1. **Semilla + Ondas de Sincronía** con el motor de partículas real (ParticleEngine
   GPGPU mínimo + ShaderSystem + RhythmEngine) — sustituye a la esfera `AICore.tsx`.
2. Ritmos iniciales: **Reposo** (respiración orgánica nunca idéntica), **Escucha**
   simple (el campo se hunde, primeras raíces insinuadas) y **Comunicación** simple
   (la energía asciende y late con la voz de Aithera vía audioLevel).
3. **Sin clipping**: canvas full-bleed, cámara fit-contain +12% de margen y falloff
   de borde — la energía nunca queda cortada por arriba/abajo/laterales (13 §13.3).
4. **Modo Presencia**: botón (+ tecla) que pliega TODA la UI y deja solo el
   organismo visual; segundo clic/Esc restaura (13 §13.4).
5. **Chat limpio**: presencia central + panel lateral flotante (~380 px) con
   historial, input y botones de voz/conversación (13 §13.5).
6. PerformanceManager v0 (tiers Q1-Q3 manuales + escalado dinámico básico).

Se mantiene: remate de voces ElevenLabs + STT (V0.83), quitar `PROFESSIONAL_VOICES`
hardcodeadas (doc 12 A6) y el sprint perf-front (lazy Three.js/code-splitting) —
misma zona de código, mismo momento.
**Cierre**: test de presencia superado (13 §21.1). ~3-4 sesiones.

## 3. ✅ V0.85 — MOS Skeleton — CERRADA (tag `v0.8.5`) (diseño completo: doc 07)

**Opción B**: arquitectura definitiva, implementación mínima. En una frase: se
construye la columna vertebral de la memoria (interfaces `IMemoryStore`/`MemoryRouter`
+ 5 tipos de memoria + tabla `decisions`) y sobre ella la funcionalidad: ingesta de
email/calendario cada 20 min, resumen nocturno Ollama-first, contexto con atribución
de fuente en el chat, `GET /api/memory/briefing`, compactación mínima (dedup +
presupuesto), vault opcional.

- Sprints M1-M5 (5-6 sesiones), criterios de cierre por sprint en doc 07 §10.
- Incluye las optimizaciones P1 de doc 12 (init de ChromaDB en background, índices).
- **[Δ 2026-07-12]** 4 deltas del Cognitive Runtime (14 §4.1, ya en doc 07):
  `LocalSkill` con linaje en el stub · `decisions.mission_id` · `app/core/events.py`
  + emisión desde la ingesta (spec canónica: doc 17) · disciplina modular
  (doc 16 §4) desde M1. Contratos `IMemoryStore`/`MemoryRouter`/`MemoryType`
  intactos.
- **Cierre de fase**: "¿qué me ha llegado importante hoy?" responde desde memoria
  local con Gmail desconectado. Tag `v0.8.5`.
- Handoff garantizado a V0.9: briefing estable, `context()` ≤ 300 ms, `decisions`
  lista, jobs asyncio migrables a APScheduler, eventos operativos.
- **✅ ESTADO (2026-07-13): M1-M5 completos, fase cerrada.** Criterio de cierre
  verificado (test automatizado + backend real del usuario). M5 confirmó en
  vivo el arranque no bloqueante (9 s de carga de ChromaDB ya no bloquean a
  uvicorn) y añadió 8 índices de rendimiento. Suite: 232 passed, 0 skipped.
  Detalle completo por sprint en `CLAUDE.md` §1. Diferido a propósito a V0.9
  (fuera del alcance literal de la fila M5 de doc 07 §10): compactación/
  `lifecycle.py` (08 RFC-007), `httpx` con conexiones persistentes (doc 12 A2).

## 3b. V0.87 — WPMS: Workspace & Project Management System (diseño completo: doc 18)

El sistema operativo del trabajo: la capa donde usuario y Aithera organizan
proyectos, milestones (por versión) y tareas. **Estado operativo en SQL; el
conocimiento sigue en el MOS** (`mem_project`) — el WPMS es la representación
operativa del Project Memory, nunca una segunda memoria.

- **Extiende** los modelos `Project`/`Task` reales (no reescritura) + entidad nueva
  `Milestone` (eje de versión) + `checklist`/`depends_on`/`links` en Task. Una
  migración Alembic aditiva; rutas `/api/projects` y `/api/tasks` intactas.
- **Progreso automático** por conteo de tareas (nunca manual); versionado
  `current_version` + milestone activo; docs como enlaces (repo/roadmap), sin
  duplicar. UI vara-Linear: Vista Proyecto de una columna + popup Task + atajos.
- **Integra**: escribe destilados a `mem_project` por evento (MOS); el TIE
  planifica hacia el milestone activo y escribe `mission_id` en las tareas; el AE
  gana `WorkspaceAction` (stub V0.9); el Learner mide estimado vs real; el
  briefing lee el WPMS (estado sin Gmail/LLM en caliente). Emite `task.*`/
  `milestone.*` al Event Bus (doc 17).
- **Impacto MOS**: nulo en contratos — solo convierte `mem_project` de stub a
  escritor real (doc 18 §0). Sprints W1-W3 (~2-3 sesiones). Tag `v0.8.7`.

## 4. V0.9 — Automation Engine + ApprovalGate (diseño completo: doc 11 parte A)

Arquitectura de 4 capas (Triggers/Conditions/Actions/Learner) con MVP funcional:

- **ApprovalGate genérico** persistente y reanudable — EL primitivo que reusan
  Orchestrator, Hermes y skills. La confirmación de email migra a él.
- Triggers Schedule+Event (reactivos sobre la ingesta del MOS — cero polling
  propio), condiciones composables con cooldown/ventana horaria, 4 acciones.
- **Integración MOS obligatoria**: `daily_briefing` consume `/api/memory/briefing`
  (sin Gmail en caliente); resultados → Automation Memory; aprobaciones → Decision
  API; errores → Error Memory. APScheduler entra aquí y absorbe los jobs de V0.85.
- **[Δ 2026-07-13] Deuda de V0.85 recogida explícitamente en A2** (antes solo
  mencionada en la nota de cierre de §3, sin sprint asignado — corregido):
  `lifecycle.py` se **construye** aquí (no se "migra": nunca existió, quedó
  fuera a propósito del alcance literal de M5) con dedup semántico +
  presupuesto `MEMORY_BUDGET_MB` + roll-up (diseño en doc 08 RFC-007); y
  `httpx` con conexiones persistentes por proveedor IA (doc 12 A2, `AsyncClient`
  reutilizado en vez de uno nuevo por request). Ambos entran en A2 por ser
  trabajo de infraestructura de jobs/engine, el mismo sprint que trae APScheduler.
- Reglas predefinidas (off por defecto): daily_briefing, system_monitor,
  urgent_email_alert, email_summary, agent_task. UI de reglas + aprobaciones.
- **[Δ]** Posición ratificada por el doc 14 §0: el AE va ANTES del TIE porque
  aporta sus dos prerrequisitos (ApprovalGate = gates de nodos; APScheduler) y
  porque el AE, por diseño, no contiene inteligencia — desde V1.0 `AgentTaskAction`
  delega en el TIE. `EventTrigger` se suscribe a los eventos que la ingesta de
  V0.85 ya emite (cero polling, cero retro-instrumentación).
- Sprints A1-A4 (4-5 sesiones). Stubs listos para V1.2: PatternTrigger,
  MemoryTrigger, AutomationLearner (= módulo Learner, doc 15), ChainedRuleAction.
  Tag `v0.9`.

## 5. V1.0 — **TIE v1** (Orchestrator) + **MVP BETA distribuible** (docs 14 + 11-B)

El cerebro: los 6 componentes de 11-B (Intent Classifier barato-siempre → Context
Enricher con pre-fetch/caché → Task Planner potente-solo-si-hace-falta → Executor
con gates → Response Builder → Tracer con Decision API), ahora como módulo
`app/tie/` con los contratos congelados del doc 14: el plan es un **TaskGraph**
(grafo dirigido serializable; en V1.0 lineal — ola de tamaño 1), checkpoint por
transición de nodo, kill-switch de misión, validación determinista por nodo y
camino corto conversational (~80% de queries sin grafo ni planner). `AgentRuntime`
+ `NullRuntime` (doc 10) — V1.0 es completo SIN Hermes. LLL básico (doc 09):
detección de tareas repetidas → propuesta de skills con cuarentena (doc 15 §3).
Enganche: `gateway.set_handler(tie.handle)`.

**[Δ 2026-07-15] Orquestador por proyecto** (pedido del usuario, esqueleto ya
dejado en W2e del WPMS — doc 14 §4.3c tiene el diseño completo): cada proyecto
podrá tener un `Agent` con `role="orchestrator"` cuya autoridad se limita a los
agentes de ESE proyecto y a las carpetas que el usuario le haya añadido — nunca
al resto del sistema. La columna `Agent.role` ya existe (V0.87, nullable, sin
lógica); V1.0 implementa la delegación real y, opcionalmente, la creación
guiada del orquestador al crear un proyecto.

**Definición de "MVP beta" (criterios de release, sprint O5)**:

1. Instalador NSIS con **auto-start del backend desde Electron** (doc 12 B6) —
   un beta tester hace doble clic y funciona.
2. Onboarding mínimo: primer arranque guía API keys/Ollama, Google OAuth opcional,
   Telegram opcional. Sin `.env` manual.
3. Autonomía real: briefing matinal + reglas de email + automatizaciones con
   aprobaciones + chat con memoria — sin intervención técnica.
4. Robustez: suite completa verde (contratos + perf), degradación graceful de cada
   subsistema, logs útiles, deudas P3 de doc 12 saldadas.
5. Seguridad local: todo cifrado DPAPI, CORS cerrado, sin exposición de red
   (el cliente Web/PWA con PIN llega post-V1.0 a propósito).

**[Δ 2026-07-13] MEL v1 — Model Execution Layer (doc 19), bloque E1-E2 entre O4
y O5**: la capa universal de ejecución de modelos. El resto del sistema pide
CAPACIDADES (`mel.complete(capability=CLASSIFY|DRAFT|REASON|...)`) y el MEL decide
el modelo con un **Rule Engine determinista sin LLM (<1 ms)**, políticas
Economy/Quality/Offline autoconfiguradas al cerrar el wizard del onboarding (por
eso va antes de O5), sistema de fallback con circuit breakers, y registro
`mel_executions`. `ai_manager` pasa a ser su Provider Registry interno;
`tie/router.py` (doc 14) queda como shim que delega en el MEL; se migran los ~9
call-sites (chat, triaje, ai_reply, summarizer, TIE). El aprendizaje (Learning +
Recommendation Engines) y el builder Custom drag&drop llegan en V1.2 con el
Learner (comparten la tabla `model_stats`).

Sprints O1-O5 + E1-E2 (7-8 sesiones). Tag `v1.0.0-beta`.

## 6. V1.1 — Hermes Runtime + **Learning System operativo** (docs 10 + 15)

Sprint H0 de **investigación GO/NO-GO** (API real, licencia, huella) → HermesRuntime
+ 4 adapters (Memory/Skill/Tool/Context Provider): Hermes piensa, todo lo aprendido
vive en el MOS, toda tool pasa por whitelist+gate. LSL completa (tabla `skills` +
`skill_events`) + LLL completo (análisis 2-5) + **Mission Learning** (doc 15 §4:
reflexión post-misión → decisiones/pins/skills candidatas) + escalera de confianza
completa (doc 15 §3) + panel "lo que Aithera ha aprendido" con undo. Working Memory
(Letta) como detalle interno del runtime. **Contingencia definida** si NO-GO
(wrapper de proceso / runtime nativo / otro OSS) — V1.0 ya es producto completo
sin él. Cierre: Hermes ejecuta una tarea usando memoria de Aithera sin escribir un
solo archivo propio; 0 menciones a "Hermes" en la UI. (4-5 sesiones + H0.)

## 7. V1.2 — MCP Interop + **TIE v2** + Skill Evolution

- **MCP server**: ToolManager expuesto (whitelist + gates intactos). **MCP client**:
  `MCPToolProxy` — tools externas con las mismas validaciones; Hermes las ve vía
  `AitheraToolProvider` sin cambios.
- **TIE v2** (doc 14 §5): olas paralelas con semáforo, retry + replan de subárbol
  (los nodos DONE son inmutables), presupuestos de coste DUROS por misión (medidos
  desde V1.0), Mission Manager persistente (tabla `missions` + panel en el Hub +
  misiones del AE vía `MissionAction`), Model Router alimentado por
  `model_stats`/`tool_stats` del Learner. **Mission evals**: suite de misiones
  canónicas de regresión pre-release (doc 15 §9).
- **MEL v2** (doc 19 §9): Learning Engine (job nocturno sobre `mel_executions` +
  `model_stats` compartida con el Learner: prior bayesiano, decaimiento temporal,
  evidencia mínima, cambio acotado) + Recommendation Engine (propuestas HITL con
  evidencia, misma escalera de confianza) + **Custom builder drag&drop** +
  pantallas Actividad/Recomendaciones + reconfiguración automática por eventos +
  presupuestos de coste. La fila "Model Router alimentado por model_stats" de TIE
  v2 se cumple A TRAVÉS del MEL (una sola pieza aprende a elegir modelo).
- **Skill Evolution** (doc 15 §6): merge/split/specialize con linaje + dedup
  conceptual y detección de contradicciones del Knowledge Evolution (doc 15 §7).
- Automation: PatternTrigger/MemoryTrigger (alimentados por el LLL) +
  AutomationLearner (reglas sugeridas con HITL — doc 15 §8).
- MOS: Project Memory (Capa 2) activa; candidatos Qdrant/KuzuDB/Graphiti/Cognee
  entran AQUÍ como muy pronto, uno por vez, con el protocolo de migración RFC-006.

## 8. Post-V1.0 paralelo — Cliente Web + PWA + PIN de red

Mismo build React servido por FastAPI en `/app`, PIN/token para orígenes
no-localhost, rate limiting (slowapi), PWA. No bloquea V1.1/V1.2.

## 9. V1.5 — **AVCS MVP1 "Lenguaje completo"** + Hub avanzado (13 §20)

La actualización mayor del Hub (importante, no definitiva): los **7 ritmos
biológicos completos** sobre campos de fuerza componibles; raíces y ramas maduras;
patrones de Comprensión (mandalas/redes n-fold); factor de sincronía (el Error
como pérdida de cooperación, nunca "rojo"); AudioReactor completo (bandas);
PerformanceManager íntegro (escalera de degradación + invariantes de identidad);
**rediseño general de la UI** alrededor de la presencia y salto de animaciones →
comportamiento. (5-7 sesiones.)

También en esta era: **TIE v3** (doc 14 §5 — reflexión mid-mission del Learner,
routing predictivo, misiones recurrentes con memoria de misión previa,
priorización entre misiones concurrentes); Knowledge Evolution con grafo de
entidades (doc 15 §7); Hermes Desktop deja de usarse; multi-instancia de runtimes
por perfil (research/coding/calendar) compartiendo el MOS; panel de memoria/skills
rico en el Hub.

**AVCS MVP2 "Organismo" (V1.6+/era V2.0)**: UI viva (paneles que se FORMAN de
partículas y se disuelven), vida procedural en momentos especiales (luciérnagas,
semillas, mariposas — jamás constantes), memoria visual (el Hub madura con las
horas de uso; crecimiento imperceptible, nunca desbloqueos), preparación WebGPU.
(6-8 sesiones.) La detección de hardware del instalador (13 §19) se integra con
el onboarding del MVP beta: el PerformanceManager ya lee su tier de Settings —
cero refactor.

## 10. V2.0+ — La capa de red (opcional por diseño)

GSN (red de skills, 08 RFC-004) + CIE (inteligencia colectiva, RFC-005) + Guardians
(RFC-003), con aislamiento estructural de la Private Memory (RFC-001) y PrivacyFilter
tipado. Sincronización LSL↔GSN siempre con confirmación explícita (09 §3).

## 11. Mapa de evolución del MOS

(Tabla completa en 08 — resumen)

| Capa/componente | V0.85 | V0.9 | V1.0 | V1.1 | V1.2 | V2.0+ |
|---|---|---|---|---|---|---|
| Private Memory + Conversational + Decision | ✅ | ✅ uso real | ✅ | ✅ | ✅ | ✅ |
| Error/Automation Memory | contrato | ✅ | ✅ | ✅ | ✅ | ✅ |
| Skill Memory → LSL | stub | stub | básico | ✅ completa | ✅ | ✅ +GSN |
| LLL (Capa 4 local) | — | — | ✅ básico | ✅ completo | ✅ predictivo | ✅ |
| Working/Episodic/Knowledge/Graph | — | — | — | Letta | Graphiti/Cognee/Kuzu | ✅ |
| Project Memory (Capa 2) | stub | — | — | — | ✅ | ✅ |
| Compactación (RFC-007) | mínima | prune | ✅ | ✅ | ✅ | ✅ |
| GSN/CIE/Guardians | — | — | — | — | — | ✅ opcional |

## 11b. Mapa de evolución del Cognitive Runtime (TIE + Learner — detalle en 14 §5 y 15 §9)

| Componente | V0.85 | V0.9 | V1.0 | V1.1 | V1.2 | V1.5 |
|---|---|---|---|---|---|---|
| Contratos TIE (Mission/TaskGraph/TaskNode) | diseño | diseño | ✅ código | ✅ | ✅ | ✅ |
| Eventos (`app/core/events.py`) | ✅ nace (M2) | ✅ AE consume | ✅ `mission.*` | ✅ | ✅ | ✅ |
| Graph Execution Engine | — | — | ✅ lineal | ✅ | ✅ olas+replan | ✅ |
| ApprovalGate / gates por nodo | — | ✅ nace | ✅ reusado | ✅ | ✅ | ✅ |
| Model Router / Cost | — | — | fast-smart / medir | ✅ | +stats / imponer | cost-aware pleno |
| Missions | — | — | implícita (=trace) | implícita | ✅ tabla+panel | ✅ recurrentes |
| Learner: LLL análisis 1 / Mission Learning / evolución skills | — | — | ✅ / — / — | ✅ / ✅ / tabla | ✅ / ✅ / ✅ merge-split | +predictivo |
| Mission evals (regresión) | — | — | — | — | ✅ | ✅ |

## 12. Tabla resumen

| Versión | Nombre | Sesiones (Opus 4.8) | Entregable usable |
|---|---|---|---|
| V0.82/0.83 | Voz + **AVCS Fase 0** (semilla+ondas, 3 ritmos, modo presencia, chat limpio) | 3-4 | una presencia viva en el Hub |
| V0.85 ✅ | MOS Skeleton (cerrada, tag `v0.8.5`) | 5-6 | memoria viva: ingesta, briefing, contexto con fuentes |
| V0.87 | **WPMS** (Workspace) | 2-3 | proyectos/milestones/tareas vara-Linear, progreso automático, enganche MOS/TIE |
| V0.9 | Automation + Gates | 4-5 | briefing matinal automático, reglas, aprobaciones |
| V1.0 | **TIE v1** (Orchestrator) + **MVP BETA** | 5-6 | **instalable y autónomo para beta testers**; planes como grafo, camino corto, kill-switch |
| V1.1 | Hermes Runtime + **Learning System** | 4-5 (+H0) | agente que aprende; LSL completa; Mission Learning; panel "lo aprendido" |
| V1.2 | MCP + **TIE v2** + Skill Evolution | 4-5 | interop total, olas paralelas+replan, misiones persistentes, Project Memory, mission evals |
| V1.5 | **AVCS MVP1** + Hub avanzado + **TIE v3** | 5-7 | los 7 ritmos, UI rediseñada; reflexión continua y routing predictivo |
| V1.6+ | **AVCS MVP2** (UI viva, vida, memoria visual) | 6-8 | el Hub como organismo |
| V2.0+ | Red (GSN/CIE/Guardians) | — | inteligencia colectiva opcional |

**Total hasta V1.0 beta: ~16-20 sesiones.** Regla de siempre: si una fase crece, se
parte en dos (principio 7); si algo amenaza la fecha de V1.0, se recorta alcance de
la fase, nunca se aplaza V1.0.

---
*Roadmap definitivo 2026-07-09 (Fable 5). Sustituye a la versión V0.7.2→V1.2.
Cambios clave 07-09: V0.85 = MOS Skeleton con contratos definitivos; V0.9/V1.0
integrados con el MOS.*
*Revisión 2026-07-12: Cognitive Runtime integrado (docs 14/15/16) — V1.0 = TIE v1
(absorbe el Orchestrator, plan-como-grafo), V1.1 += Learning System, V1.2 += TIE v2
+ Skill Evolution, V1.5 += TIE v3. El orden de fases y la fecha de V1.0 no cambian;
V0.85 recibe 4 deltas menores (07 §Δ / 14 §4.1).*