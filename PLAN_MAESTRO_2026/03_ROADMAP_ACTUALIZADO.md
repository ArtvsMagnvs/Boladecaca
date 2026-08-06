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
> **16** Principios Modulares · **17** Event Bus/Observabilidad · **18** WPMS/Workspace · **19** MEL/Model Execution Layer ·
> **21** plan de sesiones del TIE (T1-T5, CERRADO) · **22** plan de sesiones del MEL (E1-E2b)
> · **27** plan V1.0→V1.5 (dependencias + sesiones + modelos + tests — MANDA sobre las secciones 6-10).
>
> **La estrella polar**: V1.0 es un **MVP bien hecho — completamente autónomo y
> distribuible a usuarios BETA** — alcanzable en semanas, no meses. Todo lo que no
> sea necesario para eso se diseña hoy (contratos/stubs) y se implementa después.

---

## 0a. REGLA DE DESARROLLO — a partir de V1.0, manda el doc 27 (simple, sin ambigüedad)

**Este documento (03) es el MAPA general** — visión, orden de fases, filosofía.
**El documento [`27_PLAN_V1_A_V16.md`](27_PLAN_V1_A_V16.md) es el PLAN EJECUTABLE**
— sesión por sesión, con alcance cerrado, modelo/esfuerzo asignado, tests
obligatorios y criterio de cierre para cada una.

**Regla, para que no haya confusión en ninguna sesión futura**: desde V1.1 en
adelante — es decir, **V1.1, V1.2, V1.3, V1.4, V1.4.5 y V1.5** — el trabajo de
desarrollo sigue LITERALMENTE los pasos del doc 27, no una reinterpretación de
las secciones 6-10 de este doc 03. Si alguna vez este doc 03 y el doc 27 parecen
decir cosas distintas para V1.0+, **gana el doc 27** (ya lo decía la cabecera de
este documento con "MANDA sobre las secciones 6-10"; esta sección lo deja
explícito y fácil de encontrar). Las secciones 6-10 de este doc 03 son un RESUMEN
de doc 27 para tener la vista de conjunto — el detalle real (qué construir sesión
a sesión) vive solo en doc 27.

> ### ⚠️ REORDENACIÓN 2026-08-05 (decisión del usuario)
>
> **El MVP-beta (instalador + onboarding + verificación total, B1-B4) se APLAZA
> a V1.5.** Razón literal del usuario: *«sé que en teoría toca cerrar fase 1.0
> con el instalador, pero dado que no tengo usuarios beta para testear todavía,
> voy a continuar desarrollando y cerraremos el installer más adelante»*.
> Empaquetar sin nadie a quien entregar es trabajo que caduca: cada fase
> posterior añade dependencias, pantallas de onboarding y permisos que obligarían
> a rehacerlo. El tag `v1.0.0` ya está puesto (2026-08-02, CLAUDE.md §29).
>
> **Todo el AVCS maduro (MVP1 y MVP2) se traslada a V2.0+** (doc 27 §10): mejora
> una capacidad ENTREGADA (Génesis, en uso diario desde V0.82/83 y pulido hasta
> PU5g), frente a Learner/MCP/Hermes/red que son capacidades ausentes. El pulido
> puntual del AVCS sigue permitido; lo aparcado es el salto de arquitectura visual.
>
> **V1.6 desaparece como fase**: sus 4 sesiones AVCS van a V2.0+ y la 5.ª (O5,
> Project Memory Capa 2 + contratos GSN/CIE) sube a V1.5. **Nace V1.4.5**
> (multi-instancia de runtimes), que era la 2.ª mitad de la vieja A5 y no era
> AVCS sino concurrencia de backend dependiente de Hermes.
>
> **Ninguna sesión se ha borrado ni recortado** — todas conservan alcance,
> modelo y tests; solo cambian de sitio. Tramo activo: 36 → **23-24 sesiones**
> + 10 aparcadas en V2.0+. **Siguiente fase: V1.1 (Learner operativo), doc 27 §5.**

