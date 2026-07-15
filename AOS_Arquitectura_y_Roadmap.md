# Aithera — Roadmap (actualizado 2026-07-09)

> **Fuente de verdad**: estado real del código (CLAUDE.md) + PLAN_MAESTRO_2026 + JWIKI wiki-map.
> **Versión actual**: V0.8.0 (Gateway + Telegram + DPAPI + voz + CORS hardening).
> **Wiki**: 271/267 docs verificados (100%). Ver `JWIKI/00_INDEX/wiki-map.md`.

---

## Fases completadas ✅

- ✅ **V0.2** Base (FastAPI + SQLAlchemy + Pydantic v2 + Zustand).
- ✅ **V0.3** Hub responsivo (AICore 3D con R3F + custom shaders).
- ✅ **V0.4** PostgreSQL + Alembic (12+ migrations).
- ✅ **V0.5** AgentManager + ToolManager + 8 tools.
- ✅ **V0.6** ChromaDB memory (3 collections).
- ✅ **V0.7** Email + Calendar (Google OAuth2 + PKCE).
- ✅ **V0.7.1** Fase 4b Email Assistant refactor (urgencias sin regla, AMD GAIA, conflict detection).
- ✅ **V0.7.2** God-endpoint split (email_assistant → 7 routers), bug json/log_activity fixed.
- ✅ **V0.7.3** Email Assistant TERMINADO (7 categorías triaje, autonomía gradual Inbox Zero).
- ✅ **V0.8** Gateway + Telegram + DPAPI + voz (Whisper + 4 TTS) + CORS + conversación continua.

---

## Fases pendientes (orden roadmap 2026-07-04)

### 🎯 V0.82 — Hub Visual (pulido UI)

- Animación de conversación en el Hub (chat con vida).
- Modo pantalla completa con botones para desplegar/plegar barras laterales.
- Polish de AICore.tsx + custom shaders.
- Refactor de Framer Motion transitions.

### 🎯 V0.83 — Voz completa

- Terminar configuración de voces ElevenLabs.
- STT real (faster-whisper `distil-large-v3`).
- TTS multi-proveedor (ElevenLabs primary, EdgeTTS fallback, Kokoro local, eSpeak ultra-fallback).
- Wake word opcional ("Hey Aithera") V0.83+ con Porcupine u openWakeWord.
- Barge-in (interrupción de user durante TTS).

### 🎯 V0.85 — MOS Memory Operating System

- **Ingesta proactiva** desde Gmail/Calendar (sync cada N min).
- **Briefings diarios** automáticos.
- **Skills capture** (auto-detección de skills del user).
- **Context de proyectos** (memory por proyecto).
- **Patrones de trabajo** (ML para detectar hábitos).
- **Hybrid search** BM25 + semantic + RRF.
- **Reranking** con cross-encoder (BAAI/bge-reranker).
- **Oblivion** (selective memory pruning).
- **pgvector migration** desde ChromaDB (opcional, hybrid).
- Diseño completo en `PLAN_MAESTRO_2026/07_MOS_V085_DISENO.md` y `08_MOS_ARQUITECTURA_COMPLETA.md`.

### 🎯 V0.9 — Automation Engine

- **APScheduler** + SQLAlchemy jobstore.
- **Rule engine** JSON-based (trigger, condition, action, approval_required).
- **Approval gates** formales (Hub UI + Telegram inline).
- **Trigger types**: cron, interval, event, webhook, manual.
- **Action types**: email.*, calendar.*, chat.*, agent.run, custom.
- **Reglas predefinidas** (1-click enable).
- Diseño en `PLAN_MAESTRO_2026/11_AUTOMATION_ORCHESTRATOR_RFC.md`.

### 🎯 V1.0 — Orchestrator + Claude Code Agent (MVP BETA)

- **Intent classifier** (clasificación: query, create, execute, automate, conversational).
- **Task Planner** (sobre AI Manager, multi-step).
- **Response Builder**.
- **Claude Code Agent** (coding tasks).
- **State machine** (checkpointing + resume).
- **Routing por complejidad** (cheap local model para triage, premium para deep).
- **Approval gates** generalizados.
- **Trace logging** (P5 del Plan Maestro).
- Cambio clave: `gateway.set_handler(orchestrator)` reemplaza chat_message_handler.
- Diseño en `PLAN_MAESTRO_2026/11_AUTOMATION_ORCHESTRATOR_RFC.md` + `12_AUDITORIA_OPTIMIZACION.md`.

