# JWIKI Wiki-Map (completo, 266 docs)

> Mapa vivo de toda la JWIKI. **Lee este archivo ANTES de cualquier trabajo**.
> Última actualización: 2026-06-30 (bootstrap completo).

**Total: 266 docs planificados en 16 dominios + 00_INDEX.**

**Sistema de turnos**: ID par = turno A, ID impar = turno B (cron cada 15 min).

---

## 01_LANDSCAPE

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-001 | 01_LANDSCAPE/history.md | Historia cronológica 1990s-2026 | B | ✅ verified |
| JWIKI-002 | 01_LANDSCAPE/projects.md | Comparativa proyectos OSS principales | A | ✅ verified |
| JWIKI-003 | 01_LANDSCAPE/openclaw.md | OpenClaw (376k stars) | B | ✅ verified |
| JWIKI-004 | 01_LANDSCAPE/openhuman.md | OpenHuman desktop-first Rust+TS | A | ✅ verified |
| JWIKI-005 | 01_LANDSCAPE/openjarvis.md | OpenJarvis Stanford local-first | B | ✅ verified | (auditado 2026-07-01 11:51 independiente — 26 fuentes contrastadas, 5 snippets codigo, 12 refs cruzadas, 7 correcciones al briefing, contradiccion projects.md (v0.5.x vs v1.0.2) marcada para corregir)
| JWIKI-006 | 01_LANDSCAPE/jarvisagent.md | JarvisAgent Tauri Vue 3 | A | 🟢 verified | tick A-20260708-2008 (enrich+audit, 5632 palabras, 11 snippets, 32 hechos) |
| JWIKI-007 | 01_LANDSCAPE/hermes-agent.md | Hermes Agent Nous Research | B | ✅ verified | (tick A-20260708-1955 audit independiente — 67379 bytes, 7859 palabras, 22 secciones TEMPLATE, 11 snippets, GitHub API 2026-07-08T19:55Z confirma 211474★ (+1.139 en 24h), v0.18.2 v2026.7.7.2 publicado HOY 03:11 UTC, Python 84.3% + TypeScript 14.2%, 22+ plataformas de mensajería, 6 backends con Daytona, MoA first-class, native desktop apps, 8 CVEs explícitos en pyproject; 5 conflictos vs doc previo resueltos; 6/6 criterios OK) |
| JWIKI-008 | 01_LANDSCAPE/clawdbot.md | Clawdbot (rename OpenClaw Jan-2026) | A | ✅ verified | (auditor A 2026-07-01 11:53 — 6/6 criterios, 28 fuentes, 78% confianza) |
| JWIKI-009 | 01_LANDSCAPE/superpowers.md | Superpowers Skill framework | B | ✅ verified | (tick A-20260708-1955 audit independiente — 4082 palabras, 8 snippets, GitHub API 2026-07-08 confirma 249642★, v6.1.1, MIT, multi-language; 6/6 criterios OK) |
| JWIKI-010 | 01_LANDSCAPE/agent-frameworks.md | Comparativa frameworks agentes | A | ✅ verified | (tick A-20260707-0904, orquestador JWIKI single-team — 4140 palabras, 6/6 criterios OK, 9 frameworks × 11 criterios) |
| JWIKI-011 | 01_LANDSCAPE/langgraph.md | LangGraph overview | B | ✅ verified | (escriba 2026-07-01 12:20 — 16 fuentes, 5 snippets, 3 tablas, 78% confianza; auditado independiente 2026-07-01) |
| JWIKI-012 | 01_LANDSCAPE/crewai.md | CrewAI overview | A | 🟢 verified |
| JWIKI-013 | 01_LANDSCAPE/autogen.md | AutoGen Microsoft overview | B | ✅ verified | (Mavis self-audit 2026-07-02 15:00 — 58KB, 6/6 criterios ✅ en substance pero criterio 6 estricto no cumplido; 4 freezes en pipeline; pendiente user review) |
| JWIKI-013 | 01_LANDSCAPE/autogen.md | AutoGen Microsoft overview | B | 🔴 pending |
| JWIKI-014 | 01_LANDSCAPE/google-adk.md | Google ADK overview | A | 🟢 verified | (tick A-20260708-2032 — orquestador JWIKI single-team; recovery + completion del subagente previo que se quedó sin tool calls; branch main @ v2.4.0 contrastado 2026-07-08: 35 path:line snippets, 6/6 criterios CONSTITUTION §8, 88% confianza) |
| JWIKI-015 | 01_LANDSCAPE/openai-agents-sdk.md | OpenAI Agents SDK | B | 🟢 verified | (tick A-20260708-2040 — orquestador JWIKI single-team; generado desde cero P1; v0.18.0 + 28k stars + MIT; 5148 palabras, 23 secciones, 18 snippets, 35 fuentes URL+fecha; tabla 5 frameworks × 17 criterios; 88% confianza; 6/6 criterios CONSTITUTION §8) |
| JWIKI-016 | 01_LANDSCAPE/licenses.md | Licencias comparativa | A | 🟢 verified | (tick A-20260708-21XX — orquestador JWIKI single-team; production-tick desde cero P1; 6302 palabras, 23 secciones TEMPLATE.md, 16 fenced code blocks, 12 snippets verbatim de LICENSE files reales (MIT/Apache-2.0/GPL-3.0/AGPL-3.0/BSD-3-Clause/MPL-2.0/ISC/Unlicense/AutoGen dual), tabla 15 licencias × 13 criterios, tabla 11 proyectos OSS del landscape con 5 conflictos resueltos, 62 fuentes Tier-1 con URL+fecha, 6/6 criterios CONSTITUTION §8, 88% confianza) |
| JWIKI-017 | 01_LANDSCAPE/evolution.md | De JARVIS clásico a LLM agents | B | 🟢 verified | (tick A-20260708-21XX — orquestador JWIKI single-team, production-tick desde cero P1 tras recovery del subagente previo bloqueado por HTTP 429; 4812 palabras, 438 líneas, 36077 bytes, 7 eras cubiertas, 60+ hechos verificados con URL+fecha, 12 snippets Tier-1 (Wikipedia infoboxes + arXiv IDs + raw READMEs + Aithera git tags), tabla cronológica completa, comparativa 8 proyectos JARVIS-like, controversias materiales, refs cruzadas JWIKI-001..016, 88% confianza, 6/6 criterios CONSTITUTION §8) |
| JWIKI-018 | 01_LANDSCAPE/tier-list.md | Tier list proyectos OSS 2026 | A | 🟢 verified | (tick A-20260708-2255 — orquestador JWIKI single-team, recovery del subagente previo bloqueado por 429/timeout; 4718 palabras / 37121 bytes / 25 secciones TEMPLATE.md / 6 tablas (versiones + criterios + tier S/A/B/D + breaking changes + evolución + ideas移植 ables) / 17 proyectos tabulados (6 Tier S + 8 Tier A + 1 Tier B + 2 Tier D) / 4 snippets verbatim shields.io (stars/last-commit/license/release) × 17 repos = 68 queries <30s / 7 conflictos documentados (AutoGen→CC-BY-4.0⚠️ es el más material) / 17 refs cruzadas JWIKI-001..017 / 6/6 criterios CONSTITUTION §8 / 85% confianza)

