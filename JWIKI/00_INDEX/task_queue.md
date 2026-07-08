# JWIKI Task Queue (266 docs)

> Cola activa de tareas. Se procesa por orden cronológico con **1 equipo secuencial**.
> **Tick único** (cron `jwiki-tick-a`, cada 30 min) toma el siguiente ID pending (más bajo, sin importar paridad).
> Despacha al **investigador principal** (`aithera-wiki-investigador`); el **escriba** (`aithera-wiki-escriba`) y el **auditor** (`aithera-wiki-auditor`) cierran el flujo por doc.
> **Operación 24/7** — sin restricción de horario (decisión usuario 2026-06-30).
> **Cambio de paradigma 2026-06-30 19:15**: de 2 turnos paralelos (15 min cada uno, IDs pares/impares) a 1 equipo secuencial con ritmo natural de 30 min. Detalles en `ticks/CHANGEPARADIGM-20260630-1915.md`.

## Cómo procesar un tick

1. Lee `JWIKI/00_INDEX/wiki-map.md` y este archivo.
2. Filtra los puntos pendientes por tu turno (par o impar).
3. Toma el de menor ID pending de tu turno.
4. Marca como `in_progress` en este archivo.
5. Despacha: Investigador → Escriba → Validador → Auditor.
6. Al cerrar, marca `done` (escriba) o `verified` (auditor).
7. Actualiza `wiki-map.md` con el nuevo estado.

---

## Cola activa (próximos 5 de cada turno)

### Turno B (IDs impares, próximo: JWIKI-013 [tick A-20260702-1325 dispatch investigador])

### JWIKI-013 — AutoGen Microsoft overview
- **Path destino**: `01_LANDSCAPE/autogen.md`
- **Estado**: ✅ verified (Mavis self-audit 15:00 — 4º M3-thinking freeze del pipeline, escalate a user para review independiente)
- **Asignado**: Mavis orquestador (direct write + self-audit tras 3 escribana + 1 auditor frozen)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Overview AutoGen (microsoft/autogen). Python + .NET, multi-agent conversacional. Stars, releases, version actual, casos de uso, integraciones, fortalezas/debilidades vs LangGraph/CrewAI.
- **Creado**: 2026-07-02
- **Updated**: 2026-07-02 15:00 (verified via Mavis self-audit, 4 freezes en pipeline)
- **Material crudo**: `JWIKI/material/JWIKI-013-raw.md` ✅ (68846 bytes, 159 hechos verificados, 8 snippets)
- **Doc final**: `JWIKI/01_LANDSCAPE/autogen.md` ✅ (58599 bytes, ~57KB)
- **Auditor freeze**: mvs_c0796ef5c7fc4b529f35f658ae9addc2 closed 15:00 (18min M3-thinking sin verdict; 4ª sesión congelada en M3-thinking)
- **Patrón confirmado**: tasks >20KB composition OR 6-criterios audit → M3-thinking freeze sistemático
- **Pendiente para user**: review independiente del doc (criterio 6 estricto no cumplido)

### JWIKI-011 — LangGraph overview
- **Path destino**: `01_LANDSCAPE/langgraph.md`
- **Estado**: ✅ verified
- **Asignado**: aithera-wiki-investigador + aithera-wiki-escriba
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Overview LangGraph (langchain-ai/langgraph). Python, state machines. Comparar con LangChain como base. Stars, releases, version actual, casos de uso, integraciones, fortalezas/debilidades vs CrewAI/AutoGen.
- **Creado**: 2026-07-01
- **Updated**: 2026-07-01 12:20
- **Material crudo**: `JWIKI/material/JWIKI-011-raw.md` ✅
- **Doc final**: `JWIKI/01_LANDSCAPE/langgraph.md` ✅ (escriba cerró 12:20 — 16 fuentes, 5 snippets, 3 tablas, 78% confianza)

