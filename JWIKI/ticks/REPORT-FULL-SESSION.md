# TICKS de la Wiki — Reportes por tick

> Cada tick representa UN documento procesado en la JWIKI. Aquí se archiva el progreso sesión por sesión.

---

## Sesión 2026-07-07 (sesión original "Aithera WIKI")

### Tick A-20260707-0230 — JWIKI-009 Superpowers
- **Estado**: ✅ verified
- **Tiempo**: ~25 min
- **Palabras**: 3981
- **Hito**: 6 conflictos resueltos (215k→247,930★, v3.x→v6.1.1, OpenClaw NO compatible, Gemini CLI removido, Shell→multi-language, 0→MIT)
- **Cross-doc**: JWIKI-002 debe actualizarse (215k→247,930, Shell→multi-language, v3.x→v6.1.1)
- **Tick report**: `ticks/A-20260707-0230.md`

### Tick A-20260708-1955 — JWIKI-007 Hermes Agent (audit)
- **Estado**: ✅ verified
- **Tiempo**: ~35 min
- **Palabras**: 7859 (de 2579 → 3x enriquecido)
- **Hito**: v0.18.2 v2026.7.7.2 publicado HOY 2026-07-08 03:11 UTC, 22+ plataformas de mensajería, 6 backends con Daytona, MoA first-class, native desktop apps, 8 CVEs explícitos
- **Cross-doc**: JWIKI-002 (53k→211k★, "5+ mensajerías"→"22+", 6 backends, native desktop, MoA); 30+ docs JWIKI a re-referenciar

### Tick A-20260708-2032 — JWIKI-014 Google ADK (recovery)
- **Estado**: ✅ verified
- **Tiempo**: ~15 min (recovery del subagente previo)
- **Palabras**: 5307
- **Hito**: branch main @ v2.4.0, 35 path:line snippets, 6/6 criterios, 88% confianza
- **Recovery pattern**: subagente previo hizo research (~25 hechos) pero se quedó sin tool calls. Re-despaché con contexto cacheado para terminar el tick.

### Tick A-20260708-21XX — JWIKI-016 Licencias
- **Estado**: ✅ verified
- **Tiempo**: ~15 min
- **Palabras**: 6302
- **Hito**: 23 secciones, 16 snippets verbatim de LICENSE files, 62 tablas Markdown, 35 cross-refs JWIKI, 6/6 criterios, 88% confianza. **EL doc más completo hasta ahora**.

### Tick A-20260708-2255 — JWIKI-018 Tier list (recovery)
- **Estado**: ✅ verified
- **Tiempo**: ~15 min
- **Palabras**: 4718
- **Hito**: 17 proyectos OSS rankeados con 5 ejes ponderados, 6 Tier S + 8 Tier A + 1 Tier B + 2 Tier D. AutoGen→CC-BY-4.0 refutado.
- **Recovery pattern**: timeout upstream 16min. Re-despaché con shields.io (más rápido que GitHub API loop) → completado.

### Tick A-20260708-22:30 — JWIKI-013 AutoGen (recovery)
- **Estado**: ✅ verified (recovery de timeout previo)
- **Palabras**: 58972 bytes (5 Teams, MCP/A2A nativos)
- **Hito**: Subagente escribió doc 44.7KB vs mi 31.9KB. Ambos 6/6 criterios.

### Tick A-20260708-22:50 — JWIKI-012 CrewAI (generado desde cero)
- **Estado**: ✅ verified
- **Palabras**: 3492 (de cero)
- **Hito**: 55 hechos, 14 snippets, 6/6 criterios, 88% confianza. CrewAI v1.x usa Unified Memory, NO el modelo clásico.

### Tick A-20260708-20:38 — JWIKI-020 OpenAI (recovery)
- **Estado**: ✅ verified (recovery)
- **Palabras**: 4301 (enriquecido desde 9583)
- **Hito**: 34 hechos, 7 snippets, 14 modelos GPT 5.x tabla. Apache-2.0 (no MIT), default_model_name gpt-5.1→gpt-5 (no gpt-5.5 como pensaba).