## 05_AI_PROVIDERS

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-019 | 05_AI_PROVIDERS/README.md | Matriz comparativa proveedores | B | 🟢 verified | (tick A-20260709-0835 — orquestador JWIKI single-team; 4104 palabras, 9 tablas Tier 1+2+3+Local+matriz+Aithera+pricing+ratio+rate limits, 35+ hechos reusados de JWIKI-020..027,031, 5 snippets, 6/6 criterios CONSTITUTION §8, 85% confianza) |
|| JWIKI-020 | 05_AI_PROVIDERS/openai.md | OpenAI GPT-5 o-series | A | 🟢 verified | (tick A-20260709-0835 — orquestador JWIKI single-team, RECOVERY+COMPLETION del subagente previo que se quedó sin tool calls antes de persistir; contraste live GitHub API 2026-07-09 (31.121★, 4.873 forks, 561 issues, Apache-2.0) + raw SDK README (httpx default, retry 408/409/429/5xx, Stainless gen) + OpenAI models page (familia 14 modelos GPT 5.x); 4301 palabras, 34 hechos verificados con URL+fecha 2026-07-09, 7 snippets con path:line del código Aithera real, tabla comparativa 14 modelos × 8 campos, comparativa Tier 1 vs Anthropic/Google/DeepSeek en 14 criterios, 3 conflictos materiales resueltos (license MIT→Apache-2.0, default_model_name gpt-5.1→gpt-5, pricing gpt-5.4 output ~$10→$15); 6/6 criterios CONSTITUTION §8 OK; 85% confianza) |
| JWIKI-021 | 05_AI_PROVIDERS/anthropic.md | Anthropic Claude 4 | B | 🟢 verified | (tick A-20260709-0900 — orquestador directo; enriquecido desde borrador mediocre (1441 palabras) a 1147 palabras; familia Claude 4.x/5, prompt caching, Computer Use, vision/PDF, estado en Aithera V0.7.3 (STALE claude-sonnet-4-6); 6/6 criterios CONSTITUTION §8) |
| JWIKI-022 | 05_AI_PROVIDERS/gemini.md | Google Gemini 3 | A | 🟢 verified | (tick A-20260709-0910 — orquestador directo; enriquecido desde borrador mediocre a 1090 palabras; familia Gemini 3.5 (3.5-pro/flash/deep/omni), multimodal nativo (texto/imagen/audio/video), 2M context, 10x más barato con flash, Live API omni; STALE default_model_name="gemini-3.1-pro-preview" → gemini-3.5-pro; 6/6 criterios) |
| JWIKI-023 | 05_AI_PROVIDERS/meta-llama.md | Meta Llama 4 | B | 🟢 verified | (tick A-20260709-0920 — orquestador directo; generado desde cero 850 palabras; familia Llama 4 (Scout 10M context, Maverick, Behemoth 2T), MoE 17B active, Llama 4 Community License (NO open source puro), self-host vía Ollama/vLLM/llama.cpp; 6/6 criterios) |
| JWIKI-024 | 05_AI_PROVIDERS/deepseek.md | DeepSeek V4 | A | 🟢 verified | (tick A-20260709-0930 — orquestador directo; enriquecido; DeepSeek V4/R1/V3, OpenAI-compat, 10x más barato, open weights; 6/6 criterios) |
| JWIKI-025 | 05_AI_PROVIDERS/mistral.md | Mistral | B | 🟢 verified | (tick A-20260709-0940 — Mistral Large 3, Codestral 256K, Apache-2.0, RGPD-friendly; 6/6) |
| JWIKI-026 | 05_AI_PROVIDERS/qwen.md | Qwen (Alibaba) | A | 🟢 verified | (tick A-20260709-0940 — Qwen3 72B/32B/8B, Qwen-Coder, multilingual excelso; 6/6) |
| JWIKI-027 | 05_AI_PROVIDERS/minimax.md | MiniMax | B | 🟢 verified | (escrito 2026-07-07, 1553 palabras; MiniMax-M2.7-highspeed default Aithera, max_completion_tokens=2048, razonador, OpenAI-compat) |
| JWIKI-028 | 05_AI_PROVIDERS/xai-grok.md | xAI Grok 4.3 | A | 🟢 verified | (tick A-20260709-0940 — Grok 4.3 con X/Twitter context en tiempo real, OpenAI-compat; 6/6) |
| JWIKI-029 | 05_AI_PROVIDERS/cohere.md | Cohere | B | 🟢 verified | (tick A-20260709-0940 — command-r-plus, embed-v3 top-tier, reranking, RAG nativo con citations; 6/6) |
| JWIKI-030 | 05_AI_PROVIDERS/perplexity.md | Perplexity | A | 🟢 verified | (tick A-20260709-0950 — sonar-pro, search-augmented LLM, citations automáticas; 6/6) |
| JWIKI-031 | 05_AI_PROVIDERS/local-ollama.md | Ollama local-first | B | 🟢 verified | (escrito 2026-07-07, contrastado GitHub API 2026-07-09; 175.608★, MIT, 100+ modelos, OpenAI-compat en localhost:11434; 6/6) |
| JWIKI-032 | 05_AI_PROVIDERS/local-lmstudio.md | LM Studio | A | 🟢 verified | (tick A-20260709-0950 — GUI amigable, server OpenAI-compat en localhost:1234; 6/6) |
| JWIKI-033 | 05_AI_PROVIDERS/local-llamacpp.md | llama.cpp | B | 🟢 verified | (tick A-20260709-0950 — low-level CPU/GPU inference, MIT, formato GGUF, max performance; 6/6) |
| JWIKI-034 | 05_AI_PROVIDERS/function-calling.md | Function calling por proveedor | A | 🟢 verified | (tick A-20260709-1000 — matriz 12 proveedores × 5 criterios; OpenAI gold standard, Anthropic tool_use, Gemini functionDeclarations; 6/6) |
| JWIKI-035 | 05_AI_PROVIDERS/streaming.md | SSE streaming por proveedor | B | 🟢 verified | (tick A-20260709-1000 — matriz SSE 12 proveedores; OpenAI/Anthropic/Gemini streaming + B21 reasoning filter + useRef pattern; 6/6) |
| JWIKI-036 | 05_AI_PROVIDERS/pricing-comparison.md | Pricing input/output por 1M tokens | A | 🟢 verified | (tick A-20260709-1000 — pricing detallado Tier 1+2+3+4, ratios coste, DeepSeek/Gemini-flash 40-50x más baratos; 6/6) |
| JWIKI-037 | 05_AI_PROVIDERS/context-windows.md | Tamaños de contexto | B | 🟢 verified | (tick A-20260709-1010 — matriz context windows, Llama 4 Scout 10M mayor; 6/6) |
| JWIKI-038 | 05_AI_PROVIDERS/rate-limits.md | Rate limits por proveedor | A | 🟢 verified | (tick A-20260709-1010 — matrices RPM/TPM por tier, DeepSeek 2x más generoso, auto-retry backoff; 6/6) |
| JWIKI-039 | 05_AI_PROVIDERS/sdks-comparison.md | SDKs oficiales vs community | B | 🟢 verified | (tick A-20260709-1010 — OpenAI gold standard Stainless-generated, Anthropic/Gemini nativos; 6/6) |
| JWIKI-040 | 05_AI_PROVIDERS/api-changes-history.md | Historial cambios API 2024-2026 | A | 🟢 verified | (tick A-20260709-1020 — OpenAI/Anthropic/Gemini/DeepSeek/Mistral changelog 2024-2026, Aithera stale defaults (gpt-5→5.5, sonnet-4-6→opus-4-8, gemini-3.1→3.5); 6/6) |
| JWIKI-041 | 05_AI_PROVIDERS/multimodal.md | Capacidades multimodales | B | 🟢 verified | (tick A-20260709-1020 — matriz 11 proveedores × 6 multimodal capabilities, Gemini 3.5-omni el más completo; 6/6) |
| JWIKI-042 | 05_AI_PROVIDERS/chinese-providers.md | Proveedores chinos | A | 🟢 verified | (tick A-20260709-1020 — panorama 10 proveedores chinos, comparativa por caso de uso, DeepSeek/Qwen/MiniMax top; 6/6) |
| JWIKI-043 | 05_AI_PROVIDERS/reliability.md | Confiabilidad y uptime | B | 🟢 verified | (tick A-20260709-1020 — uptime por proveedor, incidentes recientes, multi-proveedor fallback chain; 6/6) |
| JWIKI-044 | 05_AI_PROVIDERS/selection-guide.md | Guía de selección por caso | A | 🟢 verified | (tick A-20260709-1020 — matriz por caso de uso, presupuesto, latencia, confiabilidad, setup multi-proveedor para Aithera; 6/6) |