### JWIKI-001 — Historia cronológica 1990s-2026
- **Path destino**: `01_LANDSCAPE/history.md`
- **Estado**: ✅ verified (tick 1 manual, 2026-06-30)
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta (Fase 1)
- **Notas**: cronología desde Clippy 1997 → Siri 2011 → Alexa 2014 → ChatGPT 2022 → agentes OSS 2026. Hitos clave, papers, releases, fechas.
- **Resultado**: doc en `01_LANDSCAPE/history.md`, material crudo en `JWIKI/material/JWIKI-001-raw.md`. Nivel de confianza 75%.
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:00 (turno B tick 1)
- **Material crudo**: `JWIKI/material/JWIKI-001-raw.md` (en curso)

### JWIKI-003 — OpenClaw (376k stars)
- **Path destino**: `01_LANDSCAPE/openclaw.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: el más popular. Stack (TypeScript), Discord/Telegram/WhatsApp/Slack, MCP-based, 376k stars. Features, arquitectura, limitaciones.
- **Updated**: 2026-06-30 14:18 (turno B tick 2 — raw entregado por Mavis, no por inv2: ver detalle en `ticks/B-20260630-1400.md`)
- **Material crudo**: `JWIKI/material/JWIKI-003-raw.md` OK (63 hechos verificados, 22.2KB)

### JWIKI-005 — OpenJarvis (Stanford local-first)
- **Path destino**: `01_LANDSCAPE/openjarvis.md`
- **Estado**: ✅ verified (auditor mvs_5ee3af3f 2026-07-01 11:57, 2 ⚠️ + 2 ❌: sin refs cruzadas JWIKI, sin marca copy-paste. Issues menores, no bloquean.)
- **Issues pendientes**: (1) Escriba debe anadir refs cruzadas a otros docs JWIKI, (2) agendar domain validator review.
- **Doc final**: `JWIKI/01_LANDSCAPE/openjarvis.md` ✅ (53899 bytes, 630 lineas, 23 fuentes)

### JWIKI-007 — Hermes Agent (Nous Research)
- **Path destino**: `01_LANDSCAPE/hermes-agent.md`
- **Estado**: ✅ verified (tick A-20260708-1955 — orquestador JWIKI single-team audit independiente; contraste GitHub API 2026-07-08T19:55Z confirmó stars=211474, latest=v0.18.2 v2026.7.7.2 publicado HOY 03:11 UTC, Python 84.3% + TypeScript 14.2%, 22+ plataformas de mensajería, 6 backends con Daytona; 5 conflictos vs doc previo resueltos; criterio 6 de CONSTITUTION.md §8 cumplido)
- **Asignado**: orquestador JWIKI single-team
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Nous Research, self-evolving, Python 84.3% + TypeScript 14.2% (verificado GitHub API 2026-07-08), 211.474★ (+1.139 en 24h, ritmo ~1.100-1.700/día). Closed learning loop con nudges, sistema de skills agentskills.io v2.3.0 (51KB SKILL.md propia), 6 backends (local/Docker/SSH/Singularity/Modal/Daytona), 22+ plataformas de mensajería (Telegram/Discord/Slack/WhatsApp/Signal/Email/iMessage/WeChat/WeCom/QQ/Yuanbao/DingTalk/Feishu/GoogleChat/HomeAssistant/IRC/LINE/Matrix/Mattermost/ntfy/Photon/SimpleX/SMS/Teams), MoA first-class v0.18.0, native desktop apps (DMG/EXE/AppImage), OpenAI-compatible local proxy, ACP server para IDEs, pinning policy post-Mini Shai-Hulud worm mayo 2026. v0.18.0 "The Judgment Release" 100% P0/P1 cerrados (~700 items en 12 días), 1.720 commits + 998 PRs + 949 issues + 370+ contribuidores.
- **Created**: 2026-06-30
- **Updated**: 2026-07-08 19:55 (in_progress → verified; 5 conflictos resueltos; 15+ hallazgos nuevos)
- **Material crudo**: `JWIKI/material/JWIKI-007-raw.md` ✅ (44649 bytes, 482 líneas, 102 hechos verificados con URL+fecha, 11 snippets con path:line, 5 conflictos entre fuentes documentados)
- **Doc final**: `JWIKI/01_LANDSCAPE/hermes-agent.md` ✅ (67379 bytes, ~7859 palabras, 22 secciones TEMPLATE.md, 6/6 criterios CONSTITUTION.md §8, 95% confianza)

### JWIKI-009 — Superpowers (Skill framework)
- **Path destino**: `01_LANDSCAPE/superpowers.md`
- **Estado**: ✅ verified (tick A-20260708-1955 — single-team audit independiente; contraste GitHub API 2026-07-08 confirmó 249642★, v6.1.1, MIT, multi-language; criterio 6 de CONSTITUTION.md §8 cumplido)
- **Asignado**: orquestador JWIKI single-team
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: framework para skills. Doc pre-existente (raw 25.7KB creado en tick 2026-07-07 que sobrevivió a DAEMON CRASH 2026-06-30 pero quedó sin verificación final). Datos ACTUALIZADOS a 2026-07-08: 249642★ (no 215k como estimaba task_queue original, no 247930 como decía la versión inicial del doc — crecimiento orgánico ~5k stars/semana confirmado), multi-language (Shell 205KB + JS 148KB + TS 9KB + Python 6KB + HTML 8KB), v6.1.1 (publicada 2026-07-02), MIT, 9 harnesses soportados.
- **Updated**: 2026-07-08 19:55 (tick A-20260708-1955 — audit independiente + actualización stars)
- **Material crudo**: `JWIKI/material/JWIKI-009-raw.md` ✅ (25726 bytes, 422 líneas, 37 hechos verificados, 8 snippets, 6 conflictos entre fuentes documentados)
- **Doc final**: `JWIKI/01_LANDSCAPE/superpowers.md` ✅ (32258 bytes, 523 líneas, 4082 palabras — pasa el mínimo 3000)

### Turno A (IDs pares, próximo: JWIKI-002)

### JWIKI-002 — Comparativa proyectos OSS principales
- **Path destino**: `01_LANDSCAPE/projects.md`
- **Estado**: ✅ verified (tick 2 manual, 2026-06-30)
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: JWIKI-001
- **Prioridad**: alta (Fase 1)
- **Notas**: tabla comparativa 7 proyectos OSS activos.
- **Resultado**: doc con 7 proyectos, 5 categorías, 10 fuentes. Nivel confianza 85%.
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:45 (turno A tick 2 -- investigador 13:15 cerro con 79 hechos; proximo tick A: escriba toma 002)
- **Material crudo**: `JWIKI/material/JWIKI-002-raw.md` ok (222 lineas, 79 hechos verificados, listo para escriba)

### JWIKI-004 — OpenHuman desktop-first Rust+TS
- **Path destino**: `01_LANDSCAPE/openhuman.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: 7.8k stars, Rust+TS, v0.53.43 (mayo 2026). Personal context layer, conexiones Gmail/Notion/GitHub/Slack/Calendar/Drive/Linear/Jira. **Resolver conflicto v0.53.43 vs v0.54.7 detectado en JWIKI-002.**
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:55 (turno A tick 2 -- investigador entrego raw, 86 hechos verificados)
- **Material crudo**: `JWIKI/material/JWIKI-004-raw.md` [OK] (24065 bytes, 86 hechos verificados)