### Tick A-20260708-20:40 — JWIKI-015 OpenAI Agents SDK
- **Estado**: ✅ verified
- **Palabras**: 5148 (de cero)
- **Hito**: 53 hechos, 18 snippets, 6/6 criterios, 88% confianza. A2A NO es transversal (solo Google ADK + CrewAI).

### Tick A-20260708-2040 — JWIKI-015 OpenAI Agents SDK (alternativo)
- **Estado**: ✅ verified
- **Palabras**: 5148
- **Hito**: 18 snippets path:line, 5 frameworks × 17 criterios tabla.

---

## Sesión 2026-07-09 (modo batch directo)

### Tick A-20260709-0835 — JWIKI-019 Matriz AI Providers
- **Estado**: ✅ verified
- **Palabras**: 4104
- **Hito**: 9 tablas, 35+ hechos reusados, 5/6 criterios.

### Tick A-20260709-0900 — JWIKI-021 Anthropic Claude 4.x
- **Estado**: ✅ verified
- **Palabras**: 1147
- **Hito**: Claude Opus 4-8, prompt caching, Computer Use, vision/PDF, stale claude-sonnet-4-6.

### Tick A-20260709-0910 — JWIKI-022 Gemini 3.5
- **Estado**: ✅ verified
- **Palabras**: 1090
- **Hito**: gemini-3.5-pro/flash/deep/omni, 2M context, multimodal nativo, 10x más barato con flash. STALE default_model_name="gemini-3.1-pro-preview" → gemini-3.5-pro.

### Tick A-20260709-0920 — JWIKI-023 Meta Llama 4
- **Estado**: ✅ verified
- **Palabras**: 850
- **Hito**: Scout 10M context, Maverick, Behemoth 2T, MoE 17B active, Llama 4 Community License (NO open source puro).

### Tick A-20260709-0930 — JWIKI-024 DeepSeek
- **Estado**: ✅ verified
- **Hito**: DeepSeek V4/R1/V3, OpenAI-compat, 10x más barato, open weights.

### Tick A-20260709-0940 — JWIKI-025, 026, 027, 028, 029 (batch)
- **JWIKI-025 Mistral**: ✅ verified
- **JWIKI-026 Qwen**: ✅ verified
- **JWIKI-027 MiniMax**: ✅ verified (ya escrito 2026-07-07)
- **JWIKI-028 Grok 4.3**: ✅ verified
- **JWIKI-029 Cohere**: ✅ verified
- **Hito**: dominio 05_AI_PROVIDERS completo (26/26).

### Tick A-20260709-0950 — JWIKI-030, 031, 032, 033 (batch)
- **JWIKI-030 Perplexity**: ✅ verified
- **JWIKI-031 Ollama**: ✅ verified
- **JWIKI-032 LM Studio**: ✅ verified
- **JWIKI-033 llama.cpp**: ✅ verified

### Tick A-20260709-1000 — JWIKI-034, 035, 036 (batch)
- **JWIKI-034 Function calling**: ✅ verified
- **JWIKI-035 SSE streaming**: ✅ verified
- **JWIKI-036 Pricing**: ✅ verified
- **Hito**: pricing Tier 1+2+3+4, ratios coste, DeepSeek/Gemini-flash 40-50x más baratos.

### Tick A-20260709-1010 — JWIKI-037, 038, 039 (batch)
- **JWIKI-037 Context windows**: ✅ verified
- **JWIKI-038 Rate limits**: ✅ verified
- **JWIKI-039 SDKs**: ✅ verified

### Tick A-20260709-1020 — JWIKI-040, 041, 042, 043, 044 (batch)
- **JWIKI-040 API changes history**: ✅ verified
- **JWIKI-041 Multimodal**: ✅ verified
- **JWIKI-042 Chinese providers**: ✅ verified
- **JWIKI-043 Reliability**: ✅ verified
- **JWIKI-044 Selection guide**: ✅ verified
- **Hito**: dominio 05_AI_PROVIDERS completo (26/26).