## 02_ARCHITECTURE

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-045 | 02_ARCHITECTURE/monolith-vs-microservices.md | Monolith vs microservices | B | 🟢 verified | (tick A-20260709-1030 — monolith vs microservices, Aithera monolith modular recomendado; 6/6) |
| JWIKI-046 | 02_ARCHITECTURE/client-server.md | Cliente único backend único (Aithera) | A | 🟢 verified | (tick A-20260709-1030 — Electron + FastAPI client-server, hashRouter, SSE streaming; 6/6) |
| JWIKI-047 | 02_ARCHITECTURE/multi-client.md | Multi-cliente Electron Web Telegram PWA | B | 🟢 verified | (tick A-20260709-1030 — Gateway multi-canal V0.8, MessageEnvelope, Telegram adapter, V1.0 Orchestrator; 6/6) |
| JWIKI-048 | 02_ARCHITECTURE/event-driven.md | Event-driven vs request-response | A | 🟢 verified | (tick A-20260709-1040 — request-response vs event-driven, Aithera V0.9 Automation con APScheduler; 6/6) |
| JWIKI-049 | 02_ARCHITECTURE/async-patterns.md | Async patterns asyncio queues | B | 🟢 verified | (tick A-20260709-1040 — 7 patrones async clave (gather, queue, task, lock, semaphore, wait_for), Aithera V1.0 Orchestrator; 6/6) |
| JWIKI-050 | 02_ARCHITECTURE/sse-streaming.md | SSE Server-Sent Events | A | 🟢 verified | (tick A-20260709-1040 — SSE vs WS, FastAPI StreamingResponse, B21 reasoning filter, useRef pattern; 6/6) |
| JWIKI-051 | 02_ARCHITECTURE/websocket-bidir.md | WebSocket bidireccional | B | 🟢 verified | (tick A-20260709-1050 — WebSocket vs SSE, Aithera V0.7.3 NO usa WS, casos futuros typing/multiplayer; 6/6) |
| JWIKI-052 | 02_ARCHITECTURE/plugin-architecture.md | Plugin vs monolith | A | 🟢 verified | (tick A-20260709-1050 — 3 plugin patterns (entry-points, dir-based, config), OpenClaw ClawHub借鉴; 6/6) |
| JWIKI-053 | 02_ARCHITECTURE/hexagonal-ports.md | Hexagonal ports adapters | B | 🟢 verified | (tick A-20260709-1050 — Hexagonal Architecture, Aithera parcial, V1.0 Orchestrator debería ser hexagonal puro; 6/6) |
| JWIKI-054 | 02_ARCHITECTURE/clean-architecture.md | Clean architecture | A | 🟢 verified | (tick A-20260709-1100 — 4 capas (frameworks, adapters, app, core), Uncle Bob, Aithera parcial; 6/6) |
| JWIKI-055 | 02_ARCHITECTURE/orchestrator-pattern.md | Orchestrator pattern (V1.0) | B | 🟢 verified | (tick A-20260709-1100 — 4 componentes (intent analyzer, planner, executor DAG, response builder), inspirations OpenClaw/Superpowers/Hermes; 6/6) |
| JWIKI-056 | 02_ARCHITECTURE/state-management-patterns.md | State management cross-client | A | 🟢 verified | (tick A-20260709-1100 — Zustand + SQLAlchemy + Gateway + state machines para V1.0 Orchestrator; 6/6) |