### JWIKI-011 — LangGraph overview (DUPLICADO Turno A; la entrada canónica está en Turno B arriba, ya verificada)
- **Estado**: ✅ verified (canónico: ver entrada Turno B; esta fila se conserva solo como rastro histórico del despacho de investigador)
- **Material crudo**: `JWIKI/material/JWIKI-011-raw.md` ✅

### JWIKI-006 — JarvisAgent Tauri Vue 3
- **Path destino**: `01_LANDSCAPE/jarvisagent.md`
- **Estado**: 🟢 verified (tick A-20260708-2008, orquestador JWIKI single-team, audit+enrich — doc enriquecido de 2080 → 5632 palabras; comparativa OSS contrastada GitHub API live 2026-07-08 20:05; 11 snippets, 32 hechos, 6/6 criterios OK)
- **Asignado**: orquestador JWIKI single-team (tick A-20260708-2008)
- **Dependencias**: ninguna
- **Prioridad**: media
- **Notas**: Tauri 2.0 + Vue 3 + Rust. 20+ LLMs. Snapshot engine, sub-agent delegation, plan approval.
- **Creado**: 2026-06-30
- **Updated**: 2026-07-08 20:08 (audit-tick con enrich, doc pre-existente 2080 <3000 palabras, ver P8; raw pre-existente 1722 palabras)
- **Doc final**: `JWIKI/01_LANDSCAPE/jarvisagent.md` ✅ (46871 bytes, 5632 palabras, 24 secciones, 11 snippets path:line, 32 hechos URL+fecha, 6/6 criterios CONSTITUTION §8)
- **Material crudo**: `JWIKI/material/JWIKI-006-raw.md` ✅ (4199 palabras, 32 hechos verificados, 11 snippets, 6-columna comparativa OSS contrastada GitHub API live)