Las 4 sesiones **B1-B4** (Verificación total, Instalador+auto-start, Onboarding
wizard, Beta kit+release) conservan su texto íntegro en doc 27 §4b y se ejecutan
en **V1.5** (doc 27 §9) — la mención más abajo a "Sprints O1-O5" es la numeración
ANTIGUA de antes de que TIE/MEL/Tools/Orchestrator se ejecutaran con sus propios
nombres (T1-T5, E1-E2b, R1-R7); se mantiene aquí solo como historial de diseño.

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

## 2. ✅ V0.82 / V0.83 — Voz + Hub: **AVCS Fase 0 "Génesis"** — CERRADA (diseño: doc 13)

> **[Corrección 2026-07-22]** Esta fase **SÍ se construyó** — commits
> `c457393`/`93b3e8b`/`8f5ad70`/`7b6d376`/`6d8b820`/`19adbb4`/`aadb180`/
> `918138a` (2026-07-10 a 2026-07-12). Una nota posterior en CLAUDE.md
> (escrita el 2026-07-15, en el sprint W2b del Workspace) decía "AVCS
> completo de doc 13... sin construir" — comparaba con el AVCS *maduro* de
> MVP1/MVP2, no con esta fase, pero se leyó como "Génesis no existe" y ese
> error se propagó al doc 27 (que reprogramaba construir Génesis en V1.1).
> Corregido aquí y en doc 27 §1/§5 — ver auditoría 2026-07-22 (commits+código
> reales en `frontend/src/avcs/`).

Nace el **Aithera Visual Consciousness System** (especificación completa en
`13_AVCS_DISENO_MAESTRO.md`), motor real en `frontend/src/avcs/` (contrato de
arquitectura congelado en `avcs/ARCHITECTURE.md`):

1. ✅ **Semilla + Ondas de Sincronía** — `ParticleEngine` GPGPU real
   (`GPUComputationRenderer` ping-pong, 3 texturas) + `ShaderSystem` +
   `RhythmEngine` — sustituye a la esfera `AICore.tsx`. Semilla con la forma
   de pétalo de loto de la referencia (`math/lotus.ts`), núcleo Ámbar
   constante + aura, respiración anti-mecánica (nunca `sin(t)` puro).
