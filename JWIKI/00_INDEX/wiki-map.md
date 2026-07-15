# JWIKI — Mapa de Interconexiones por Temas

> **Cómo usar este mapa**: cuando un agente (humano o AI) busca información sobre
> un tema específico (ej. "voice", "agents", "memory"), encuentra aquí todas las
> conexiones relevantes — qué dominios, qué archivos, qué conceptos están
> vinculados. No es una lista de IDs lineales, es una **red de relaciones**.

---

## 🔍 Búsqueda rápida por tema

Si quieres información sobre uno de estos temas, ve a la sección correspondiente:

- 🤖 **[Agents / Orchestrator / Multi-agent](#-agents--orchestrator--multi-agent)** → 06_AGENTS, 02_ARCHITECTURE, 10_AUTOMATION
- 🧠 **[Memory / RAG / ChromaDB / Oblivion](#-memory--rag--chromadb--oblivion)** → 07_MEMORY, 02_ARCHITECTURE
- 🎙️ **[Voice / STT / TTS / Realtime](#-voice--stt--tts--realtime)** → 08_VOICE, 04_FRONTEND
- 🤖 **[AI Providers / LLM / API Keys](#-ai-providers--llm--api-keys)** → 05_AI_PROVIDERS, 11_SECURITY
- 🔌 **[Integrations / OAuth / Telegram / Discord](#-integrations--oauth--telegram--discord)** → 09_INTEGRATIONS, 02_ARCHITECTURE
- 🏗️ **[Backend / FastAPI / SQLAlchemy](#-backend--fastapi--sqlalchemy)** → 03_BACKEND, 11_SECURITY
- 🎨 **[Frontend / React / 3D / Shaders](#-frontend--react--3d--shaders)** → 04_FRONTEND
- 🚀 **[Deployment / Build / Release](#-deployment--build--release)** → 13_DEPLOYMENT
- ⚙️ **[Automation / Scheduler / Rules](#-automation--scheduler--rules)** → 10_AUTOMATION, 16_SOPS
- 🛡️ **[Security / DPAPI / Prompt Injection](#-security--dpapi--prompt-injection)** → 11_SECURITY, 15_KNOWN_PITFALLS
- 🛠️ **[Tooling / ToolManager / Execution](#-tooling--toolmanager--execution)** → 12_TOOLING, 06_AGENTS
- 📚 **[Best Practices / Testing / Docs](#-best-practices--testing--docs)** → 14_BEST_PRACTICES, 16_SOPS
- ⚠️ **[Pitfalls / Bugs / Anti-patterns](#-pitfalls--bugs--anti-patterns)** → 15_KNOWN_PITFALLS
- 🏛️ **[Architecture / Design / Patterns](#-architecture--design--patterns)** → 02_ARCHITECTURE
- 🌐 **[JARVIS-like Landscape / OSS Projects](#-jarvis-like-landscape--oss-projects)** → 01_LANDSCAPE

---

## 🤖 Agents / Orchestrator / Multi-agent

**Tema**: agent loops, frameworks, V1.0 Orchestrator, multi-agent handoffs.

**Dominios primarios**:
- `06_AGENTS/` — Patterns, frameworks, Aithera AgentManager.
- `02_ARCHITECTURE/orchestrator-pattern.md` — V1.0 diseño.
- `10_AUTOMATION/` — Approval flows, rules.

**Conceptos relacionados**:
- `ReAct`, `Plan-Execute`, `Reflexion`, `CoT`, `ToT` (todos en 06_AGENTS/patterns-*.md).
- `Handoffs` (OpenAI Agents SDK pattern) →借鉴 para Aithera V1.0.
- `Multi-agent jerárquico` (manager + sub-agents)借鉴 de CrewAI.
- `Approval flows` (human-in-the-loop).

**Archivos críticos**:
- `06_AGENTS/aithera-agent-manager.md` — AgentManager V0.5+ (~200 líneas vs 2000+ de LangChain).
- `06_AGENTS/agent-loops.md` — Single vs multi loops.
- `06_AGENTS/sub-agents.md` — Aislamiento + concurrencia.
- `02_ARCHITECTURE/orchestrator-pattern.md` — V1.0 Orchestrator.
- `10_AUTOMATION/approval-flows-automation.md` — Approval gates.

**Cuando buscar aquí**: cualquier cosa sobre "agent", "orchestrator", "intent", "planner", "tools", "tool calling", "handoff", "sub-agent".

---

## 🧠 Memory / RAG / ChromaDB / Oblivion

**Tema**: ChromaDB, embeddings, RAG patterns, oblivion, MOS V0.85.

**Dominios primarios**:
- `07_MEMORY/` — Vector stores, embeddings, RAG, conversation memory, user context.
- `02_ARCHITECTURE/` — Memory architecture.
- `11_SECURITY/` — Memory encryption (oblivion = GDPR).

**Conceptos relacionados**:
- ChromaDB (current) vs pgvector (V0.85+ opcional).
- Sentence-transformers (local) vs OpenAI/Cohere embeddings.
- RAG patterns: naive, hybrid (BM25 + semantic), reranking (cross-encoder), HyDE.
- MOS Skeleton V0.85 (M1-M5 sprints): ingesta proactiva, briefings, skills, oblivion.
- Long-term memory, episodic memory, semantic memory, procedural memory.

**Archivos críticos**:
- `07_MEMORY/chromadb.md` — ChromaDB en Aithera V0.6+.
- `07_MEMORY/vector-stores.md` — Comparativa (Pinecone/Qdrant/Weaviate/Milvus).
- `07_MEMORY/embeddings-comparison.md` — Sentence-transformers vs OpenAI.
- `07_MEMORY/rag-patterns.md` — 4 patterns.
- `07_MEMORY/oblivion.md` — Selective memory pruning (GDPR).
- `07_MEMORY/conversation-memory.md` — Short-term + long-term.
- `07_MEMORY/user-context.md` — Preferencias + habits.
- `07_MEMORY/memory-degradation.md` — Graceful degradation.

**Cuando buscar aquí**: "memory", "chroma", "rag", "embedding", "vector", "search", "context", "skill", "forget", "oblivion", "MOS", "briefing".

---

## 🎙️ Voice / STT / TTS / Realtime

**Tema**: Whisper STT, ElevenLabs/EdgeTTS/Kokoro/eSpeak, voice pipelines, realtime.

**Dominios primarios**:
- `08_VOICE/` — TTS/STT comparativa, latency, voice cloning.
- `04_FRONTEND/` — UI components para voice.

**Conceptos relacionados**:
- STT: Whisper, faster-whisper (Aithera V0.8), Deepgram, Google STT.
- TTS: ElevenLabs primary, EdgeTTS fallback, Kokoro local, eSpeak ultra-fallback.
- Realtime: OpenAI gpt-realtime-2, Gemini Live, voice orchestrator.
- Wake word: Porcupine, openWakeWord.
- Voice cloning: ElevenLabs, Coqui XTTS v2.
- Latency budget: VAD → STT → LLM → TTS, target <2s TTFB.
- Multilingual: ElevenLabs multilingual_v2, EdgeTTS 100+ idiomas.

**Archivos críticos**:
- `08_VOICE/README.md` — Stack Aithera V0.8.
- `08_VOICE/elevenlabs.md` — TTS primary.
- `08_VOICE/whisper.md` — STT.
- `08_VOICE/voice-pipelines-realtime.md` — Pipeline async.
- `08_VOICE/voice-latency-budget.md` — TTFB <2s target.
- `08_VOICE/voice-cloning.md` — ElevenLabs + XTTS v2.
- `08_VOICE/voice-orchestrator.md` — V1.0+ diseño.

**Cuando buscar aquí**: "voice", "tts", "stt", "whisper", "elevenlabs", "speak", "audio", "realtime", "wake word", "vad".

---

## 🤖 AI Providers / LLM / API Keys

**Tema**: 14 proveedores IA, pricing, function calling, API keys encryption.

**Dominios primarios**:
- `05_AI_PROVIDERS/` — Tier 1/2/3, local-first, comparativas.
- `11_SECURITY/api-keys-*.md` — Encryption, keyring.

**Conceptos relacionados**:
- Tier 1 (Frontier): OpenAI, Anthropic, Google, Meta.
- Tier 2 (Affordable): DeepSeek, Mistral, Qwen, Cohere.
- Tier 3 (Specialized): xAI Grok, Perplexity, MiniMax, HuggingFace.
- Local-first: Ollama, LM Studio, llama.cpp.
- Function calling: OpenAI tools, Anthropic tool_use, Gemini function_call.
- API key storage: DPAPI (V0.8+), keyring, secrets managers.
- Cost optimization: pricing tiers, prompt caching (Anthropic 90% descuento).

**Archivos críticos**:
- `05_AI_PROVIDERS/README.md` — Matriz comparativa.
- `05_AI_PROVIDERS/selection-guide.md` — Cuándo elegir qué.
- `05_AI_PROVIDERS/pricing-comparison.md` — Pricing tiers.
- `05_AI_PROVIDERS/function-calling.md` — Tool use.
- `11_SECURITY/api-keys-encrypted-db.md` — DPAPI V0.8+.

**Cuando buscar aquí**: "provider", "llm", "openai", "anthropic", "claude", "gpt", "gemini", "api key", "pricing".

---

## 🔌 Integrations / OAuth / Telegram / Discord

**Tema**: Google Workspace, Telegram, Discord, WhatsApp, Notion, Linear, GitHub.

**Dominios primarios**:
- `09_INTEGRATIONS/` — 18 docs por servicio.
- `02_ARCHITECTURE/multi-client.md` — Gateway multi-canal.

**Conceptos relacionados**:
- OAuth2 + PKCE (Google, Microsoft).
- Gateway (V0.8+) channel-agnostic.
- Channel adapters (Telegram actual, Discord/Slack futuros).
- Email (Gmail API, IMAP/SMTP, CalDAV).
- Calendar (Google Calendar API, CalDAV).
- Productivity (Notion, Linear, GitHub).
- Webhooks (entrantes + salientes).

**Archivos críticos**:
- `09_INTEGRATIONS/google-oauth-flow.md` — OAuth2 + PKCE flow.
- `09_INTEGRATIONS/gmail-api.md` — Gmail REST (44KB tool Aithera).
- `09_INTEGRATIONS/google-calendar-api.md` — Calendar API.
- `09_INTEGRATIONS/telegram-bot.md` — Aithera V0.8 adapter.
- `09_INTEGRATIONS/auto-reply-patterns.md` — Inbox Zero.
- `09_INTEGRATIONS/meeting-detection.md` — 2-stage AMD GAIA.
- `02_ARCHITECTURE/multi-client.md` — Gateway.

**Cuando buscar aquí**: "telegram", "discord", "gmail", "calendar", "oauth", "integration", "webhook", "channel", "gateway".

---

## 🏗️ Backend / FastAPI / SQLAlchemy

**Tema**: FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, migrations.

**Dominios primarios**:
- `03_BACKEND/` — 22 docs (frameworks, ORMs, DB, auth, REST, lifespan, etc.).

**Conceptos relacionados**:
- FastAPI lifespan (startup/shutdown).
- SQLAlchemy 2.0 (declarative_base, async sessions).
- Pydantic v2 (from_attributes=True, NO orm_mode).
- Alembic migrations (autogenerate + manual).
- PostgreSQL primary + SQLite fallback.
- REST API conventions.
- Async lifespan.
- Global exception handler.
- tRPC, GraphQL (por qué NO en Aithera).

**Archivos críticos**:
- `03_BACKEND/fastapi.md` — Framework.
- `03_BACKEND/sqlalchemy-2.md` — ORM.
- `03_BACKEND/alembic.md` — Migrations.
- `03_BACKEND/pydantic-v2.md` — Validators.
- `03_BACKEND/api-design-rest.md` — REST conventions.
- `03_BACKEND/async-lifespan.md` — Lifespan pattern.

**Cuando buscar aquí**: "backend", "fastapi", "sqlalchemy", "alembic", "migration", "pydantic", "api", "endpoint", "router".

---

## 🎨 Frontend / React / 3D / Shaders

**Tema**: React 18, R3F, three.js, AICore 3D, custom shaders, Tailwind, Zustand.

**Dominios primarios**:
- `04_FRONTEND/` — 22 docs (frameworks, state, 3D, animations, build, desktop).

**Conceptos relacionados**:
- React 18 (concurrent features, Suspense).
- @react-three/fiber + drei (AICore 3D).
- three.js 0.160 (custom shaders).
- Framer Motion 11 (transitions).
- Zustand 4 (state management).
- Tailwind 3.4 (utility-first CSS).
- HashRouter (Electron file:// requirement).
- useRef pattern para streaming (CLAUDE.md §2 OBLIGATORIO).
- Electron 29 vs Tauri 2.

**Archivos críticos**:
- `04_FRONTEND/react.md` — React 18 patterns.
- `04_FRONTEND/3d-react-three-fiber.md` — R3F + shaders.
- `04_FRONTEND/state-zustand.md` — State.
- `04_FRONTEND/useref-streaming.md` — Pattern OBLIGATORIO.
- `04_FRONTEND/routing-hashrouter.md` — HashRouter.
- `04_FRONTEND/tailwind.md` — CSS.

**Cuando buscar aquí**: "react", "frontend", "3d", "shader", "r3f", "zustand", "tailwind", "ui", "electron", "desktop".

---

## 🚀 Deployment / Build / Release

**Tema**: electron-builder, NSIS, Docker, PWA, CI, GitHub Releases, backup.

**Dominios primarios**:
- `13_DEPLOYMENT/` — 14 docs.

**Conceptos relacionados**:
- electron-builder 24 (NSIS Windows).
- Auto-update via electron-updater + GitHub Releases.
- Code signing (Certum, ~$30/año).
- Tauri 2 alternative (10MB vs 150MB bundle).
- Docker compose para SaaS (V1.5+).
- PWA manifest + service worker.
- GitHub Actions CI/CD.
- Backup/restore (pg_dump, cron).

**Archivos críticos**:
- `13_DEPLOYMENT/electron-builder.md` — Build config.
- `13_DEPLOYMENT/electron-auto-update.md` — Auto-update.
- `13_DEPLOYMENT/docker-compose-backend.md` — SaaS deploy.
- `13_DEPLOYMENT/pwa-manifest.md` — PWA setup.
- `13_DEPLOYMENT/backup-restore-db.md` — Backups.
- `16_SOPS/deploy-electron-build.md` — SOP release.

**Cuando buscar aquí**: "deploy", "build", "release", "electron", "docker", "pwa", "ci", "github actions", "backup".

---

## ⚙️ Automation / Scheduler / Rules

**Tema**: APScheduler, rule engine, approval flows, automation rules.

**Dominios primarios**:
- `10_AUTOMATION/` — 10 docs.
- `16_SOPS/scheduler-config.md` — SOP setup.

**Conceptos relacionados**:
- APScheduler with SQLAlchemy jobstore.
- Rule engine JSON-based.
- Trigger types: cron, interval, event, webhook, manual.
- Action types: email.*, calendar.*, chat.*, agent.run.
- Approval gates (Hub UI + Telegram inline).
- Reglas predefinidas (1-click enable).

**Archivos críticos**:
- `10_AUTOMATION/apscheduler.md` — Setup.
- `10_AUTOMATION/rules-engines.md` — JSON structure.
- `10_AUTOMATION/approval-flows-automation.md` — Gates.
- `10_AUTOMATION/automation-rules-examples.md` — 8 reglas predefinidas.
- `16_SOPS/scheduler-config.md` — SOP.

**Cuando buscar aquí**: "automation", "scheduler", "rule", "trigger", "approval", "apscheduler", "cron".

---

## 🛡️ Security / DPAPI / Prompt Injection

**Tema**: API key encryption, OAuth2, sandboxing, prompt injection, CORS.

**Dominios primarios**:
- `11_SECURITY/` — 12 docs.
- `15_KNOWN_PITFALLS/` — bugs reales Aithera V0.7.3.

**Conceptos relacionados**:
- DPAPI Windows (V0.8+).
- OS keyring (cross-platform V0.85+).
- OAuth2 + PKCE + state parameter.
- Tool sandboxing (whitelist + validation + timeout).
- Path traversal prevention.
- Command injection prevention.
- Prompt injection defenses (B21 + system prompt).
- Encryption at rest (V0.85+).
- CORS restringido.

**Archivos críticos**:
- `11_SECURITY/api-keys-encrypted-db.md` — DPAPI V0.8+.
- `11_SECURITY/sandboxing-tool-whitelist.md` — Sandboxing.
- `11_SECURITY/path-traversal-prevention.md` — Path traversal.
- `11_SECURITY/command-injection-prevention.md` — Command injection.
- `11_SECURITY/prompt-injection-defenses.md` — B21 + layers.
- `11_SECURITY/oauth-pkce.md` — OAuth2 best practices.
- `11_SECURITY/oauth-state-parameter.md` — CSRF protection.
- `15_KNOWN_PITFALLS/api-keys-plaintext.md` — Bug history.
- `15_KNOWN_PITFALLS/cors-open-prod.md` — Bug history.

**Cuando buscar aquí**: "security", "dpapi", "keyring", "oauth", "cors", "sandbox", "prompt injection", "encryption", "secret".

---

## 🛠️ Tooling / ToolManager / Execution

**Tema**: 8 tools Aithera, ToolManager, execution engine, tool calling format.

**Dominios primarios**:
- `12_TOOLING/` — 12 docs.
- `06_AGENTS/tool-use-function-calling.md` — Function calling pattern.

**Conceptos relacionados**:
- 8 tools: filesystem, shell, git, powershell, email, calendar, voice, memory.
- ToolManager + whitelist per agent.
- Execution engine (validation pipeline: whitelist + schema + timeout + audit).
- Pydantic schema validation.
- Tool calling formats (OpenAI/Anthropic/Gemini).
- Tool timeout handling (asyncio.wait_for).
- God-endpoint → split por dominios.

**Archivos críticos**:
- `12_TOOLING/execution-engine-pattern.md` — Engine.
- `12_TOOLING/tool-manager-pattern.md` — Registry.
- `12_TOOLING/email-tool.md` — Email (44KB).
- `12_TOOLING/calendar-tool.md` — Calendar (29KB).
- `12_TOOLING/filesystem-tool.md` — Filesystem.
- `12_TOOLING/shell-tool.md` — Shell.
- `12_TOOLING/tool-calling-llm-format.md` — Provider formats.

**Cuando buscar aquí**: "tool", "toolmanager", "execution", "function calling", "email tool", "calendar tool", "filesystem", "shell".

---

## 📚 Best Practices / Testing / Docs

**Tema**: ADRs, performance, UX, conventions, observability, testing, docs.

**Dominios primarios**:
- `14_BEST_PRACTICES/` — 12 docs.
- `16_SOPS/` — 24 docs (operaciones).

**Conceptos relacionados**:
- Architecture Decision Records (ADRs).
- Performance: streaming (TTFT <750ms), caching (Redis, LLM prompt cache).
- UX: feedback loops, error handling.
- Conventions: code structure, naming (Python/TS/DB/URL/AI).
- Observability: structlog JSON, Prometheus metrics.
- Testing: 5 levels (smoke/unit/contract/integration/E2E).
- Documentation: docs as code, wiki-map.

**Archivos críticos**:
- `14_BEST_PRACTICES/README.md` — Overview.
- `14_BEST_PRACTICES/architecture-decisions.md` — ADRs 001-008.
- `14_BEST_PRACTICES/performance-streaming.md` — SSE streaming.
- `14_BEST_PRACTICES/testing-strategy.md` — 5 levels.
- `14_BEST_PRACTICES/documentation-strategy.md` — Docs as code.
- `16_SOPS/` — 24 SOPs paso a paso.

**Cuando buscar aquí**: "best practices", "convention", "naming", "adr", "performance", "ux", "testing", "documentation".

---

## ⚠️ Pitfalls / Bugs / Anti-patterns

**Tema**: bugs reales Aithera V0.2-V0.7.3, anti-patterns comunes.

**Dominios primarios**:
- `15_KNOWN_PITFALLS/` — 14 docs.

**Conceptos relacionados**:
- Streaming closure bug (V0.2 fixed).
- God-endpoint anti-pattern.
- API keys plaintext (V0.7.3 fixed V0.8).
- CORS abierto (V0.7.3 fixed V0.8).
- Módulos paralelos legacy (eliminados Sprint 1).
- Pydantic v1 vs v2.
- React 18 strict mode double-render.
- ChromaDB size (sentence-transformers 80MB).
- MiniMax API changes (stale defaults).
- HashRouter obligatorio en Electron.
- Alembic schema divergence.

**Archivos críticos**:
- `15_KNOWN_PITFALLS/README.md` — Overview.
- `15_KNOWN_PITFALLS/streaming-closure-bug.md` — Closure bug.
- `15_KNOWN_PITFALLS/email-assistant-god-endpoint.md` — 2038-line god-endpoint.
- `15_KNOWN_PITFALLS/api-keys-plaintext.md` — DPAPI migration.
- `15_KNOWN_PITFALLS/cors-open-prod.md` — CORS fix.
- `15_KNOWN_PITFALLS/pydantic-v1-vs-v2.md` — Pydantic migration.
- `15_KNOWN_PITFALLS/god-endpoint-pattern.md` — Anti-pattern general.
- `15_KNOWN_PITFALLS/modules-parallel-legacy.md` — Legacy code.

**Cuando buscar aquí**: "bug", "pitfall", "antipattern", "mistake", "lesson", "gotcha", "broken".

---

## 🏛️ Architecture / Design / Patterns

**Tema**: arquitectura backend/frontend, monolith vs microservices, hexagonal, clean.

**Dominios primarios**:
- `02_ARCHITECTURE/` — 13 docs.
- `14_BEST_PRACTICES/architecture-decisions.md` — ADRs.

**Conceptos relacionados**:
- Monolith modular vs microservices (Aithera V0.7.3 monolith).
- Client-server (Electron ↔ FastAPI).
- Multi-client Gateway (V0.8+).
- Event-driven vs request-response.
- Async patterns (asyncio).
- SSE streaming.
- WebSocket bidireccional.
- Plugin architecture.
- Hexagonal / Clean architecture (借鉴).
- Orchestrator pattern (V1.0).
- State management patterns.

**Archivos críticos**:
- `02_ARCHITECTURE/README.md` — Monolith vs microservices.
- `02_ARCHITECTURE/client-server.md` — Cliente único backend único.
- `02_ARCHITECTURE/multi-client.md` — Gateway multi-canal.
- `02_ARCHITECTURE/orchestrator-pattern.md` — V1.0 Orchestrator.
- `02_ARCHITECTURE/event-driven.md` — APScheduler events.
- `02_ARCHITECTURE/async-patterns.md` — asyncio patterns.
- `02_ARCHITECTURE/sse-streaming.md` — SSE protocol.
- `02_ARCHITECTURE/hexagonal-ports.md` — Ports & Adapters.
- `02_ARCHITECTURE/clean-architecture.md` — Uncle Bob.

**Cuando buscar aquí**: "architecture", "design", "pattern", "monolith", "microservice", "orchestrator", "state management".

---

## 🌐 JARVIS-like Landscape / OSS Projects

**Tema**: OpenClaw, Hermes, Superpowers, AutoGen, CrewAI, Google ADK, OpenAI Agents SDK, LlamaIndex, Semantic Kernel, moltis.

**Dominios primarios**:
- `01_LANDSCAPE/` — 20 docs (proyectos OSS + comparativas).
- `06_AGENTS/crewai-deep.md`, `autogen-deep.md` — Deep dives.

**Conceptos relacionados**:
- Tier S (>100k★): OpenClaw 382k, Superpowers 250k, Hermes 211k, Claude Code 137k, LangChain 141k.
- Tier A (>20k★): Aider, AutoGen, CrewAI, OpenAI Agents SDK, Google ADK, LlamaIndex, Semantic Kernel, DeepSeek, Anthropic, OpenAI, Google, Mistral.
- Frameworks con A2A: Google ADK + CrewAI nativos.
- MCP-first: moltis (nuevo, baja tracción).
- Skill frameworks: obra/superpowers (v6.1.1, MIT, 250k★).

**Archivos críticos**:
- `01_LANDSCAPE/history.md` — Cronología 1990s-2026.
- `01_LANDSCAPE/projects.md` — Comparativa 11+ proyectos.
- `01_LANDSCAPE/openclaw.md` — OpenClaw 382k★.
- `01_LANDSCAPE/openclaw-code-audit.md` — Audit código real (jul 2026, 159 path:line, 25 canales/78 providers/65 skills bundled).
- `01_LANDSCAPE/openclaw-architecture.md` — Arquitectura 7 diagramas ASCII.
- `01_LANDSCAPE/hermes-agent.md` — Hermes 211k★ v0.18.2.
- `01_LANDSCAPE/hermes-agent-code-audit.md` — Audit código real (jul 2026, 158 path:line, 26 correcciones).
- `01_LANDSCAPE/hermes-agent-architecture.md` — 12 diagramas Mermaid.
- `01_LANDSCAPE/superpowers.md` — Superpowers 250k★.
- `01_LANDSCAPE/superpowers-code-audit.md` — Audit código real (jul 2026, 14 skills catalogadas).
- `01_LANDSCAPE/openai-agents-sdk.md` — OpenAI Agents SDK 28k★.
- `01_LANDSCAPE/openai-agents-sdk-code-audit.md` — Audit código real (jul 2026, 8965 palabras, 44-row divergence table).
- `01_LANDSCAPE/openai-agents-sdk-architecture.md` — 14 capas diagramas.
- `01_LANDSCAPE/google-adk.md` — Google ADK v2.4.0.
- `01_LANDSCAPE/crewai.md`, `autogen.md` — Deep dives.
- `01_LANDSCAPE/langgraph.md` — LangGraph overview.
- `01_LANDSCAPE/langgraph-code-audit.md` — Audit código real (jul 2026, 14 correcciones, `create_react_agent` deprecated).
- `01_LANDSCAPE/langgraph-architecture.md` — Arquitectura LangGraph.
- `01_LANDSCAPE/moltis.md` — MCP-first OSS.
- `01_LANDSCAPE/licenses.md` — Licencias OSS.

**Cuando buscar aquí**: "jarvis", "openclaw", "hermes", "superpowers", "autogen", "crewai", "langgraph", "adk", "agents sdk", "competencia", "benchmark".

---

## 🔗 Cross-cutting connections

Estos temas tocan varios dominios:

### "Quiero añadir un tool nuevo"
→ `12_TOOLING/` (pattern + validation) + `11_SECURITY/sandboxing-tool-whitelist.md` (whitelist) + `06_AGENTS/tool-use-function-calling.md` (LLM format) + `16_SOPS/create-tool.md` (SOP paso a paso).

### "Quiero añadir un proveedor IA"
→ `05_AI_PROVIDERS/README.md` (overview) + `11_SECURITY/api-keys-encrypted-db.md` (DPAPI) + `16_SOPS/add-ai-provider.md` (SOP).

### "Quiero añadir un canal al Gateway"
→ `02_ARCHITECTURE/multi-client.md` (Gateway) + `09_INTEGRATIONS/` (ejemplos Telegram/Discord) + `15_KNOWN_PITFALLS/hashrouter-vs-browser.md` (Electron).

### "Quiero debug streaming"
→ `15_KNOWN_PITFALLS/streaming-closure-bug.md` + `04_FRONTEND/useref-streaming.md` + `16_SOPS/debug-streaming-stuck.md` + `08_VOICE/voice-pipelines-realtime.md`.

### "Quiero hacer backup/restore"
→ `13_DEPLOYMENT/backup-restore-db.md` + `11_SECURITY/data-encryption-rest.md` + `16_SOPS/backup-restore-aithera.md` + `16_SOPS/rollback-migration.md`.

### "Quiero entender un bug real de Aithera"
→ `15_KNOWN_PITFALLS/` (14 docs de bugs) + CLAUDE.md §16 (deuda técnica crítica).

### "Quiero借鉴 del landscape JARVIS-like"
→ `01_LANDSCAPE/` (20 docs) + `06_AGENTS/agent-frameworks.md` (comparativa) + `02_ARCHITECTURE/orchestrator-pattern.md` (V1.0借鉴).

### "Quiero entender la decisión V0.85 MOS"
→ `07_MEMORY/` (ChromaDB, oblivion, MOS) + `PLAN_MAESTRO_2026/07_MOS_V085_DISENO.md` + `08_MOS_ARQUITECTURA_COMPLETA.md`.

### "Quiero implementar V1.0 Orchestrator"
→ `02_ARCHITECTURE/orchestrator-pattern.md` + `06_AGENTS/multi-agent-hierarchical.md` + `06_AGENTS/handoffs-delegation.md` + `06_AGENTS/aithera-agent-manager.md` + `10_AUTOMATION/approval-flows-automation.md` + `PLAN_MAESTRO_2026/11_AUTOMATION_ORCHESTRATOR_RFC.md`.

---

## 📂 Quick reference — Por dominio

Si sabes qué dominio buscas:

| Dominio | Path | # docs |
|---|---|---|
| 00_INDEX | `JWIKI/00_INDEX/` | 4 (status, wiki-map, README, CHANGELOG) |
| 01_LANDSCAPE | `JWIKI/01_LANDSCAPE/` | 20 (proyectos OSS JARVIS-like) |
| 02_ARCHITECTURE | `JWIKI/02_ARCHITECTURE/` | 13 (design patterns) |
| 03_BACKEND | `JWIKI/03_BACKEND/` | 22 (FastAPI, SQLAlchemy, etc.) |
| 04_FRONTEND | `JWIKI/04_FRONTEND/` | 22 (React, R3F, AICore) |
| 05_AI_PROVIDERS | `JWIKI/05_AI_PROVIDERS/` | 26 (14 providers + comparativas) |
| 06_AGENTS | `JWIKI/06_AGENTS/` | 18 (patterns + frameworks) |
| 07_MEMORY | `JWIKI/07_MEMORY/` | 16 (ChromaDB, RAG, oblivion) |
| 08_VOICE | `JWIKI/08_VOICE/` | 16 (STT, TTS, realtime) |
| 09_INTEGRATIONS | `JWIKI/09_INTEGRATIONS/` | 18 (Google, Telegram, etc.) |
| 10_AUTOMATION | `JWIKI/10_AUTOMATION/` | 10 (APScheduler, rules) |
| 11_SECURITY | `JWIKI/11_SECURITY/` | 12 (DPAPI, OAuth, sandboxing) |
| 12_TOOLING | `JWIKI/12_TOOLING/` | 12 (ToolManager + 8 tools) |
| 13_DEPLOYMENT | `JWIKI/13_DEPLOYMENT/` | 14 (electron-builder, Docker, PWA) |
| 14_BEST_PRACTICES | `JWIKI/14_BEST_PRACTICES/` | 12 (ADRs, testing, conventions) |
| 15_KNOWN_PITFALLS | `JWIKI/15_KNOWN_PITFALLS/` | 14 (bugs reales Aithera) |
| 16_SOPS | `JWIKI/16_SOPS/` | 24 (procedimientos paso a paso) |

**Total: 271 IDs verificados / 375 archivos .md en disco**.

---

## 🔄 Update cadence

- **Cada 2-3 días**: audit JWIKI para detectar info stale.
- **Skill `jwiki-tick`** mantiene el loop.
- **Cron `2dafcb3f8959` (jwiki-tick-a)** corre cada 30min (single-team mode).

Para audit: revisar OSS data (stars, releases) + nuevas versiones de tools/frameworks + bugs nuevos Aithera.

---

*Última actualización: 2026-07-09 — wiki-map rediseñado como mapa de interconexiones por temas.*