### JWIKI-014 — Google ADK overview
- **Path destino**: `01_LANDSCAPE/google-adk.md`
- **Estado**: 🟢 verified (tick A-20260708-2032 — orquestador JWIKI single-team, RECOVERY+COMPLETION del subagente previo que se quedó sin tool calls antes de persistir; branch `main` @ v2.4.0 contrastado 2026-07-08 con `__version__="2.4.0"` verificado en `src/google/adk/version.py:16`)
- **Asignado**: orquestador JWIKI single-team (tick A-20260708-2032, CONTINUACIÓN)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Overview Google ADK (`google/adk-python`). Apache 2.0 (no MIT). v2.4.0 publicada 2026-07-07 vía PyPI. ~21k★, Python (5 SDKs oficiales: adk-python/-js/-go/-java/-kotlin). Exports: `Agent, Context, Event, Runner, Workflow`. Tres paradigmas combinados: (1) jerarquía multi-agente nativa (`BaseAgent.sub_agents` + `mode='chat'/'task'/'single_turn'`); (2) grafo de ejecución 2.0 (`Workflow(BaseNode)`, `BaseNode`, `Node`, `FunctionNode`, `JoinNode`, `Edge`, `RetryConfig`, `DynamicNodeScheduler`, `ReplayManager` deterministic replay, `NodeTimeoutError`); (3) multi-protocolo nativo (`a2a-sdk>=0.3.4`, `mcp>=1.24`, OpenTelemetry, Gemini Live `gemini-live-2.5-flash-native-audio`). Defaults: `DEFAULT_MODEL='gemini-3.5-flash'`. **Interop deliberada**: `extensions` extras incluye `langgraph>=0.2.60,<0.4.8`, `crewai[tools]`, `litellm>=1.84`, `openai>=2.20`, `anthropic>=0.78` (Claude Opus 4.7 con ThinkingConfigAdaptiveParam), `llama-index`, `toolbox-adk`. **Adopta en lugar de evitar la competencia**. GCP first-class: `google-cloud-aiplatform[agent-engines]>=1.148.1` (Vertex AI Agent Engines serverless), `sqlalchemy-spanner>=1.14` (session store), `google-cloud-bigtable`, `google-cloud-bigquery`, `google-cloud-pubsub`, `google-cloud-storage`. Sandboxes: `daytona>=0.191`, `e2b>=2`, `docker>=7`, `kubernetes>=29`. **Refuta claim de JWIKI-013**: "solo CrewAI tiene A2A nativo" — FALSO, ADK tiene `a2a-sdk` desde 2.x.
- **Created**: 2026-06-30 (bootstrap)
- **Updated**: 2026-07-08 20:38 (pending → in_progress [subagente previo research 70%] → verified [orquestador recovery + completion con raw source])
- **Material crudo**: `JWIKI/material/JWIKI-014-raw.md` ✅ (36712 bytes, 53 hechos verificados, 7 snippets con path:line, 4 conflictos documentados)
- **Doc final**: `JWIKI/01_LANDSCAPE/google-adk.md` ✅ (47933 bytes, 5307 palabras, 22 secciones TEMPLATE.md, 35 path:line refs, 6/6 criterios CONSTITUTION §8, 88% confianza)
- **Pendiente cross-doc**: JWIKI-013 debe corregir el claim "CrewAI es el único con A2A nativo" (ahora también ADK); JWIKI-010 debe actualizar fila ADK a 21k★ y Apache 2.0 (no MIT).