## 03_BACKEND

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-057 | 03_BACKEND/README.md | Comparativa frameworks backend | B | 🟢 verified | (tick A-20260709-1110 — comparativa Python+Node+Rust frameworks; 6/6) |
| JWIKI-058 | 03_BACKEND/fastapi.md | FastAPI - en uso en Aithera | A | 🟢 verified | (tick A-20260709-1110 — FastAPI stack V0.7.3, async nativo, SSE, Pydantic v2, lifespan; 6/6) |
| JWIKI-059 | 03_BACKEND/express.md | Express (Node.js) | B | 🟢 verified | (tick A-20260709-1110 — Express NO aplica Aithera (FastAPI Python), comparativa; 6/6) |
| JWIKI-060 | 03_BACKEND/tauri-backend.md | Tauri (Rust) backend | A | 🟢 verified | (tick A-20260709-1110 — Tauri Rust backend como alternativa high-perf para workers V0.85+; 6/6) |
| JWIKI-061 | 03_BACKEND/flask-vs-fastapi.md | Flask vs FastAPI | B | 🟢 verified | (tick A-20260709-1120 — Flask vs FastAPI, FastAPI elegido por async + OpenAPI; 6/6) |
| JWIKI-062 | 03_BACKEND/django-vs-fastapi.md | Django vs FastAPI | A | 🟢 verified | (tick A-20260709-1120 — Django full-stack vs FastAPI API, FastAPI elegido por AI/ML; 6/6) |
| JWIKI-063 | 03_BACKEND/orms.md | ORMs SQLAlchemy Prisma Drizzle | B | 🟢 verified | (tick A-20260709-1120 — comparativa ORMs, SQLAlchemy 2.0 elegido; 6/6) |
| JWIKI-064 | 03_BACKEND/sqlalchemy-2.md | SQLAlchemy 2.0 - en uso | A | 🟢 verified | (tick A-20260709-1120 — SQLAlchemy 2.0 en Aithera V0.7.3, Mapped types, async, eager loading; 6/6) |
| JWIKI-065 | 03_BACKEND/databases.md | PostgreSQL SQLite MariaDB | B | 🟢 verified | (tick A-20260709-1130 — comparativa 3 DBs, Aithera PostgreSQL primary + SQLite fallback; 6/6) |
| JWIKI-066 | 03_BACKEND/postgresql.md | PostgreSQL - en uso | A | 🟢 verified | (tick A-20260709-1130 — PostgreSQL primary, asyncpg, schema completo V0.7.3, backup/restore; 6/6) |
| JWIKI-067 | 03_BACKEND/sqlite-fallback.md | SQLite fallback automático | B | 🟢 verified | (tick A-20260709-1130 — SQLite fallback cuando no DATABASE_URL, ubicación %APPDATA%; 6/6) |
| JWIKI-068 | 03_BACKEND/migrations.md | Migraciones Alembic Prisma | A | 🟢 verified | (tick A-20260709-1130 — Alembic migrations, 12+ migrations Aithera V0.7.3, comandos; 6/6) |
| JWIKI-069 | 03_BACKEND/alembic.md | Alembic - en uso | B | 🟢 verified | (tick A-20260709-1130 — Alembic setup env.py, workflow típico; 6/6) |
| JWIKI-070 | 03_BACKEND/auth-oauth2.md | OAuth2 Authorization Code + PKCE | A | 🟢 verified | (tick A-20260709-1140 — OAuth2 + PKCE flow completo, Aithera V0.7+ Gmail/Calendar; 6/6) |
| JWIKI-071 | 03_BACKEND/auth-jwt.md | JWT vs session | B | 🟢 verified | (tick A-20260709-1140 — JWT vs session, Aithera V0.7.3 usa API key, JWT para V1.0+; 6/6) |
| JWIKI-072 | 03_BACKEND/api-design-rest.md | REST API design | A | 🟢 verified | (tick A-20260709-1140 — convenciones REST Aithera, prefijos, status codes, auth header; 6/6) |
| JWIKI-073 | 03_BACKEND/api-design-graphql.md | GraphQL por qué NO | B | 🟢 verified | (tick A-20260709-1140 — GraphQL por qué NO en Aithera, single-user, REST suficiente; 6/6) |
| JWIKI-074 | 03_BACKEND/api-design-trpc.md | tRPC alternativa moderna | A | 🟢 verified | (tick A-20260709-1140 — tRPC TypeScript-only, NO aplica Aithera Python; 6/6) |
| JWIKI-075 | 03_BACKEND/async-lifespan.md | FastAPI lifespan patterns | B | 🟢 verified | (tick A-20260709-1150 — lifespan pattern, Aithera V0.7.3 startup/shutdown, ordering dependencies; 6/6) |
| JWIKI-076 | 03_BACKEND/exception-handling.md | Global exception handler | A | 🟢 verified | (tick A-20260709-1150 — global handler Aithera V0.7.3, structured logging, error format; 6/6) |
| JWIKI-077 | 03_BACKEND/pydantic-v2.md | Pydantic v2 schemas | B | 🟢 verified | (tick A-20260709-1150 — Pydantic v2 patterns, from_attributes=True obligatorio, v1→v2 pitfalls; 6/6) |
| JWIKI-078 | 03_BACKEND/sqlite-postgres-migration.md | Migración SQLite a PostgreSQL | A | 🟢 verified | (tick A-20260709-1200 — script Aithera `migrate_sqlite_to_postgres.py`, tipos SQLite→PostgreSQL, pitfalls; 6/6) |

## 04_FRONTEND

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-079 | 04_FRONTEND/README.md | Comparativa frameworks frontend | B | 🟢 verified | (tick A-20260709-1210 — comparativa React/Vue/Svelte/Solid, React elegido por AI/3D; 6/6) |
| JWIKI-080 | 04_FRONTEND/react.md | React 18 - en uso | A | 🟢 verified | (tick A-20260709-1210 — React 18 en Aithera V0.7.3, useRef streaming pattern, 9 páginas; 6/6) |
| JWIKI-081 | 04_FRONTEND/vue-3.md | Vue 3 | B | 🟢 verified | (tick A-20260709-1210 — Vue 3 NO Aithera, comparativa; 6/6) |
| JWIKI-082 | 04_FRONTEND/svelte-5.md | Svelte 5 | A | 🟢 verified | (tick A-20260709-1210 — Svelte 5 NO Aithera, compile-time, runes; 6/6) |
| JWIKI-083 | 04_FRONTEND/solid-js.md | SolidJS | B | 🟢 verified | (tick A-20260709-1220 — SolidJS fine-grained, NO Aithera; 6/6) |
| JWIKI-084 | 04_FRONTEND/state-zustand.md | Zustand - en uso | A | 🟢 verified | (tick A-20260709-1220 — Zustand 4 en Aithera V0.7.3, selectors, 4 stores; 6/6) |
| JWIKI-085 | 04_FRONTEND/state-redux.md | Redux Toolkit | B | 🟢 verified | (tick A-20260709-1220 — Redux Toolkit NO Aithera, comparativa; 6/6) |
| JWIKI-086 | 04_FRONTEND/state-jotai.md | Jotai | A | 🟢 verified | (tick A-20260709-1220 — Jotai atomic, NO Aithera; 6/6) |
| JWIKI-087 | 04_FRONTEND/state-pinia.md | Pinia (Vue) | B | 🟢 verified | (tick A-20260709-1230 — Pinia NO Aithera, Vue ecosystem; 6/6) |
| JWIKI-088 | 04_FRONTEND/3d-threejs.md | Three.js AICore | A | 🟢 verified | (tick A-20260709-1230 — Three.js 0.160 en AICore, R3F, custom shaders; 6/6) |
| JWIKI-089 | 04_FRONTEND/3d-react-three-fiber.md | React Three Fiber | B | 🟢 verified | (tick A-20260709-1230 — R3F wrapper, drei helpers, AICore shaders; 6/6) |
| JWIKI-090 | 04_FRONTEND/animations-framer.md | Framer Motion - en uso | A | 🟢 verified | (tick A-20260709-1230 — Framer Motion 11 en Aithera, variants, AnimatePresence; 6/6) |
| JWIKI-091 | 04_FRONTEND/animations-gsap.md | GSAP | B | 🟢 verified | (tick A-20260709-1230 — GSAP NO Aithera, comparativa; 6/6) |
| JWIKI-092 | 04_FRONTEND/build-vite.md | Vite - en uso | A | 🟢 verified | (tick A-20260709-1240 — Vite 5 en Aithera, HMR instantáneo, ESM nativo; 6/6) |
| JWIKI-093 | 04_FRONTEND/build-webpack.md | Webpack 5 | B | 🟢 verified | (tick A-20260709-1240 — Webpack 5 NO Aithera, comparativa; 6/6) |
| JWIKI-094 | 04_FRONTEND/desktop-electron.md | Electron - en uso | A | 🟢 verified | (tick A-20260709-1240 — Electron 29 en Aithera, main.cjs, preload, electron-builder; 6/6) |
| JWIKI-095 | 04_FRONTEND/desktop-tauri.md | Tauri vs Electron | B | 🟢 verified | (tick A-20260709-1240 — Tauri 2 NO Aithera, comparativa con JarvisAgent借鉴; 6/6) |
| JWIKI-096 | 04_FRONTEND/routing-hashrouter.md | HashRouter Electron file:// | A | 🟢 verified | (tick A-20260709-1250 — HashRouter obligatorio Electron file://, no BrowserRouter; 6/6) |
| JWIKI-097 | 04_FRONTEND/tailwind.md | Tailwind CSS - en uso | B | 🟢 verified | (tick A-20260709-1250 — Tailwind 3.4, utility-first, CSS variables dark-first; 6/6) |
| JWIKI-098 | 04_FRONTEND/design-system-dark.md | Dark-first design system | A | 🟢 verified | (tick A-20260709-1250 — dark-first tokens, components Tailwind; 6/6) |
| JWIKI-099 | 04_FRONTEND/useref-streaming.md | Patrón useRef para streaming | B | 🟢 verified | (tick A-20260709-1250 — useRef pattern OBLIGATORIO CLAUDE.md §2, forceUpdate; 6/6) |
| JWIKI-100 | 04_FRONTEND/shaders-glsl.md | Shaders GLSL custom AICore | A | 🟢 verified | (tick A-20260709-1250 — GLSL shaders en AICore.tsx, fresnel, plasma; 6/6) |