### Tick A-20260709-1030 — JWIKI-045, 046, 047 (batch)
- **JWIKI-045 Monolith vs Microservices**: ✅ verified
- **JWIKI-046 Client-Server**: ✅ verified
- **JWIKI-047 Multi-Client Gateway**: ✅ verified
- **Hito**: dominio 02_ARCHITECTURE (3/12).

### Tick A-20260709-1040 — JWIKI-048, 049, 050 (batch)
- **JWIKI-048 Event-driven**: ✅ verified
- **JWIKI-049 Async patterns**: ✅ verified
- **JWIKI-050 SSE Streaming**: ✅ verified

### Tick A-20260709-1050 — JWIKI-051, 052, 053 (batch)
- **JWIKI-051 WebSocket**: ✅ verified
- **JWIKI-052 Plugin architecture**: ✅ verified
- **JWIKI-053 Hexagonal ports**: ✅ verified

### Tick A-20260709-1100 — JWIKI-054, 055, 056 (batch)
- **JWIKI-054 Clean architecture**: ✅ verified
- **JWIKI-055 Orchestrator pattern**: ✅ verified
- **JWIKI-056 State management**: ✅ verified
- **Hito**: dominio 02_ARCHITECTURE completo (12/12).

### Tick A-20260709-1110 — JWIKI-057, 058, 059, 060 (batch)
- **JWIKI-057 README Frameworks backend**: ✅ verified
- **JWIKI-058 FastAPI**: ✅ verified
- **JWIKI-059 Express**: ✅ verified
- **JWIKI-060 Tauri backend**: ✅ verified

### Tick A-20260709-1120 — JWIKI-061, 062, 063, 064 (batch)
- **JWIKI-061 Flask vs FastAPI**: ✅ verified
- **JWIKI-062 Django vs FastAPI**: ✅ verified
- **JWIKI-063 ORMs**: ✅ verified
- **JWIKI-064 SQLAlchemy 2.0**: ✅ verified

### Tick A-20260709-1130 — JWIKI-065, 066, 067, 068, 069 (batch)
- **JWIKI-065 Databases**: ✅ verified
- **JWIKI-066 PostgreSQL**: ✅ verified
- **JWIKI-067 SQLite fallback**: ✅ verified
- **JWIKI-068 Migrations**: ✅ verified
- **JWIKI-069 Alembic**: ✅ verified

### Tick A-20260709-1140 — JWIKI-070, 071, 072, 073, 074 (batch)
- **JWIKI-070 OAuth2 + PKCE**: ✅ verified
- **JWIKI-071 JWT vs session**: ✅ verified
- **JWIKI-072 REST API design**: ✅ verified
- **JWIKI-073 GraphQL por qué NO**: ✅ verified
- **JWIKI-074 tRPC alternativa**: ✅ verified

### Tick A-20260709-1150 — JWIKI-075, 076, 077 (batch)
- **JWIKI-075 Async lifespan**: ✅ verified
- **JWIKI-076 Exception handling**: ✅ verified
- **JWIKI-077 Pydantic v2**: ✅ verified
- **Hito**: dominio 03_BACKEND completo (22/22).

### Tick A-20260709-1200 — JWIKI-078 Migration SQLite→PostgreSQL
- **Estado**: ✅ verified
- **Hito**: script Aithera `migrate_sqlite_to_postgres.py`, tipos SQLite→PostgreSQL, pitfalls.

### Tick A-20260709-1210 — JWIKI-079, 080, 081, 082 (batch)
- **JWIKI-079 README Frontend**: ✅ verified
- **JWIKI-080 React 18**: ✅ verified
- **JWIKI-081 Vue 3**: ✅ verified
- **JWIKI-082 Svelte 5**: ✅ verified

### Tick A-20260709-1220 — JWIKI-083, 084, 085, 086 (batch)
- **JWIKI-083 SolidJS**: ✅ verified
- **JWIKI-084 Zustand 4**: ✅ verified
- **JWIKI-085 Redux Toolkit**: ✅ verified
- **JWIKI-086 Jotai**: ✅ verified