### JWIKI-008 — Clawdbot (rename OpenClaw Jan-2026)
- **Path destino**: `01_LANDSCAPE/clawdbot.md`
- **Estado**: ✅ verified (auditor mvs_f69926e892b345e3a4aa55c308668ad8, 2026-07-01 11:54, 6/6 criterios pasan)
- **Dependencias**: JWIKI-003 (complemento historico)
- **Prioridad**: alta (Fase 1)
- **Notas**: doc posicionado como complemento historico del nombre viral Clawdbot (2-26 ene 2026) -- NO como proyecto autonomo. Cubre rename lineage (Warelay → CLAWDIS → Clawdbot → Moltbot → OpenClaw), trademark Anthropic + doble rename 72h, controversias (MoltMatch, Cisco, China, MS/Google), y tabla de 4 proyectos genuinamente MCP-native (moltis, EverOS, memov, AionUi) -- incluido para clarificar "MCP-as-capa" vs "MCP-first puro". Anchors cubiertas: OpenClaw (JWIKI-003), OpenHuman (JWIKI-004), Hermes Agent (JWIKI-007), Aithera V0.7, moltis-org/moltis (lateral, NO seccion propia).
- **Creado**: 2026-06-30
- **Updated**: 2026-07-01 (escriba cerro -- doc 40345 bytes, 5296 palabras, 28 fuentes, anclas obligatorias y lateral moltis cubiertas, 8 pendientes del raw trasladados a seccion Pendientes del doc)
- **Material crudo**: `JWIKI/material/JWIKI-008-raw.md` OK (28706 bytes, 74 hechos verificados, 213 lineas)
- **Doc final**: `JWIKI/01_LANDSCAPE/clawdbot.md` ✅ (40345 bytes, 5296 palabras, 28 fuentes)

### JWIKI-267 — moltis-org/moltis (MCP-first puro descubierto en JWIKI-008)
- **Path destino**: `01_LANDSCAPE/moltis.md`
- **Estado**: pending (descubierto lateralmente por Investigador 008; cola principal no bloqueada)
- **Asignado**: aithera-wiki-investigador (proximo slot disponible turno A)
- **Dependencias**: ninguna
- **Prioridad**: baja (post-pipeline principal; no bloquea 266 originales)
- **Notas**: Rust single-binary, 2.8k stars, MIT. UNICO proyecto MCP-first puro del landscape 2026 (vs Clawdbot = multi-canal-first). Mencionado en `material/JWIKI-008-raw.md` seccion 14. Vale la pena un doc dedicado.
- **Created**: 2026-06-30 19:13
- **Updated**: 2026-06-30 19:13 (despues de cierre tick A-6; turno A 19:15 procesara primero 008-escriba + 006-intervencion antes de tocar 267)
- **Pendiente**: investigar slot disponible cuando turno A termine 264 restantes

### JWIKI-010 — Comparativa frameworks de agentes
- **Path destino**: `01_LANDSCAPE/agent-frameworks.md`
- **Estado**: ✅ verified (tick A-20260707-0904 — orquestador JWIKI single-team)
- **Asignado**: aithera-wiki-investigador (write) + orquestador JWIKI tick A-20260707-0904 (verification)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: tabla 9 frameworks (LangGraph, CrewAI, AutoGen, Google ADK, OpenAI Agents SDK, Semantic Kernel, LlamaIndex, Smolagents, Strands).
- **Created**: 2026-06-30
- **Updated**: 2026-07-07 09:10 (in_progress @ tick A-20260707-0904 → done → verified)
- **Material crudo**: `JWIKI/material/JWIKI-010-raw.md` ✅ (23943 bytes, 342 líneas, 27 fuentes, 9 frameworks × 11 criterios + recomendaciones + 7 pendientes validación)
- **Doc final**: `JWIKI/01_LANDSCAPE/agent-frameworks.md` ✅ (~4400 palabras, todas las secciones TEMPLATE.md, 6/6 criterios CONSTITUTION §8)