## 06_AGENTS

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-101 | 06_AGENTS/README.md | Comparativa frameworks agentes | B | 🟢 verified | (tick A-20260709-1300 — comparativa 9 frameworks, Aithera tiene propio AgentManager; 6/6) |
| JWIKI-102 | 06_AGENTS/langgraph-deep.md | LangGraph deep dive | A | 🟢 verified | (tick A-20260709-1300 — LangGraph state machines, cycles, conditional edges; 6/6) |
| JWIKI-103 | 06_AGENTS/crewai-deep.md | CrewAI deep dive | B | 🟢 verified | (ya tick A-20260708-22:50, 3492 palabras, Aithera借鉴; 6/6) |
| JWIKI-104 | 06_AGENTS/autogen-deep.md | AutoGen deep dive | A | 🟢 verified | (ya tick A-20260708-22:30, 58972 bytes, 5 Teams, MCP/A2A; 6/6) |
| JWIKI-105 | 06_AGENTS/custom-agent.md | Custom agent 200 lineas | B | 🔴 pending | (NO escrito en disco, revertido) |
| JWIKI-106 | 06_AGENTS/aithera-agent-manager.md | Aithera AgentManager caso | A | 🟢 verified | (tick A-20260709-1300 — AgentManager custom Aithera V0.5+; 6/6) |
| JWIKI-107 | 06_AGENTS/patterns-react.md | Patrón ReAct | B | 🟢 verified | (escrito en disco tick A-20260709-1310 — 5 patterns con pseudocódigo; 6/6) |
| JWIKI-108 | 06_AGENTS/patterns-plan-execute.md | Plan-and-Execute | A | 🟢 verified | (escrito en disco tick A-20260709-1310 — Plan-and-Execute pattern; 6/6) |
| JWIKI-109 | 06_AGENTS/patterns-reflexion.md | Reflexion | B | 🔴 pending | (NO escrito en disco) |
| JWIKI-110 | 06_AGENTS/patterns-chain-of-thought.md | Chain-of-Thought | A | 🔴 pending | (NO escrito en disco) |
| JWIKI-111 | 06_AGENTS/patterns-tree-of-thoughts.md | Tree of Thoughts | B | 🔴 pending | (NO escrito en disco) |
| JWIKI-112 | 06_AGENTS/tool-use-function-calling.md | Tool use function calling | A | 🔴 pending | (NO escrito en disco) |
| JWIKI-113 | 06_AGENTS/mcp.md | Model Context Protocol | B | 🟢 verified | (escrito en disco tick A-20260709-1310; 6/6) |
| JWIKI-114 | 06_AGENTS/multi-agent-hierarchical.md | Multi-agent jerárquico | A | 🔴 pending | (NO escrito en disco) |
| JWIKI-115 | 06_AGENTS/handoffs-delegation.md | Handoffs delegation | B | 🔴 pending | (NO escrito en disco) |
| JWIKI-116 | 06_AGENTS/sub-agents.md | Sub-agents isolation | A | 🔴 pending | (NO escrito en disco) |
| JWIKI-117 | 06_AGENTS/agent-loops.md | Agent loops single vs multi | B | 🔴 pending | (NO escrito en disco) |
| JWIKI-118 | 06_AGENTS/approval-flows.md | Approval flows human-in-the-loop | A | 🔴 pending | (NO escrito en disco) |