### 🎯 V1.1 — Hermes Integration

- Hermes Agent (Nous Research) como runtime de agents.
- **Skills/SKILL.md** system借鉴 obra/superpowers.
- **MCP server/client** para tools.
- **Local Skill Library (LSL)** + **Local Learning Loop (LLL)**.
- Diseño en `PLAN_MAESTRO_2026/10_HERMES_INTEGRATION_RFC.md` + `09_LSL_LLL_RFC.md`.

### 🎯 V1.2 — MCP + potenciación

- Aithera como **MCP server** (exponer memory + tools).
- Consumir **MCP servers externos** (filesystem, github, postgres).
- Marketplace de skills.

### 🎯 V1.5 — AVCS MVP1

- **AVCS** (Aithera Visual Conversational State) — 7 ritmos.
- UI rediseñada.
- **TIE Cognitive Runtime** (memoria a largo plazo personalizada).
- **LSLL** (Learning System Layer).
- Diseño en `PLAN_MAESTRO_2026/13_AVCS_DISENO_MAESTRO.md` + `14_TIE_COGNITIVE_RUNTIME_DISENO.md` + `15_LEARNING_SYSTEM_DISENO.md`.

### 🎯 V2.0+ — GSN + CIE + Guardians

- **GSN** (Global State Network).
- **CIE** (Cognitive Integration Engine).
- **Guardians** (safety agents).

### 🔮 Post-V1.0 — Web + PWA + PIN

- Build de React servido por FastAPI en `/app`.
- PWA (manifest + service worker).
- PIN/token de red.
- Microsoft Store MSIX.
- Mac/Linux desktop (electron-builder cross-compile).

---

## Backlog (Sprint planning)

### Sprint V0.82 (próximo)

- [ ] Animación de conversación en el Hub.
- [ ] Polish AICore.tsx shaders.
- [ ] Optimizar render performance (CLAUDE.md §1 "perf hub" pendiente).

### Sprint V0.83

- [ ] ElevenLabs setup final.
- [ ] faster-whisper production setup.
- [ ] Kokoro integration tests.
- [ ] Conversation continua VAD con Silero VAD.

### Sprint V0.85 (CRÍTICO)

- [ ] MOS Skeleton (Plan Maestro §07).
- [ ] Briefings diarios.
- [ ] Ingesta Gmail/Calendar.
- [ ] Hybrid search + reranking.
- [ ] Oblivion pattern.

### Sprint V0.9

- [ ] APScheduler con SQLAlchemy jobstore.
- [ ] Approval flow UI.
- [ ] 8+ reglas predefinidas.

### Sprint V1.0 (BETA distribuible)

- [ ] Intent classifier.
- [ ] Task Planner.
- [ ] Claude Code Agent integration.
- [ ] Trace logging.
- [ ] Orchestrator vs chat handler swap.

---

## JWIKI Status (referencia)

- **271/267 docs verificados** (100%).
- **16 dominios completos**.
- Wiki-map es mapa de **interconexiones por temas** (no por IDs).
- **Skill `jwiki-tick`** mantiene el loop de actualización continua.
- Audit cadence: cada 2-3 días (cron `jwiki-tick-a`).

---

## Tareas abiertas por sub-equipo

### Backend

- [ ] Continuar separación routers (ya hecho en email).
- [ ] DB query optimization (CLAUDE.md §16 "Auditoría optimización" pendiente).
- [ ] Observability: Prometheus metrics (V0.85+).

### Frontend

- [ ] Hub animation polish (V0.82).
- [ ] TTS streaming player (V0.83+).
- [ ] Approval flow UI components (V0.9).

### Memory (V0.85)

- [ ] Hybrid search BM25 + semantic.
- [ ] Reranker integration.
- [ ] Oblivion pattern.
- [ ] Migration tooling ChromaDB ↔ pgvector.

### Agents (V1.0)

- [ ] Orchestrator.
- [ ] Multi-agent handoffs (OpenAI Agents SDK借鉴).
- [ ] State machine + checkpointing.

---

*Última actualización: 2026-07-09 (WIKI 100% completa + roadmap actualizado).*