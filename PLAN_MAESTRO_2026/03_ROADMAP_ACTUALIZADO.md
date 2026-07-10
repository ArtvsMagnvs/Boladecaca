# Roadmap definitivo — V0.8 → V2.0+ (Plan Maestro 2.0)

> Reescrito 2026-07-09 (Fable 5) integrando los diseños de `FABLE5_PROMPTS/` 01-07.
> Los principios 1-8 del AOS siguen vigentes e inviolables. Documentos de diseño:
> **07** MOS V0.85 · **08** MOS arquitectura completa · **09** LSL/LLL · **10** Hermes
> · **11** Automation+Orchestrator · **12** Auditoría/optimización · **13** AVCS (sistema visual).
>
> **La estrella polar**: V1.0 es un **MVP bien hecho — completamente autónomo y
> distribuible a usuarios BETA** — alcanzable en semanas, no meses. Todo lo que no
> sea necesario para eso se diseña hoy (contratos/stubs) y se implementa después.

---

## 0. Filosofía ACI (la capa por encima del roadmap)

- **ACI (Aithera Cognitive Infrastructure)**: memoria + skills + tools +
  automatización + orquestación. Diseñada para sobrevivir a cualquier LLM o runtime.
- **MOS (Memory Operating System)**: el subsistema de memoria de la ACI (docs 07/08).
  **La memoria pertenece a Aithera, nunca al runtime.**
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

## 3. V0.85 — MOS Skeleton (diseño completo: doc 07)

**Opción B**: arquitectura definitiva, implementación mínima. En una frase: se
construye la columna vertebral de la memoria (interfaces `IMemoryStore`/`MemoryRouter`
+ 5 tipos de memoria + tabla `decisions`) y sobre ella la funcionalidad: ingesta de
email/calendario cada 20 min, resumen nocturno Ollama-first, contexto con atribución
de fuente en el chat, `GET /api/memory/briefing`, compactación mínima (dedup +
presupuesto), vault opcional.

- Sprints M1-M5 (5-6 sesiones), criterios de cierre por sprint en doc 07 §10.
- Incluye las optimizaciones P1 de doc 12 (init de ChromaDB en background, índices).
- **Cierre de fase**: "¿qué me ha llegado importante hoy?" responde desde memoria
  local con Gmail desconectado. Tag `v0.8.5`.
- Handoff garantizado a V0.9: briefing estable, `context()` ≤ 300 ms, `decisions`
  lista, jobs asyncio migrables a APScheduler.

## 4. V0.9 — Automation Engine + ApprovalGate (diseño completo: doc 11 parte A)

Arquitectura de 4 capas (Triggers/Conditions/Actions/Learner) con MVP funcional:

- **ApprovalGate genérico** persistente y reanudable — EL primitivo que reusan
  Orchestrator, Hermes y skills. La confirmación de email migra a él.
- Triggers Schedule+Event (reactivos sobre la ingesta del MOS — cero polling
  propio), condiciones composables con cooldown/ventana horaria, 4 acciones.
- **Integración MOS obligatoria**: `daily_briefing` consume `/api/memory/briefing`
  (sin Gmail en caliente); resultados → Automation Memory; aprobaciones → Decision
  API; errores → Error Memory. APScheduler entra aquí y absorbe los jobs de V0.85.
- Reglas predefinidas (off por defecto): daily_briefing, system_monitor,
  urgent_email_alert, email_summary, agent_task. UI de reglas + aprobaciones.
- Sprints A1-A4 (4-5 sesiones). Stubs listos para V1.2: PatternTrigger,
  MemoryTrigger, AutomationLearner, ChainedRuleAction. Tag `v0.9`.

## 5. V1.0 — Orchestrator + **MVP BETA distribuible** (diseño: doc 11 parte B)

El cerebro: 6 componentes (Intent Classifier barato-siempre → Context Enricher con
pre-fetch/caché → Task Planner potente-solo-si-hace-falta → Executor secuencial con
gates → Response Builder → Tracer con Decision API). `AgentRuntime` + `NullRuntime`
(doc 10) — V1.0 es completo SIN Hermes. LLL básico (doc 09): detección de tareas
repetidas → propuesta de skills. Enganche: `gateway.set_handler(orchestrator)`.

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

Sprints O1-O5 (5-6 sesiones). Tag `v1.0.0-beta`.

## 6. V1.1 — Hermes Runtime (diseño completo: doc 10)

Sprint H0 de **investigación GO/NO-GO** (API real, licencia, huella) → HermesRuntime
+ 4 adapters (Memory/Skill/Tool/Context Provider): Hermes piensa, todo lo aprendido
vive en el MOS, toda tool pasa por whitelist+gate. LSL completa + LLL completo +
panel "lo que Aithera ha aprendido" (doc 09). Working Memory (Letta) como detalle
interno del runtime. **Contingencia definida** si NO-GO (wrapper de proceso /
runtime nativo / otro OSS) — V1.0 ya es producto completo sin él.
Cierre: Hermes ejecuta una tarea usando memoria de Aithera sin escribir un solo
archivo propio; 0 menciones a "Hermes" en la UI. (4-5 sesiones + H0.)

## 7. V1.2 — MCP Interop + potenciación

- **MCP server**: ToolManager expuesto (whitelist + gates intactos). **MCP client**:
  `MCPToolProxy` — tools externas con las mismas validaciones; Hermes las ve vía
  `AitheraToolProvider` sin cambios.
- Orchestrator: paralelismo por olas, plan backtracking, plan negotiation.
- Automation: PatternTrigger/MemoryTrigger (alimentados por el LLL) + AutomationLearner.
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

También en esta era: Hermes Desktop deja de usarse; multi-instancia de runtimes
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

## 12. Tabla resumen

| Versión | Nombre | Sesiones (Opus 4.8) | Entregable usable |
|---|---|---|---|
| V0.82/0.83 | Voz + **AVCS Fase 0** (semilla+ondas, 3 ritmos, modo presencia, chat limpio) | 3-4 | una presencia viva en el Hub |
| V0.85 | MOS Skeleton | 5-6 | memoria viva: ingesta, briefing, contexto con fuentes |
| V0.9 | Automation + Gates | 4-5 | briefing matinal automático, reglas, aprobaciones |
| V1.0 | Orchestrator + **MVP BETA** | 5-6 | **instalable y autónomo para beta testers** |
| V1.1 | Hermes Runtime | 4-5 (+H0) | agente que aprende; skills en la LSL |
| V1.2 | MCP + potenciación | 4-5 | interop total, paralelismo, Project Memory |
| V1.5 | **AVCS MVP1** + Hub avanzado | 5-7 | los 7 ritmos, UI rediseñada |
| V1.6+ | **AVCS MVP2** (UI viva, vida, memoria visual) | 6-8 | el Hub como organismo |
| V2.0+ | Red (GSN/CIE/Guardians) | — | inteligencia colectiva opcional |

**Total hasta V1.0 beta: ~16-20 sesiones.** Regla de siempre: si una fase crece, se
parte en dos (principio 7); si algo amenaza la fecha de V1.0, se recorta alcance de
la fase, nunca se aplaza V1.0.

---
*Roadmap definitivo 2026-07-09 (Fable 5). Sustituye a la versión V0.7.2→V1.2.
Cambios clave: V0.85 = MOS Skeleton con contratos definitivos; V0.9/V1.0 integrados
con el MOS; 