2. ✅ Ritmos reales: **Reposo** (S1) y **Escucha**/**Comunicación** (S2, con
   pesos propios diseñados — no clones de Reposo) — `AudioBridge`/
   `AudioReactor` real sobre el audio del TTS; el logo se hincha con la voz
   al hablar.
3. ✅ **Sin clipping**: cámara fit-contain + falloff de borde NDC (13 §13.3).
4. ✅ **Modo Presencia** (F9/botón, pliega toda la UI, 13 §13.4).
5. ✅ **Chat limpio**: presencia central + panel lateral flotante (13 §13.5).
6. ✅ **PerformanceManager v0**: tiers **Q1-Q4** (creció de Q1-Q3 a Q1-Q4 más
   tarde) con selector en Ajustes → HUB Visual, alimentado además por el
   scanner de hardware (CLAUDE.md §23).

**Deuda real que SÍ queda de esta fase** (no confundir con MVP1, hoy en V2.0+):
`PROFESSIONAL_VOICES` sigue hardcodeado en `elevenlabs_voice.py` (doc 12 A6,
sin tocar). El sprint perf-front (`React.lazy`/`Suspense` por ruta) **sí se
hizo**, pero en O3 (doc 26, 2026-07-20) — sesión distinta, no este bloque.

**Lo que NO se construyó aquí y sigue siendo MVP1 (V2.0+ desde 2026-08-05, doc 13 §20)**: los
otros 4 ritmos (Comprensión/Acción/Error/Recuperación hoy son copias de los
pesos de Reposo en `constants.ts`, no diseño propio), los campos de fuerza
maduros (raíces/ramas/mandalas — `fRoot/fBranch/fMandala/fChannel` siguen
siendo `vec3(0.0)`), el factor de sincronía visual completo y el pulido de
transición entre ritmos.

**Cierre real**: verificado en navegador (semilla emerge, ondas empujan el
campo, respira sin bucle detectable en 5 min, 0 errores de consola;
navegar Hub↔Chat×4 = 1 solo Canvas, 0 re-inits). 8 commits, 2026-07-10 a
2026-07-12.

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

> **[Δ 2026-07-15] Plan de sesiones detallado, listo para ejecutar**:
> `PLAN_MAESTRO_2026/20_V09_PLAN_SESIONES.md` traduce este diseño a sprints
> **sin decisiones abiertas** (A1 · A2a · A2b · A3 · A4), auditado contra el
> estado REAL del código de v0.8.7. Recoge los 10 deltas desde que se planificó
> V0.9 (eventos WPMS, WorkspaceAction, briefing con workspace, lifecycle.py,
> httpx persistente, cooldown, chat_service, push del Gateway, Decision.history,
> stub por proyecto). A2 se divide en A2a/A2b por carga (mismo criterio que
> W2→W2a-e). Artefacto visual acompañante en el scratchpad de la sesión.

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

> ✅ **TIE v1 (T1-T5) CERRADO — 2026-07-17, tag `v0.9.2`** (plan: doc 21).
> ✅ **MEL v1 (E1-E2b) CERRADO** (plan: doc 22), sin bump.
> ✅ **ORQUESTRATOR (R1-R7) CERRADO — 2026-07-20, tag `v0.9.5`** (plan: doc 23).
>
> El Orquestador NO era un renombrado del TIE sino la capa POR ENCIMA: decide
> QUÉ MISIONES hay (descomposición, concurrencia, anidamiento, consolidación),
> mientras el TIE decide los pasos dentro de una misión y el MEL el modelo. En
> R1 se cerró además el hueco más grave del TIE (Δ2): NUNCA había ejecutado una
> tool — decía haber hecho cosas que se inventaba.
>
> ✅ **V1.0 CERRADA — 2026-08-02, tag `v1.0.0`** (CLAUDE.md §29), y después
> siguieron los bloques de fiabilidad (doc 40 A·B·C) y navegación web (doc 32
> B·WEB-1/2, C·WEB-3/4), cerrados el 2026-08-05.
>
> **[2026-08-05] El MVP-beta** (instalador NSIS, auto-start del backend,
> onboarding) **YA NO es el bloque que falta para `1.0.0`: se aplaza a V1.5**
> por decisión del usuario — sin beta testers no entrega valor y caduca con cada
> fase posterior. El tag `v1.0.0` se puso igualmente por el volumen de bloques
> cerrados. Ver §0a y doc 27 §9.
>
> **[Δ 2026-07-22, CRÍTICO — orden del usuario] Fiabilidad de memoria
> (guardar→recuperable).** El task-bench de modelos (mel_benchmarks.tasks,
> scripts/model_task_bench.py) destapó que `memory_save` es el escenario menos
> fiable del sistema: los modelos ejecutan la memory tool CORRECTAMENTE (save +
> search, 2 tools OK) y aun así el dato tarda en ser recuperable o no aparece
> en la búsqueda semántica — apunta a la memory tool / indexación de ChromaDB
> (latencia de indexado tras `store()`, ranking), NO a los modelos. Un
> asistente que "guarda" algo y luego no lo encuentra es inaceptable en 1.0.
> **Revisar y arreglar ANTES del MVP-beta.** (Mitigación temporal ya aplicada:
> `memory_save` no computa para la aptitud agentic de los modelos, y el
> verificador del banco reintenta con espera de indexación.)

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

**[Δ 2026-07-18] MEL crece a E1-E1b-E2-E2b** (plan de sesiones detallado: doc
22) por dos peticiones explícitas del usuario: catálogo auto-investigado por
modelo conectado (refresco cada 14 días) y override explícito del usuario con
confirmación de alcance (tarea vs. proyecto) — el override manda sobre el MEL,
pero el TIE tiene que confirmar el alcance antes de aplicarlo. Mismo bloque del
roadmap, 4.5-5 sesiones en vez de 2-3.

> **Nota (2026-07-23)**: la línea de arriba ("Sprints O1-O5 + E1-E1b-E2-E2b")
> es la numeración de diseño ANTERIOR a que TIE/MEL/Tools/Orchestrator se
> ejecutaran de verdad con sus propios nombres de sprint (T1-T5 para el TIE,
> E1-E2b para el MEL, R1-R7 para el Orquestrator — todos ✅ CERRADOS, ver nota
> al inicio de esta sección). Se conserva como historial. Las 4 sesiones B1-B4
> (Verificación total · Instalador+auto-start · Onboarding wizard · Beta
> kit+release) **se ejecutan en V1.5** desde la reordenación del 2026-08-05 —
> ver regla de la sección 0a.

Tag `v1.0.0` puesto el 2026-08-02 (CLAUDE.md §29). El empaquetado llega en
`v1.5.0` (doc 27 §9).

## 6. V1.1 — **Learner operativo** (plan de sesiones: doc 27 §5) ⬅ **FASE ACTIVA**

**[Δ 2026-07-20, reordenación por dependencias — doc 27 §1]**: el Learner SUBE a
V1.1 (es el nodo con más dependientes: MEL Learning, AutomationLearner, Skill
Evolution, reflexión, y la LSL que Hermes necesita) y Hermes BAJA a V1.3. "TIE
v3" queda DISUELTO: reflexión continua → Learner (aquí), routing predictivo →
MEL Learning (V1.2), multi-runtime → V1.4.5 (fase propia desde 2026-08-05).

**[2026-08-05] Es la fase que se empieza AHORA**, tras aplazar el MVP-beta a
V1.5. Arranca con todo lo que necesita ya en producción y acumulando datos
reales desde hace meses: eventos `mission.*` (V1.0 T4a), `automation_learner`
stub con interfaz congelada (V0.9 A4), `mem_automation`/`mem_error` (A4),
Decision API con `history()` (A4), `skill_store` + `LocalSkill` con linaje
(V0.85 M1) y telemetría de misiones punta a punta (doc 31). El Learner no nace
en blanco.

**[Corrección 2026-07-22]**: esta fase YA NO incluye AVCS Génesis. Se
descubrió (auditoría de commits) que Génesis se construyó en V0.82/83
(§2 — 2026-07-10 a 07-12), no que estuviera pendiente. La pista frontend
paralela AV1-AV2 que aquí se planeaba se retira por completo; V1.1 queda
100% backend (Learner). Completar los 4 ritmos que faltan
(Comprensión/Acción/Error/Recuperación) sigue siendo MVP1 (V2.0+ desde la
reordenación del 2026-08-05, doc 13 §20) — confirmado con el usuario que no
urge, puede esperar a esa fase.

- **Backend (L1-L4)**: LSL completa (tabla `skills`+`skill_events` con linaje) +
  escalera de confianza + Mission Learning (`mission.completed` → model_stats,
  decisiones, skills DRAFT) + LLL análisis 2-5 + panel "Lo que Aithera ha
  aprendido" con Aceptar/Editar/Rechazar/Undo.
- **[Comparativa competitiva 2026-07-24, doc 32 Anexo]** El LLL (L3) gana una vía
  de autoría de skills tipo `/learn` de Hermes Agent: el usuario pasa una
  conversación/URL/notas y Aithera redacta el `SKILL.md` (cuarentena + HITL,
  como cualquier skill DRAFT). Es una FUENTE más, no un pivote. Detalle en doc 09.
- 4 sesiones (Fable ×1: contratos L1). Tag `v1.1.0`.

## 7. V1.2 — MCP Interop + **TIE v2** + **MEL Learning** (doc 27 §6)

- **MCP client** (Fable: superficie de seguridad): `MCPToolProxy` con whitelist +
  gates + permiso `mcp.use`; **MCP server**: ToolManager expuesto (stdio), tools
  `internal=True` jamás. Prepara el terreno de Hermes.
- **TIE v2**: olas paralelas (semáforo), retry/replan de subárbol (nodos DONE
  inmutables), presupuestos DUROS por misión, Mission Manager persistente +
  `MissionAction` del AE + **mission evals** (suite canónica pre-release).
- **MEL Learning + Recommendation Engines** (doc 19 §9.2-9.3, ahora con
  `model_stats` poblada por el Learner) + **Skill Evolution** + AutomationLearner.
- **[Comparativa competitiva 2026-07-24, doc 32 Anexo]** MCP era el gap de
  interoperabilidad más citado: los tres sistemas OSS más usados
  (OpenClaw/Hermes/OpenJarvis) lo tienen, OpenJarvis además bidireccional (+A2A).
  Ya estaba planeado aquí — la comparativa solo confirma la prioridad, sin
  reprogramar. Mantener C2 (server) bidireccional en el alcance.
- 6 sesiones (Fable ×2: C1 MCP client, T1 executor). Tag `v1.2.0`.

## 8. V1.3 — Hermes Runtime (GO/NO-GO) (doc 27 §7)

Investigación 2026-07-20: **viable de forma GRADUAL** — `hermes-agent` es paquete
Python (v0.14+), con memory providers ENCHUFABLES (v2026.4.3) que encajan con los
adapters del doc 10, y LLM configurable por endpoint custom → **todas sus
llamadas pasarán por el MEL** (shim OpenAI-compatible local). Nunca integración
"de golpe": H0 verifica en real (providers, interceptación de tools, huella,
offline) → GO: H1-H4 incremental con las garantías de la auditoría (grounding,
gates) aplicadas a Hermes · NO-GO: plan B (doc 10 §6) en 2 sesiones. 5 sesiones
(Fable ×2: H0, H1+shim MEL). Tag `v1.3.0`.

**[Comparativa competitiva 2026-07-24, doc 32 Anexo]** H1 generaliza el patrón
"narrow waist" de Hermes (UN contrato `provider+registry+plugin` para TODO lo
pluggable, no solo modelos como hoy el MEL): al enchufar el 2.º runtime real, se
formaliza el contrato uniforme. **Nota honesta**: el TIE de Aithera ya es MÁS
estructurado que el bucle plano de Hermes (planner+DAG vs ReAct, confirmado por
análisis externos) — Hermes aporta su ecosistema (32 proveedores/24 canales/181
skills) y el patrón del contrato, NO su arquitectura de razonamiento.

## 8b. V1.4 — Red (Web+PWA+PIN) + 2 canales + sandboxing + voz + memoria legible (doc 27 §8)

Cliente Web servido en `/app` + PIN/token + rate limiting (Fable: superficie de
red) + PWA + decisiones de voz VZ2-VZ4 CON los datos del profiling VZ5 + UX
remanentes (U1-U3). **[Comparativa competitiva 2026-07-24, doc 32 Anexo]** V1.4
absorbe 3 items derivados de la comparativa OpenJarvis/OpenClaw/Hermes (todos
decididos por el usuario para post-1.0):
- **W3 — 2 canales más del Gateway (Discord + WhatsApp)**: los competidores
  tienen 24-37 canales; Aithera solo Telegram. El patrón `ChannelAdapter` (doc
  20, ya inspirado en OpenClaw) hace barato añadir adapters.
- **S1 — Sandboxing de ejecución (Docker)** para `shell`/`desktop`/`browser`:
  hoy solo whitelist; 2 de 3 competidores usan aislamiento real de proceso. Modo
  contenedorizado opcional, degradación graciosa si no hay Docker.
- **Memoria humano-legible** (dentro de U1, inspirado en `MEMORY.md` de
  OpenClaw): vista/export legible y editable del perfil MOS (extiende `profile.py`).

7 sesiones (Fable ×2: W1 red, S1 sandboxing). Tag `v1.4.0`.

## 8c. V1.4.5 — Multi-instancia de runtimes (27 §8b)

Varias instancias de runtime vivas a la vez, por perfil (research/coding/calendar,
o una por proyecto), compartiendo el MOS y con aislamiento de estado entre ellas.
**[2026-08-05]** Sale a fase propia: estaba pegada a la sesión A5 del AVCS por
convivencia, no por dependencia — es concurrencia de backend y depende de Hermes
(V1.3), no de partículas. Si H0 salió NO-GO, se reduce a varias instancias del
runtime nativo y el contrato queda listo para el día que entre un segundo runtime.
(1-2 sesiones, Fable.)

## 9. V1.5 — Cierre del organismo local + **MVP-beta** (27 §9)

**[Reordenación 2026-08-05]** Fase de CIERRE del tramo, fusión de dos cosas:

- **O5 — Project Memory Capa 2** (permisos por proyecto, doc 08 Capa 2) +
  **revisión de contratos GSN/CIE** (PortableSkill, PrivacyFilter, aislamiento
  RFC-001, GuardianRuntime) → handoff documentado a V2.0. Va primera: si obliga a
  tocar el núcleo, mejor antes de empaquetarlo.
- **B1-B4 — el MVP-beta que estaba al principio del plan**: verificación total y
  deudas de cierre (incluida la carrera `state=done`/`outcome` del tracer y la
  suite completa en Windows, adelantables a cualquier hueco), instalador NSIS +
  auto-start, onboarding wizard, y beta kit + release. Se empaqueta aquí porque
  aquí el producto ya no va a cambiar de forma — hacerlo antes obligaba a
  rehacerlo tras cada fase (Hermes, Docker, MCP, PIN de red, pantallas nuevas).

**Cierre V1.5 = Aithera como organismo completo local, empaquetado y
distribuible.** Bump a `1.5.0` + tag. (5 sesiones.)

## 10. V2.0+ — AVCS maduro + la capa de red

**AVCS MVP1 "Lenguaje completo"** (5 sesiones, 13 §20, 27 §10): los **7 ritmos
biológicos completos** sobre campos de fuerza componibles; raíces y ramas maduras;
patrones de Comprensión (mandalas/redes n-fold); factor de sincronía (el Error
como pérdida de cooperación, nunca "rojo"); AudioReactor completo (bandas);
PerformanceManager íntegro (escalera de degradación + invariantes de identidad);
**rediseño general de la UI** alrededor de la presencia y salto de animaciones →
comportamiento.

**AVCS MVP2 "Organismo"** (4 sesiones): UI viva (paneles que se FORMAN de
partículas y se disuelven), vida procedural en momentos especiales (luciérnagas,
semillas, mariposas — jamás constantes), memoria visual (el Hub madura con las
horas de uso; crecimiento imperceptible, nunca desbloqueos), preparación WebGPU.
La detección de hardware (13 §19) ya está integrada con Ajustes → Sistema desde
2026-07-21: el PerformanceManager lee su tier de ahí — cero refactor pendiente.

> **[2026-08-05] Por qué el AVCS maduro está aquí y no en V1.5**: Génesis está
> entregado y en uso diario desde V0.82/83, y se ha seguido puliendo hasta PU5g
> (partículas por tier con luminosidad medida, anillos que giran y laten con la
> voz, bloom, el apagón arreglado). Lo que queda MEJORA una capacidad que ya
> existe, frente a Learner/MCP/Hermes/red que son capacidades ausentes. **El AVCS
> no se congela**: el pulido puntual sigue siendo bienvenido; lo aparcado es el
> salto de arquitectura visual, no los retoques.

**También en esta era**: **TIE v3** (doc 14 §5 — reflexión mid-mission del
Learner, routing predictivo, misiones recurrentes con memoria de misión previa,
priorización entre misiones concurrentes); Knowledge Evolution con grafo de
entidades (doc 15 §7); panel de memoria/skills rico en el Hub.

**La capa de red (opcional por diseño)**: GSN (red de skills, 08 RFC-004) + CIE
(inteligencia colectiva, RFC-005) + Guardians (RFC-003), con aislamiento
estructural de la Private Memory (RFC-001) y PrivacyFilter tipado. Sincronización
LSL↔GSN siempre con confirmación explícita (09 §3). Plan de sesiones propio al
llegar, sobre los contratos revisados en O5 (V1.5).

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

| Componente | V0.85 | V0.9 | V1.0 | V1.1 | V1.2 | V1.5+ |
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
| V0.82/0.83 ✅ | Voz + **AVCS Fase 0 "Génesis"** — cerrada 2026-07-12 (semilla+ondas, 3 ritmos reales, modo presencia, chat limpio, PerformanceManager Q1-Q4) | 3-4 (hecho) | presencia viva en el Hub, ya entregada |
| V0.85 ✅ | MOS Skeleton (cerrada, tag `v0.8.5`) | 5-6 | memoria viva: ingesta, briefing, contexto con fuentes |
| V0.87 | **WPMS** (Workspace) | 2-3 | proyectos/milestones/tareas vara-Linear, progreso automático, enganche MOS/TIE |
| V0.9 | Automation + Gates | 4-5 | briefing matinal automático, reglas, aprobaciones |
| V1.0 ✅ | **TIE v1** (Orchestrator) + MEL + Tools + auditoría + pulido | — | tag `v1.0.0` (2026-08-02); planes como grafo, camino corto, kill-switch, navegación web agentic |
| ~~V1.0 cierre~~ | ~~MVP-beta~~ → **movido a V1.5** (2026-08-05) | — | sin beta testers no entrega valor y caduca con cada fase; ver §0a |
| **V1.1** ⬅ | **Learner operativo** | 4 | Aithera aprende (LSL, Mission Learning, panel con undo) — AVCS Génesis ya entregado en V0.82/83, no se repite |
| V1.2 | MCP + **TIE v2** + MEL Learning + Skill Evolution | 6 | interop total; olas+replan+presupuestos; el MEL aprende; evals |
| V1.3 | Hermes Runtime (H0 GO/NO-GO → H1-H4) | 5 | runtime que crece, con memoria/tools/LLM 100% de Aithera |
| V1.4 | Web+PWA+PIN + 2 canales + sandboxing + voz + memoria legible | 7 | Aithera desde el navegador/móvil; voz fluida medida; ejecución aislada |
| V1.4.5 | Multi-instancia de runtimes | 1-2 | varios runtimes vivos por perfil, con estado aislado |
| V1.5 | Project Memory C2 + puerta GSN/CIE + **MVP-beta (instalador)** | 5 | el organismo local cerrado Y empaquetado; doble clic y funciona; tag `v1.5.0` |
| V2.0+ | **AVCS MVP1 + MVP2** · Red (GSN/CIE/Guardians) | 9 + ? | el Hub como organismo; inteligencia colectiva opcional |

**Total hasta V1.0: ejecutado** (tag `v1.0.0`, 2026-08-02 — ver §5 y CLAUDE.md §29).
**Total V1.1 → V1.5: 23-24 sesiones** + 10 aparcadas en V2.0+ (recuento exacto y
detallado por sesión en doc 27 §2 — la cifra de esta tabla es
orientativa/histórica, doc 27 manda, ver §0a). Regla de siempre: si una fase
crece, se parte en dos
(principio 7); si algo amenaza la fecha de V1.0, se recorta alcance de la
fase, nunca se aplaza V1.0.

---
*Roadmap definitivo 2026-07-09 (Fable 5). Sustituye a la versión V0.7.2→V1.2.
Cambios clave 07-09: V0.85 = MOS Skeleton con contratos definitivos; V0.9/V1.0
integrados con el MOS.*
*Revisión 2026-07-12: Cognitive Runtime integrado (docs 14/15/16) — V1.0 = TIE v1
(absorbe el Orchestrator, plan-como-grafo), V1.1 += Learning System, V1.2 += TIE v2
+ Skill Evolution, V1.5 += TIE v3. El orden de fases y la fecha de V1.0 no cambian;
V0.85 recibe 4 deltas menores (07 §Δ / 14 §4.1).*