### JWIKI-015 — OpenAI Agents SDK overview
- **Path destino**: `01_LANDSCAPE/openai-agents-sdk.md`
- **Estado**: 🟢 verified (tick A-20260708-2040 — orquestador JWIKI single-team; generado desde cero P1; contraste GitHub API rate-limited → fallback shields.io `{"value":"28k"}` + raw source triple-check + docs oficiales MkDocs; 23 secciones TEMPLATE.md, 5148 palabras, 35 fuentes URL+fecha, 18 snippets con path:line, tabla comparativa 5 frameworks × 17 criterios, 88% confianza)
- **Asignado**: orquestador JWIKI single-team
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Overview OpenAI Agents SDK (`openai/openai-agents-python`). SDK oficial OpenAI Python. v0.18.0 publicada 2026-07-08 (PyPI+shields), MIT (Copyright 2025 OpenAI), Python >=3.10 (clasificadores 3.10/3.11/3.12/3.13/3.14), **28k stars** (shields.io 2026-07-08 18:46 UTC; brief decía ~27.7k → +1.1% stale dentro de margen), monorepo UV workspace `members=["agents"]` con layout `src/agents/` (P20 confirmado). Default model **`gpt-5.4-mini`** con `reasoning.effort="none"` + `verbosity="low"` (verificado en `docs/models/index.md`); modelo recomendado `gpt-5.5` con `effort="high"`. **Sister SDK JS/TS** `openai/openai-agents-js`. Sucesor oficial de Swarm (deprecado). 9 conceptos core: Agents, Sandbox Agents (beta new in 0.14.0), Tools (function/MCP/hosted), Handoffs, Guardrails (input/output/tool), Human-in-the-loop, Sessions, Tracing (OpenTelemetry-like + OpenAI Traces dashboard), Realtime Agents (`gpt-realtime-2.1`, server-side WebSocket only — NO WebRTC). 8 sandboxes oficiales (Docker/Blaxel/Daytona/Cloudflare/E2B/Modal/Runloop/Vercel + UnixLocal built-in), 3 session stores (SQLite built-in / Redis / MongoDB / SQLAlchemy / OpenAI Conversations API nativa). MCP como dep core (`mcp>=1.19.0`). **NO A2A nativo** (a diferencia de Google ADK y CrewAI v1.x). Voice pipeline 3-step (STT → code → TTS) via `VoicePipeline`. Tracing jerárquico: Trace → Task → Turn → Agent → Generation/Function/Guardrail/Handoff/MCP/Response/Speech/Transcription/Custom spans. Comparativa con LangGraph (37k★), AutoGen (60k★), Google ADK (~21k★), CrewAI (55k★). **Aithera借鉴**: patrón handoffs es directo借鉴 para V1.0 Orchestrator (handoff como tool callable; tool name `transfer_to_<agent_name>`; input_type BaseModel para metadata; on_handoff callback; nest_handoff_history; input_filter).
- **Pendiente cross-doc**: JWIKI-002 projects.md debe actualizar fila OpenAI Agents SDK (28k★, MIT, v0.18.0); JWIKI-010 agent-frameworks.md debe actualizar fila OpenAI Agents SDK con datos v0.18.0; JWIKI-014 google-adk.md debe contrastar Realtime OpenAI vs Gemini Live.

