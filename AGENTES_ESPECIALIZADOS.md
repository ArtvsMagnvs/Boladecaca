# AGENTES_ESPECIALIZADOS.md — Subagentes curados para Aithera

> Complementa a [`PRINCIPIOS_KARPATHY.md`](PRINCIPIOS_KARPATHY.md) (CÓMO
> comportarse) y a `CLAUDE.md` §18 (QUÉ construye Aithera). Este documento
> dice A QUIÉN delegar: cuándo una tarea encaja claramente en un dominio
> especializado, usa el subagente correspondiente (tool `Agent`, parámetro
> `subagent_type`) en vez de resolverlo todo en el hilo principal.

## Origen

29 definiciones de agente en `.claude/agents/` (formato estándar de Claude
Code: frontmatter `name`/`description` + persona), curadas a mano de
[`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents)
(254 agentes originales). Se descartaron ~213: los de dominios ajenos a
Aithera (e-commerce, salud, legal, inmobiliario, RRHH, ventas, marketing en
plataformas chinas, GIS/mapas, videojuegos, XR/spatial computing...) y los
meta-docs del framework "NEXUS" del repo origen (`EXECUTIVE-BRIEF.md`,
`QUICKSTART.md`, `nexus-strategy.md`), que describían SU propio sistema de
orquestación, no algo aplicable aquí.

Cada agente que se quedó tiene una razón concreta ligada a una parte REAL de
Aithera (no "podría servir algún día" — eso es sobreingeniería, principio 2
de `PRINCIPIOS_KARPATHY.md`).

## Tabla de enrutado

| Cuándo la tarea es... | Delega en... | Por qué encaja con Aithera |
|---|---|---|
| UI de React (Hub, Workspace, Chat, Missions) | **Frontend Developer** | `frontend/src/pages/` — React 18 + TS + Tailwind + Zustand |
| Empaquetado/IPC de Electron, `.bat`, instalador NSIS | **Desktop App Engineer** | `frontend/electron/`, roadmap O5 (MVP-beta: instalador, auto-start) |
| Pulido visual, CSS, glass-surface, tarjetas del Workspace | **UI Designer** | `.glass-surface`, `ProjectCard`/`AgentChip`, animaciones del Workspace |
| Decisiones de arquitectura frontend (estado, routing, patrones) | **UX Architect** | HashRouter, patrón `useWindowCard`, Zustand stores |
| Usabilidad del Hub/Workspace/Chat, flujos confusos | **UX Researcher** | Bugs de UX ya encontrados en vivo (W2b superposición, T4b pérdida de chat) |
| Routers FastAPI, capa de servicios, diseño de endpoints | **Backend Architect** | `app/api/endpoints/`, `app/services/` |
| Disciplina modular, límites de módulo, evitar sobreingeniería | **Software Architect** | doc16 (disciplina modular), `test_module_boundaries.py` |
| Esquema SQL, migraciones Alembic, índices, rendimiento de queries | **Database Optimizer** | 19 migraciones Alembic, incidentes de "migración solo probada en SQLite" |
| Diseño del grafo del TIE, AgentRuntime, Automation Engine | **Multi-Agent Systems Architect** | `app/tie/` (planner/executor/graph), `app/automation/` |
| Integración multi-proveedor IA, futuro MEL | **AI Engineer** | 8 proveedores IA, `ai_manager.py`, doc19 (MEL, plan aparte) |
| Prompts del clasificador de intención / planner / responder | **Prompt Engineer** | `app/tie/intents.py`, `planner.py`, `responder.py` — fronteras LLM→JSON |
| Búsqueda semántica y dedup de la memoria (ChromaDB) | **Search Relevance Engineer** | MOS (`app/memory/`), dedup por coseno en `lifecycle.py` |
| STT/TTS, ElevenLabs/eSpeak, conversación por voz | **Voice AI Integration Engineer** | `app/voice/`, roadmap V0.83 (Voz completa) |
| OAuth de Google, cifrado DPAPI, whitelist de Telegram | **Identity & Access Engineer** | `google_auth.py`, `app/core/secrets.py` |
| Jobs en background (APScheduler), salud del sistema, degradación graciosa | **SRE (Site Reliability Engineer)** | `scheduler_service`, `health_check()`, presupuestos de latencia del TIE |
| Cualquier fix o feature — ANTES de escribir código, para no sobreconstruir | **Minimal Change Engineer** | Aplica literalmente `PRINCIPIOS_KARPATHY.md` §2/§3 |
| Revisión profunda de un diff no trivial | **Code Reviewer** | Complementa (no sustituye) el skill `/code-review` ya instalado |
| Orientarse rápido en una parte del código nunca tocada | **Codebase Onboarding Engineer** | Backend+frontend ya grandes (repo con 20+ bloques de fase) |
| Estrategia de commits/ramas en casos no triviales | **Git Workflow Master** | Regla del proyecto: "un commit por paso terminado" |
| Actualizar CLAUDE.md / docs de fase tras cerrar un bloque | **Technical Writer** | Disciplina de CLAUDE.md (todo bloque cerrado se documenta igual) |
| Automatizar arranque/despliegue, CI, instalador | **DevOps Automator** | Deuda conocida: "backend no arranca desde Electron", roadmap O5 |
| Endurecer CORS, cifrado en reposo, superficie de ataque | **Application Security Engineer** | Historial real: CORS abierto y API keys en plano, ya corregidos |
| Escanear secretos antes de un commit | **Senior SecOps Engineer** | API keys de proveedores IA + tokens (Telegram, Google) en el repo |
| Suite de pytest, tests de contrato, tests e2e | **Test Automation Engineer** | `backend/tests/` (400+ tests), disciplina de un test por garantía |
| Medir presupuestos de latencia (checkpoint, validate, kill-switch) | **Performance Benchmarker** | doc14 §6 — los 5 presupuestos del TIE, ya con tests dedicados |
| Antes de dar un bloque por cerrado — exigir prueba, no narrativa | **Reality Checker** | Encaja con la cultura del proyecto: "verificado en vivo", nunca teatro |
| Reunir capturas/DOM como prueba de que algo funciona de verdad | **Evidence Collector** | Mismo patrón ya usado en cada verificación en vivo (DOM, screenshots) |
| Diseñar un flujo MCP (herramientas externas reales) | **MCP Builder** | Roadmap V1.2: conexión real a herramientas vía MCP (browser/computer use) |
| Diseñar un flujo multi-paso complejo (Kanban, triggers del AE, TIE) | **Workflow Architect** | WPMS (Kanban+atajos), triggers/conditions del Automation Engine |

## Cómo se activa "automáticamente"

Claude Code ya lista estos 29 agentes como `subagent_type` disponibles para
la tool `Agent` (se leen de `.claude/agents/*.md`). La instrucción de este
documento es de comportamiento, no de configuración: cuando una tarea
encaje CLARAMENTE con una fila de la tabla, usar ese agente en vez de
resolverlo todo genéricamente — igual que ya se hace con el agente `Explore`
para búsquedas amplias. Si una tarea no encaja con ninguno, se resuelve
directamente (no forzar un agente que no pinta nada).

---

*Fuente de los 29 agentes: [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)
(curado el 2026-07-17, 29 de 254 originales — el resto son de dominios ajenos
a Aithera y se descartaron).*