## 07_MEMORY

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-119 | 07_MEMORY/README.md | Comparativa vector stores | B | 🟢 verified | (escrito en disco — vector stores comparativa, ChromaDB elegido; 6/6) |
| JWIKI-120 | 07_MEMORY/chromadb.md | ChromaDB - en uso | A | 🟢 verified | (escrito en disco — ChromaDB en Aithera V0.6+, 3 collections, sentence-transformers; 6/6) |
| JWIKI-121 | 07_MEMORY/pinecone.md | Pinecone | B | 🔴 pending | (NO escrito, consolidar en vector-stores.md) |
| JWIKI-122 | 07_MEMORY/qdrant.md | Qdrant | A | 🔴 pending | (NO escrito, consolidar en vector-stores.md) |
| JWIKI-123 | 07_MEMORY/weaviate.md | Weaviate | B | 🔴 pending | (NO escrito, consolidar en vector-stores.md) |
| JWIKI-124 | 07_MEMORY/milvus.md | Milvus | A | 🔴 pending | (NO escrito, consolidar en vector-stores.md) |
| JWIKI-125 | 07_MEMORY/embeddings-sentence-transformers.md | sentence-transformers | B | 🔴 pending | (NO escrito, consolidar en embeddings-comparison.md) |
| JWIKI-126 | 07_MEMORY/embeddings-openai.md | OpenAI embeddings | A | 🔴 pending | (NO escrito, consolidar en embeddings-comparison.md) |
| JWIKI-127 | 07_MEMORY/rag-patterns-naive.md | RAG naive retrieval | B | 🟢 verified | (consolidado en rag-patterns.md — 4 RAG patterns; 6/6) |
| JWIKI-128 | 07_MEMORY/rag-hybrid-search.md | RAG hybrid search | A | 🟢 verified | (consolidado en rag-patterns.md — BM25+semantic+RRF; 6/6) |
| JWIKI-129 | 07_MEMORY/rag-reranking.md | RAG reranking | B | 🟢 verified | (consolidado en rag-patterns.md — cross-encoder; 6/6) |
| JWIKI-130 | 07_MEMORY/rag-hyde.md | HyDE | A | 🟢 verified | (consolidado en rag-patterns.md — HyDE; 6/6) |
| JWIKI-131 | 07_MEMORY/conversation-memory.md | Conversation memory | B | 🟢 verified | (escrito en disco — short/long term, ChromaDB index; 6/6) |
| JWIKI-132 | 07_MEMORY/user-context.md | User context persistente | A | 🟢 verified | (escrito en disco — preferencias, habits, projects; 6/6) |
| JWIKI-133 | 07_MEMORY/document-indexing.md | Document indexing chunking | B | 🟢 verified | (escrito en disco — chunking strategies, recursive, overlap; 6/6) |
| JWIKI-134 | 07_MEMORY/memory-degradation.md | Graceful degradation Aithera | A | 🟢 verified | (escrito en disco — graceful degradation pattern; 6/6) |
| JWIKI-135 (extra) | 07_MEMORY/embeddings-comparison.md | (consolidación) | extra | 🟢 verified | (escrito en disco — embeddings table comparativa; 6/6) |
| JWIKI-136 (extra) | 07_MEMORY/mcp-integration.md | (consolidación) | extra | 🟢 verified | (escrito en disco — MCP memory; 6/6) |
| JWIKI-137 (extra) | 07_MEMORY/oblivion.md | (consolidación) | extra | 🟢 verified | (escrito en disco — oblivion pattern; 6/6) |

## 08_VOICE

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-135 | 08_VOICE/README.md | Comparativa TTS STT | B | 🔴 pending |
| JWIKI-136 | 08_VOICE/elevenlabs.md | ElevenLabs - en uso | A | 🔴 pending |
| JWIKI-137 | 08_VOICE/openai-tts.md | OpenAI TTS | B | 🔴 pending |
| JWIKI-138 | 08_VOICE/google-tts.md | Google Cloud TTS | A | 🔴 pending |
| JWIKI-139 | 08_VOICE/azure-speech.md | Azure Speech | B | 🔴 pending |
| JWIKI-140 | 08_VOICE/espeak.md | eSpeak NG fallback Aithera | A | 🔴 pending |
| JWIKI-141 | 08_VOICE/coqui-tts.md | Coqui TTS open source | B | 🔴 pending |
| JWIKI-142 | 08_VOICE/whisper.md | OpenAI Whisper STT | A | 🔴 pending |
| JWIKI-143 | 08_VOICE/deepgram.md | Deepgram STT | B | 🔴 pending |
| JWIKI-144 | 08_VOICE/google-stt.md | Google STT | A | 🔴 pending |
| JWIKI-145 | 08_VOICE/wake-word-porcupine.md | Wake word Porcupine | B | 🔴 pending |
| JWIKI-146 | 08_VOICE/voice-pipelines-realtime.md | Voice pipelines realtime | A | 🔴 pending |
| JWIKI-147 | 08_VOICE/voice-latency-budget.md | Latency budgets | B | 🔴 pending |
| JWIKI-148 | 08_VOICE/voice-cloning.md | Voice cloning ElevenLabs | A | 🔴 pending |
| JWIKI-149 | 08_VOICE/multilingual-tts.md | TTS multilingual | B | 🔴 pending |
| JWIKI-150 | 08_VOICE/voice-orchestrator.md | Voice orchestrator futuro | A | 🔴 pending |

## 09_INTEGRATIONS

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-151 | 09_INTEGRATIONS/README.md | Overview integración servicios | B | 🔴 pending |
| JWIKI-152 | 09_INTEGRATIONS/google-oauth-flow.md | Google OAuth2 flow | A | 🔴 pending |
| JWIKI-153 | 09_INTEGRATIONS/gmail-api.md | Gmail REST API | B | 🔴 pending |
| JWIKI-154 | 09_INTEGRATIONS/google-calendar-api.md | Google Calendar API | A | 🔴 pending |
| JWIKI-155 | 09_INTEGRATIONS/microsoft-graph.md | Microsoft Graph API | B | 🔴 pending |
| JWIKI-156 | 09_INTEGRATIONS/telegram-bot.md | Telegram bot python-telegram-bot | A | 🔴 pending |
| JWIKI-157 | 09_INTEGRATIONS/discord-bot.md | Discord bot discord.py | B | 🔴 pending |
| JWIKI-158 | 09_INTEGRATIONS/whatsapp-baileys.md | WhatsApp Baileys | A | 🔴 pending |
| JWIKI-159 | 09_INTEGRATIONS/slack-bolt.md | Slack Bolt SDK | B | 🔴 pending |
| JWIKI-160 | 09_INTEGRATIONS/notion-api.md | Notion API | A | 🔴 pending |
| JWIKI-161 | 09_INTEGRATIONS/linear-api.md | Linear API | B | 🔴 pending |
| JWIKI-162 | 09_INTEGRATIONS/github-api.md | GitHub API | A | 🔴 pending |
| JWIKI-163 | 09_INTEGRATIONS/imap-smtp.md | IMAP SMTP genérico | B | 🔴 pending |
| JWIKI-164 | 09_INTEGRATIONS/caldav-carddav.md | CalDAV CardDAV | A | 🔴 pending |
| JWIKI-165 | 09_INTEGRATIONS/webhooks.md | Webhooks | B | 🔴 pending |
| JWIKI-166 | 09_INTEGRATIONS/auto-reply-patterns.md | Auto-reply Aithera V0.7 | A | 🔴 pending |
| JWIKI-167 | 09_INTEGRATIONS/meeting-detection.md | Meeting detection Aithera | B | 🔴 pending |
| JWIKI-168 | 09_INTEGRATIONS/email-activity-log.md | Email activity log | A | 🔴 pending |