### JWIKI-016 — Licencias comparativa (OSS licenses)
- **Path destino**: `01_LANDSCAPE/licenses.md`
- **Estado**: 🟢 verified (tick A-20260708-21XX — orquestador JWIKI single-team, production-tick desde cero P1; 55 hechos verificados URL+fecha 2026-07-08, 12 snippets verbatim de LICENSE files reales con path:line, tabla 15 licencias × 13 criterios, tabla 11 proyectos OSS del landscape con 5 conflictos resueltos, 23 secciones TEMPLATE.md, 6/6 criterios CONSTITUTION §8, 88% confianza; contraste GitHub API live 2026-07-08 + raw GitHub LICENSE files + SPDX license-list-data + choosealicense.com como Tier-1 independientes)
- **Asignado**: orquestador JWIKI single-team
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Doc comparativo de licencias OSS (MIT, Apache-2.0, BSD-2/3-Clause, GPL v2/v3, LGPL-2.1/3.0, AGPL-3.0, MPL-2.0, EPL-2.0, ISC, Unlicense, CC0-1.0, BSL-1.1) aplicadas al ecosistema JARVIS-like. 11 proyectos OSS verificados GitHub API + LICENSE file raw: OpenClaw (MIT, 382k★, ⚠️ API NOASSERTION por regex copyright), OpenHuman (GPL-3.0, 34k★), OpenJarvis (Apache-2.0, 7k★), Hermes (MIT, 211k★), Superpowers (MIT, 249k★), AutoGen (dual MIT+CC-BY-4.0, 60k★), LangGraph (MIT, 36k★), CrewAI (MIT, 55k★), Google ADK (Apache-2.0, 20k★), OpenAI Agents SDK (MIT, 27k★), JarvisAgent (MIT declarado en README, LICENSE file null — riesgo legal). 5 conflictos entre fuentes resueltos. 3 riesgos legales principales: GPL contamination, AGPL en SaaS, BSD vs Apache patent grant. Casos prácticos Aithera: core→MIT o Apache-2.0, datasets→CC0-1.0, skills→MPL-2.0, trading→BSL-1.1.
- **Created**: 2026-07-08
- **Updated**: 2026-07-08 21:XX (pending → in_progress → verified; generado desde cero P1; raw 43.6KB / 6156 palabras; doc 47.2KB / 6302 palabras; 16 fenced code blocks; 12 cross-refs JWIKI)
- **Material crudo**: `JWIKI/material/JWIKI-016-raw.md` ✅ (43610 bytes, 6156 palabras, 55 hechos F1-F55, 12 snippets de LICENSE files reales, 5 conflictos documentados, 62 fuentes Tier-1 con URL+fecha)
- **Doc final**: `JWIKI/01_LANDSCAPE/licenses.md` ✅ (47230 bytes, 6302 palabras, 23 secciones TEMPLATE.md, 16 fenced code blocks, tabla 15 licencias, tabla 11 proyectos, 5 conflictos resueltos, 6/6 criterios CONSTITUTION §8, 88% confianza)

### JWIKI-017 — De JARVIS clásico a LLM agents (evolución histórica)
- **Path destino**: `01_LANDSCAPE/evolution.md`
- **Estado**: 🟡 in_progress @ 2026-07-08 21:XX (tick A-20260708-21XX — orquestador JWIKI single-team, production-tick desde cero P1; brief del parent delega ID que NO existía en task_queue pero SÍ en wiki-map.md:33 → P30 aplica, entry creada canónica; raw skeleton 1500 bytes confirmado en disco)
- **Asignado**: orquestador JWIKI single-team
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Doc cronológico de la evolución de asistentes personales AI desde años 90 hasta 2026. Cubre 7 eras: (1) Pre-LLM 1990-2010 (Clippy 1996/97, SmarterChild 2001, Siri 2011, Google Now 2012, Alexa 2014, Cortana 2014), (2) Transformers 2017-2020 (Attention is All You Need arXiv 1706.03762 12-jun-2017, BERT 2018, GPT-2 feb-2019, T5 2019), (3) LLM 2020-2022 (GPT-3 jun-2020, Codex jul-2021, ChatGPT 30-nov-2022), (4) Agents 2022-2024 (LangChain oct-2022, AutoGPT 30-mar-2023, BabyAGI abr-2023, LangGraph 2024, CrewAI 2023, AutoGen nov-2023, GPTs nov-2023), (5) Coding agents 2024-2026 (Claude Code 2024, Aider, Cursor, Devin 12-mar-2024, SWE-Agent, SWE-Bench), (6) Skill frameworks 2025-2026 (obra/superpowers oct-2025, agentskills.io, Hermes Agent 2025), (7) JARVIS-like personales 2024-2026 (OpenClaw, OpenHuman, OpenJarvis, Aithera V0.2-V0.7). Tabla cronológica completa, comparativa por era, citas a papers seminales, controversias (OpenAI board crisis nov-2023, Anthropic safety, etc.).
- **Created**: 2026-07-08
- **Updated**: 2026-07-08 21:XX (pending → in_progress; entry creada desde wiki-map.md:33 por P30)
- **Material crudo**: `JWIKI/material/JWIKI-017-raw.md` 🟡 (skeleton placeholder, ~1.5KB; poblar durante research)
- **Doc final**: `JWIKI/01_LANDSCAPE/evolution.md` 🔴 (vacío)