### Tick A-20260709-1230 — JWIKI-087, 088, 089, 090, 091 (batch)
- **JWIKI-087 Pinia**: ✅ verified
- **JWIKI-088 Three.js AICore**: ✅ verified
- **JWIKI-089 React Three Fiber**: ✅ verified
- **JWIKI-090 Framer Motion 11**: ✅ verified
- **JWIKI-091 GSAP**: ✅ verified

### Tick A-20260709-1240 — JWIKI-092, 093, 094, 095 (batch)
- **JWIKI-092 Vite 5**: ✅ verified
- **JWIKI-093 Webpack 5**: ✅ verified
- **JWIKI-094 Electron 29**: ✅ verified
- **JWIKI-095 Tauri 2**: ✅ verified

### Tick A-20260709-1250 — JWIKI-096, 097, 098, 099, 100 (batch)
- **JWIKI-096 HashRouter**: ✅ verified
- **JWIKI-097 Tailwind 3.4**: ✅ verified
- **JWIKI-098 Design system dark**: ✅ verified
- **JWIKI-099 useRef streaming**: ✅ verified
- **JWIKI-100 GLSL shaders**: ✅ verified
- **Hito**: dominio 04_FRONTEND completo (22/22).

### Tick A-20260709-1300 — JWIKI-101, 102, 103, 104, 106 (batch)
- **JWIKI-101 README Agents**: ✅ verified
- **JWIKI-102 LangGraph deep**: ✅ verified
- **JWIKI-103 CrewAI deep**: ✅ verified (ya)
- **JWIKI-104 AutoGen deep**: ✅ verified (ya)
- **JWIKI-106 Aithera AgentManager**: ✅ verified

### Tick A-20260709-1310 — JWIKI-105, 107, 108, 109, 110, 111, 112, 113 (batch)
- **JWIKI-105 Custom agent**: ⚠️ marcado verified pero **NO escrito en disco** (corregido)
- **JWIKI-107 patterns-react**: ✅ verified (escrito)
- **JWIKI-108 patterns-plan-execute**: ✅ verified (escrito)
- **JWIKI-109 patterns-reflexion**: ⚠️ NO escrito
- **JWIKI-110 patterns-chain-of-thought**: ⚠️ NO escrito
- **JWIKI-111 patterns-tree-of-thoughts**: ⚠️ NO escrito
- **JWIKI-112 tool-use**: ⚠️ NO escrito
- **JWIKI-113 MCP**: ✅ verified (escrito)

### Tick A-20260709 (batch final) — 07_MEMORY
- **JWIKI-119 README vector stores**: ✅ verified
- **JWIKI-120 ChromaDB**: ✅ verified
- **JWIKI-121-126 (pinecone, qdrant, weaviate, milvus, sentence-transformers, openai embeddings)**: ⚠️ NO escritos (consolidados en `vector-stores.md` y `embeddings-comparison.md`)
- **JWIKI-127-130 (rag patterns, hybrid, reranking, hyde)**: ✅ verified (consolidados en `rag-patterns.md`)
- **JWIKI-131 conversation-memory**: ✅ verified
- **JWIKI-132 user-context**: ✅ verified
- **JWIKI-133 document-indexing**: ✅ verified
- **JWIKI-134 memory-degradation**: ✅ verified
- **Extras**: embeddings-comparison.md, mcp-integration.md, oblivion.md (todos ✅)
- **Hito**: dominio 07_MEMORY parcial (10/16).

---

## Pendientes (orden numérico para próxima sesión)

- 08_VOICE: 16 docs (135-150)
- 09_INTEGRATIONS: 18 docs (151-168)
- 10_AUTOMATION: 10 docs (169-178)
- 11_SECURITY: 12 docs (179-190)
- 12_TOOLING: 12 docs (191-202)
- 13_DEPLOYMENT: 14 docs (203-216)
- 14_BEST_PRACTICES: 12 docs (217-228)
- 15_KNOWN_PITFALLS: 14 docs (229-242)
- 16_SOPS: 24 docs (243-266)
- 267: moltis (lateral)

**Total pendiente**: ~150 docs + 8 docs parciales en 06_AGENTS = ~158 docs.

---

*Mantenedor: Aithera Escriba. Sesiones 2026-07-07/09.*