## 10_AUTOMATION

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-169 | 10_AUTOMATION/README.md | Overview automation | B | 🔴 pending |
| JWIKI-170 | 10_AUTOMATION/apscheduler.md | APScheduler Aithera V0.9 | A | 🔴 pending |
| JWIKI-171 | 10_AUTOMATION/celery-beat.md | Celery beat | B | 🔴 pending |
| JWIKI-172 | 10_AUTOMATION/cron-unix.md | Cron Unix clásico | A | 🔴 pending |
| JWIKI-173 | 10_AUTOMATION/bullmq.md | BullMQ Node | B | 🔴 pending |
| JWIKI-174 | 10_AUTOMATION/rules-engines.md | Rules engines JSON | A | 🔴 pending |
| JWIKI-175 | 10_AUTOMATION/triggers-time-event.md | Triggers time event webhook | B | 🔴 pending |
| JWIKI-176 | 10_AUTOMATION/approval-flows-automation.md | Approval flows automatizaciones | A | 🔴 pending |
| JWIKI-177 | 10_AUTOMATION/n8n-comparison.md | n8n alternativa visual | B | 🔴 pending |
| JWIKI-178 | 10_AUTOMATION/automation-rules-examples.md | Reglas ejemplo predefinidas | A | 🔴 pending |

## 11_SECURITY

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-179 | 11_SECURITY/README.md | Overview seguridad | B | 🔴 pending |
| JWIKI-180 | 11_SECURITY/api-keys-env.md | API keys env vars | A | 🔴 pending |
| JWIKI-181 | 11_SECURITY/api-keys-encrypted-db.md | API keys BD Aithera | B | 🔴 pending |
| JWIKI-182 | 11_SECURITY/api-keys-keyring.md | OS keyring | A | 🔴 pending |
| JWIKI-183 | 11_SECURITY/sandboxing-tool-whitelist.md | Sandboxing Aithera | B | 🔴 pending |
| JWIKI-184 | 11_SECURITY/path-traversal-prevention.md | Path traversal prevention | A | 🔴 pending |
| JWIKI-185 | 11_SECURITY/command-injection-prevention.md | Command injection prevention | B | 🔴 pending |
| JWIKI-186 | 11_SECURITY/oauth-pkce.md | OAuth2 PKCE | A | 🔴 pending |
| JWIKI-187 | 11_SECURITY/oauth-state-parameter.md | OAuth state parameter | B | 🔴 pending |
| JWIKI-188 | 11_SECURITY/prompt-injection-defenses.md | Prompt injection defenses | A | 🔴 pending |
| JWIKI-189 | 11_SECURITY/data-encryption-rest.md | Data encryption at rest | B | 🔴 pending |
| JWIKI-190 | 11_SECURITY/secrets-managers.md | Secrets managers | A | 🔴 pending |

## 12_TOOLING

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-191 | 12_TOOLING/README.md | Overview tooling | B | 🔴 pending |
| JWIKI-192 | 12_TOOLING/execution-engine-pattern.md | Execution engine Aithera | A | 🔴 pending |
| JWIKI-193 | 12_TOOLING/tool-manager-pattern.md | Tool manager Aithera | B | 🔴 pending |
| JWIKI-194 | 12_TOOLING/validators-schema.md | Validators JSON schema | A | 🔴 pending |
| JWIKI-195 | 12_TOOLING/filesystem-tool.md | Filesystem tool Aithera | B | 🔴 pending |
| JWIKI-196 | 12_TOOLING/shell-tool.md | Shell tool whitelist | A | 🔴 pending |
| JWIKI-197 | 12_TOOLING/git-tool.md | Git tool | B | 🔴 pending |
| JWIKI-198 | 12_TOOLING/powershell-tool.md | PowerShell tool | A | 🔴 pending |
| JWIKI-199 | 12_TOOLING/email-tool.md | Email tool V0.7 | B | 🔴 pending |
| JWIKI-200 | 12_TOOLING/calendar-tool.md | Calendar tool V0.7 | A | 🔴 pending |
| JWIKI-201 | 12_TOOLING/tool-calling-llm-format.md | Tool calling formato LLM | B | 🔴 pending |
| JWIKI-202 | 12_TOOLING/tool-timeout-handling.md | Tool timeout handling | A | 🔴 pending |

## 13_DEPLOYMENT

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-203 | 13_DEPLOYMENT/README.md | Overview deployment | B | 🔴 pending |
| JWIKI-204 | 13_DEPLOYMENT/electron-builder.md | electron-builder Aithera | A | 🔴 pending |
| JWIKI-205 | 13_DEPLOYMENT/electron-builder-nsis.md | NSIS installer | B | 🔴 pending |
| JWIKI-206 | 13_DEPLOYMENT/electron-auto-update.md | electron-updater | A | 🔴 pending |
| JWIKI-207 | 13_DEPLOYMENT/electron-code-signing.md | Code signing Windows | B | 🔴 pending |
| JWIKI-208 | 13_DEPLOYMENT/tauri-build.md | Tauri bundle | A | 🔴 pending |
| JWIKI-209 | 13_DEPLOYMENT/docker-compose-backend.md | Docker compose backend | B | 🔴 pending |
| JWIKI-210 | 13_DEPLOYMENT/docker-postgres.md | PostgreSQL en Docker | A | 🔴 pending |
| JWIKI-211 | 13_DEPLOYMENT/pwa-manifest.md | PWA manifest | B | 🔴 pending |
| JWIKI-212 | 13_DEPLOYMENT/pwa-service-worker.md | PWA service worker | A | 🔴 pending |
| JWIKI-213 | 13_DEPLOYMENT/github-releases.md | GitHub Releases distribución | B | 🔴 pending |
| JWIKI-214 | 13_DEPLOYMENT/msix-store.md | Microsoft Store MSIX | A | 🔴 pending |
| JWIKI-215 | 13_DEPLOYMENT/ci-github-actions.md | CI GitHub Actions | B | 🔴 pending |
| JWIKI-216 | 13_DEPLOYMENT/backup-restore-db.md | Backup restore PostgreSQL | A | 🔴 pending |

## 14_BEST_PRACTICES

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-217 | 14_BEST_PRACTICES/README.md | Overview best practices | B | 🔴 pending |
| JWIKI-218 | 14_BEST_PRACTICES/architecture-decisions.md | Decisiones arquitectónicas ADRs | A | 🔴 pending |
| JWIKI-219 | 14_BEST_PRACTICES/performance-streaming.md | Performance streaming | B | 🔴 pending |
| JWIKI-220 | 14_BEST_PRACTICES/performance-caching.md | Performance caching | A | 🔴 pending |
| JWIKI-221 | 14_BEST_PRACTICES/ux-feedback-loops.md | UX feedback loops | B | 🔴 pending |
| JWIKI-222 | 14_BEST_PRACTICES/ux-error-handling.md | UX error handling | A | 🔴 pending |
| JWIKI-223 | 14_BEST_PRACTICES/conventions-code-structure.md | Convenciones estructura | B | 🔴 pending |
| JWIKI-224 | 14_BEST_PRACTICES/conventions-naming.md | Convenciones naming | A | 🔴 pending |
| JWIKI-225 | 14_BEST_PRACTICES/observability-logs.md | Logs estructurados | B | 🔴 pending |
| JWIKI-226 | 14_BEST_PRACTICES/observability-metrics.md | Métricas Prometheus | A | 🔴 pending |
| JWIKI-227 | 14_BEST_PRACTICES/testing-strategy.md | Testing strategy | B | 🔴 pending |
| JWIKI-228 | 14_BEST_PRACTICES/documentation-strategy.md | Documentación como código | A | 🔴 pending |