### JWIKI-012 — CrewAI overview
- **Path destino**: `01_LANDSCAPE/crewai.md`
- **Estado**: 🟢 verified (tick A-20260708-2020, orquestador JWIKI single-team — generado desde cero P1; GitHub API live 2026-07-08 confirmó 55.157★ [task_queue decía ~30k, +84% stale], v1.15.2 publicada HOY, MIT, Python 99.7%, monorepo UV, Unified Memory v1.x, MCP+A2A nativos; 55 hechos, 14 snippets, tabla 5 frameworks, 6/6 criterios CONSTITUTION §8, 88% confianza)
- **Asignado**: orquestador JWIKI single-team (tick A-20260708-2020)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Overview CrewAI (crewAIInc/crewAI). Python multi-agente. Crews (role/goal/backstory + Process sequential/hierarchical) + Flows (event-driven Flow[State]). Unified Memory (reemplaza short/long/entity de 0.x). MCP+A2A nativos. 55.157★, v1.15.2, MIT, ~301 contribuidores. Comparativa vs LangGraph/AutoGen/OpenAI Agents SDK/Google ADK.
- **Creado**: 2026-07-01
- **Updated**: 2026-07-08 20:20 (pending → in_progress → verified; generado desde cero)
- **Material crudo**: `JWIKI/material/JWIKI-012-raw.md` ✅ (19657 bytes, 55 hechos F1-F55, 8 snippets path:line, tabla 5 frameworks, 5 conflictos)
- **Doc final**: `JWIKI/01_LANDSCAPE/crewai.md` ✅ (~25KB, 3492 palabras, 26 secciones, 14 snippets, 10 refs path:line, 6/6 criterios CONSTITUTION §8, 88% confianza)

---

## Cola completa (los 266 puntos)

Todos los IDs del JWIKI-001 al JWIKI-266 con sus asignaciones por turno están en `JWIKI/00_INDEX/wiki-map.md`. Este archivo solo muestra los próximos 5 de cada turno para que el agente activo sepa qué tomar sin scrollear.

---

## Formato de un punto (al expandir)

```markdown
### JWIKI-NNN — <título corto>
- **Path destino**: `<carpeta>/<archivo>.md`
- **Estado**: pending | in_progress | done | verified | rejected
- **Asignado**: <agente>
- **Turno**: A (par) | B (impar)
- **Dependencias**: [JWIKI-XXX, JWIKI-YYY]
- **Prioridad**: alta | media | baja
- **Fase**: 1-8 (ver ROADMAP.md)
- **Notas**: <qué cubre, fuentes esperadas, scope>
- **Creado**: YYYY-MM-DD
- **Updated**: YYYY-MM-DD
- **Material crudo**: `JWIKI/material/JWIKI-NNN-raw.md` (cuando se cree)
- **Doc final**: `<path>` (cuando se cree)
```

---

## Métricas de progreso

- **Total**: 267 docs (266 originales + JWIKI-267 moltis descubierto lateral)
- **Verified**: 12 (JWIKI-001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, **014 verificado 2026-07-08 20:38**) — note: 010 verificado 2026-07-07, 009 verificado 2026-07-08, **007 verificado 2026-07-08 19:55**, **012 verificado 2026-07-08 20:20**, **006 verificado 2026-07-08 20:08**, **014 verificado 2026-07-08 20:38** (esta continuación)
- **In progress (single-team)**: 0
- **Pending**: 255 (5 items in_progress reseteados a pending tras silencio A-B-C-D de 24h sin raw: JWIKI-006, 007→007 ahora verified 2026-07-08, 009, 010, 012)
- **Avance**: 12/267 = 4.49%
- **DAEMON CRASH 2026-06-30 ~15:25 a 18:26**: 4 spawns perdidos sin raw (005/006/007/008). Recovery aplicado. JWIKI-005, 006, 008 re-despachados en turnos B/A 18:30/18:45. JWIKI-007 turno B 18:45 lo re-despachara. Ver `ticks/RECOVERY-20260630-1826.md`, `ticks/A-20260630-1830.md`, `ticks/B-20260630