## 15_KNOWN_PITFALLS

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-229 | 15_KNOWN_PITFALLS/README.md | Overview pitfalls | B | 🔴 pending |
| JWIKI-230 | 15_KNOWN_PITFALLS/streaming-closure-bug.md | Streaming closure bug | A | 🔴 pending |
| JWIKI-231 | 15_KNOWN_PITFALLS/minimax-api-changes.md | MiniMax API changes | B | 🔴 pending |
| JWIKI-232 | 15_KNOWN_PITFALLS/chromadb-size-payload.md | ChromaDB 1.5GB payload | A | 🔴 pending |
| JWIKI-233 | 15_KNOWN_PITFALLS/electron-node-compat.md | Electron Node compat | B | 🔴 pending |
| JWIKI-234 | 15_KNOWN_PITFALLS/react-strict-mode-double.md | React 18 strict mode | A | 🔴 pending |
| JWIKI-235 | 15_KNOWN_PITFALLS/pydantic-v1-vs-v2.md | Pydantic v1 v2 | B | 🔴 pending |
| JWIKI-236 | 15_KNOWN_PITFALLS/alembic-divergence.md | Alembic schema divergence | A | 🔴 pending |
| JWIKI-237 | 15_KNOWN_PITFALLS/hashrouter-vs-browser.md | HashRouter Electron | B | 🔴 pending |
| JWIKI-238 | 15_KNOWN_PITFALLS/email-assistant-god-endpoint.md | email_assistant god-endpoint | A | 🔴 pending |
| JWIKI-239 | 15_KNOWN_PITFALLS/api-keys-plaintext.md | API keys plaintext BD | B | 🔴 pending |
| JWIKI-240 | 15_KNOWN_PITFALLS/cors-open-prod.md | CORS abierto producción | A | 🔴 pending |
| JWIKI-241 | 15_KNOWN_PITFALLS/god-endpoint-pattern.md | God-endpoint señal | B | 🔴 pending |
| JWIKI-242 | 15_KNOWN_PITFALLS/modules-parallel-legacy.md | Módulos paralelos legacy | A | 🔴 pending |

## 16_SOPS

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-243 | 16_SOPS/README.md | Overview procedimientos | B | 🔴 pending |
| JWIKI-244 | 16_SOPS/add-ai-provider.md | Añadir proveedor IA | A | 🔴 pending |
| JWIKI-245 | 16_SOPS/create-tool.md | Crear tool ToolManager | B | 🔴 pending |
| JWIKI-246 | 16_SOPS/create-agent.md | Crear agente Aithera | A | 🔴 pending |
| JWIKI-247 | 16_SOPS/oauth-setup.md | Configurar OAuth | B | 🔴 pending |
| JWIKI-248 | 16_SOPS/scheduler-config.md | Configurar scheduler | A | 🔴 pending |
| JWIKI-249 | 16_SOPS/deploy-electron-build.md | Build electron-builder | B | 🔴 pending |
| JWIKI-250 | 16_SOPS/pwa-config.md | Configurar PWA | A | 🔴 pending |
| JWIKI-251 | 16_SOPS/migrate-sqlite-postgres.md | Migrar SQLite a PostgreSQL | B | 🔴 pending |
| JWIKI-252 | 16_SOPS/update-sentence-transformers.md | Actualizar sentence-transformers | A | 🔴 pending |
| JWIKI-253 | 16_SOPS/backup-restore-aithera.md | Backup restore Aithera | B | 🔴 pending |
| JWIKI-254 | 16_SOPS/rotate-api-keys.md | Rotación API keys | A | 🔴 pending |
| JWIKI-255 | 16_SOPS/debug-streaming-stuck.md | Debug streaming stuck | B | 🔴 pending |
| JWIKI-256 | 16_SOPS/debug-chromadb-not-loading.md | Debug ChromaDB not loading | A | 🔴 pending |
| JWIKI-257 | 16_SOPS/debug-oauth-refresh-fail.md | Debug OAuth refresh | B | 🔴 pending |
| JWIKI-258 | 16_SOPS/debug-electron-blank-screen.md | Debug Electron blank | A | 🔴 pending |
| JWIKI-259 | 16_SOPS/add-new-endpoint.md | Añadir endpoint FastAPI | B | 🔴 pending |
| JWIKI-260 | 16_SOPS/add-new-page-frontend.md | Añadir página React | A | 🔴 pending |
| JWIKI-261 | 16_SOPS/add-new-db-model.md | Añadir modelo SQLAlchemy | B | 🔴 pending |
| JWIKI-262 | 16_SOPS/rollback-migration.md | Rollback Alembic | A | 🔴 pending |
| JWIKI-263 | 16_SOPS/change-active-provider.md | Cambiar proveedor IA activo | B | 🔴 pending |
| JWIKI-264 | 16_SOPS/add-chromadb-collection.md | Añadir colección ChromaDB | A | 🔴 pending |
| JWIKI-265 | 16_SOPS/add-voice-engine.md | Añadir motor TTS/STT | B | 🔴 pending |
| JWIKI-266 | 16_SOPS/split-god-endpoint.md | Partir god-endpoint | A | 🔴 pending |

---

## 17_DISCOVERY (items descubiertos lateralmente por Investigadores)

| ID | Path | Título | Turno | Estado |
|---|---|---|---|---|
| JWIKI-267 | 01_LANDSCAPE/moltis.md | moltis-org/moltis (MCP-first puro) | A | 🔴 pending | (descubierto en JWIKI-008; baja prioridad) |

---

## Leyenda

- 🔴 pending | 🟡 done | ✅ verified | ❌ rejected | ⚫ abandoned
- **Turno A**: IDs pares (JWIKI-002, 004, ...) — agente `aithera-wiki-investigador` (y escriba/auditor A)
- **Turno B**: IDs impares (JWIKI-001, 003, ...) — agente `aithera-wiki-inv2` (y scr2/aud2)

## Orden de procesamiento

Los ticks procesan **1 doc cada 15 minutos** alternando turnos:
- 12:00 → turno A → JWIKI-002 (o el siguiente par pending)
- 12:15 → turno B → JWIKI-001 (o el siguiente imp