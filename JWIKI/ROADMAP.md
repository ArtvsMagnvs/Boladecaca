# ROADMAP JWIKI

> Plan de investigación por fases. Las fases están ordenadas por **dependencia**: cada
> fase construye sobre la anterior. Meta: **15-30 días → la mayor wiki existente sobre
> proyectos JARVIS-like**.

## Estado por fase

| Fase | Nombre | Estado | ETA |
|---|---|---|---|
| 0 | Bootstrap (estructura + constitución) | 🟢 Completa | 2026-06-30 |
| 1 | Landscape + AI Providers (cimientos) | 🔴 Pendiente | semana 1 |
| 2 | Backend + Frontend (stack base) | 🔴 Pendiente | semana 1-2 |
| 3 | Agentes + Memory (inteligencia) | 🔴 Pendiente | semana 2 |
| 4 | Voice + Integrations (conectividad) | 🔴 Pendiente | semana 2-3 |
| 5 | Automation + Security (producción) | 🔴 Pendiente | semana 3 |
| 6 | Tooling + Deployment (operacional) | 🔴 Pendiente | semana 3-4 |
| 7 | Best Practices + Known Pitfalls (sabiduría) | 🔴 Pendiente | semana 4 |
| 8 | SOPs + Mantenimiento (operación) | 🔴 Pendiente | continuo |

---

## FASE 0 — Bootstrap (✅ Completa)

**Objetivo**: dejar la base lista para que Investigador, Escriba y Auditor puedan operar.

**Entregables**:
- [x] 16 directorios de dominio creados
- [x] 16 README.md de sección (esqueletos)
- [x] README.md raíz
- [x] CONSTITUTION.md con master prompt completo
- [x] ROADMAP.md (este documento)
- [x] CONTRIBUTING.md
- [x] CHANGELOG.md
- [x] 00_INDEX/README.md, architecture.md, dependencies.md, status.md
- [x] 00_INDEX/TEMPLATE.md (plantilla de documento)
- [x] 00_INDEX/WORKFLOW.md (loop autónomo)
- [x] 00_INDEX/task_queue.md (cola activa, vacía)
- [x] 00_INDEX/wiki-map.md (mapa vivo, activo desde día 1)
- [x] Equipo `aithera-wiki-*` creado (3 agentes)

---

## FASE 1 — Cimientos: Landscape + AI Providers (🔴 Pendiente)

**Por qué primero**: sin entender qué proyectos OSS existen y qué proveedores IA
dominan el mercado, todo lo demás es contexto sin base.

**Dominios**: `01_LANDSCAPE/`, `05_AI_PROVIDERS/`

### 1A — Landscape (01_LANDSCAPE/)

- Historia cronológica de asistentes personales AI (1990s → 2026)
- Árbol de proyectos: desde early Python JARVIS hasta OpenClaw/OpenHuman/OpenJarvis
- Comparativa de proyectos OSS activos (>500 stars):
  - OpenClaw (TS, multi-platform)
  - OpenHuman (Rust + TS, desktop-first)
  - OpenJarvis (Python, local-first, Stanford)
  - JarvisAgent (Tauri + Vue, coding-focused)
  - Hermes Agent (Nous Research, multi-modal)
  - Clawdbot (MCP-based)
  - Superpowers (Skill framework)
- Frameworks de AI agents más usados:
  - LangGraph, CrewAI, AutoGen, Google ADK, OpenAI Agents SDK
  - Semantic Kernel, LlamaIndex, Smolagents, Strands
- Estado actual: quién está activo, quién abandonado, quién es vaporware
- Licencias (MIT vs Apache vs custom)

### 1B — AI Providers (05_AI_PROVIDERS/)

- **Tier 1 (frontier)**: OpenAI (GPT-5, o-series), Anthropic (Claude 4), Google (Gemini 3), Meta (Llama 4)
- **Tier 2 (strong open/affordable)**: DeepSeek, Mistral, Qwen, GLM, Cohere
- **Tier 3 (specialized)**: xAI (Grok), Perplexity, MiniMax, HuggingFace Inference
- **Local-first**: Ollama, LM Studio, llama.cpp, vLLM
- Por cada proveedor documentar:
  - API endpoint, formato (OpenAI-compatible vs custom)
  - Modelos disponibles y tamaños de contexto
  - Pricing (input/output por 1M tokens)
  - Function calling support
  - Streaming support
  - Rate limits
  - SDK oficial vs community
  - Status histórico de la API (cambios, deprecaciones)

**Output esperado**:
- `01_LANDSCAPE/README.md` con comparativa de proyectos OSS
- `01_LANDSCAPE/history.md` cronología
- `01_LANDSCAPE/projects.md` con detalle de cada proyecto OSS
- `01_LANDSCAPE/agent-frameworks.md` con frameworks de agentes
- `05_AI_PROVIDERS/README.md` matriz comparativa
- `05_AI_PROVIDERS/openai.md`, `anthropic.md`, `gemini.md`, `meta-llama.md`, `deepseek.md`, `mistral.md`, `qwen.md`, `minimax.md`, `local-ollama.md`

**Tiempo estimado**: 1-2 sesiones largas de Investigador + Escriba.

---

## FASE 2 — Backend + Frontend (🔴 Pendiente)

**Por qué segundo**: una vez que sabemos qué hay en el ecosistema, necesitamos saber
cómo se construye cada capa.

### 2A — Backend (03_BACKEND/)
- **Frameworks**: FastAPI (Python), Express (Node), Tauri (Rust), Flask, Django
- **Comparativa**: async vs sync, performance, ecosystem, deployment
- **ORMs**: SQLAlchemy 2.0, Tortoise, Prisma, Drizzle
- **Bases de datos**: PostgreSQL, SQLite, MariaDB, MongoDB, ChromaDB
- **Migraciones**: Alembic, yoyo-migrations, Prisma migrate, Drizzle Kit
- **Auth**: OAuth2 (Authorization Code + PKCE), JWT, session cookies
- **API patterns**: REST vs GraphQL vs tRPC vs gRPC

### 2B — Frontend (04_FRONTEND/)
- **Frameworks UI**: React, Vue, Svelte, SolidJS
- **State management**: Zustand, Redux, Jotai, Pinia
- **3D/Animación**: Three.js, React Three Fiber, Framer Motion, GSAP
- **Build tools**: Vite, Webpack, Turbopack
- **Desktop wrappers**: Electron, Tauri, Neutralino
- **Routing**: HashRouter (Electron file://) vs BrowserRouter

**Output esperado**:
- `03_BACKEND/README.md` comparativa frameworks
- `03_BACKEND/fastapi.md`, `express.md`, `tauri.md`
- `03_BACKEND/orms.md`, `databases.md`, `migrations.md`, `auth.md`
- `04_FRONTEND/README.md` comparativa frameworks
- `04_FRONTEND/react.md`, `vue.md`, `svelte.md`, `state-management.md`, `3d-threejs.md`, `desktop-electron.md`

---

## FASE 3 — Agentes + Memory (🔴 Pendiente)

**Dominios**: `06_AGENTS/`, `07_MEMORY/`

### 3A — Agentes (06_AGENTS/)
- Frameworks: LangGraph, CrewAI, AutoGen, Google ADK, OpenAI Agents SDK
- Patterns: ReAct, Plan-and-Execute, Reflexion, Tool Use
- Agent loops: single-agent vs multi-agent, hierarchical agents
- Function calling / tool use: OpenAI format, Anthropic format, Google format
- Custom agent implementations: 200 líneas de código sin frameworks
- MCP (Model Context Protocol): spec, servers, clients
- Handoffs, delegation, sub-agents

### 3B — Memory (07_MEMORY/)
- Vector stores: ChromaDB, Pinecone, Qdrant, Weaviate, Milvus
- Embeddings: sentence-transformers, OpenAI embeddings, Cohere embeddings
- RAG patterns: naive, hybrid search, reranking, HyDE
- Conversation memory: short-term (window), long-term (summary), episodic
- User context: preferencias, datos del usuario, project context
- Document indexing: chunking strategies, metadata

**Output esperado**:
- `06_AGENTS/README.md` comparativa frameworks
- `06_AGENTS/langgraph.md`, `crewai.md`, `autogen.md`, `custom-agent.md`, `mcp.md`
- `06_AGENTS/patterns.md` (ReAct, Plan-Execute, Reflexion)
- `07_MEMORY/README.md` comparativa vector stores
- `07_MEMORY/chromadb.md`, `pinecone.md`, `embeddings.md`, `rag-patterns.md`

---

## FASE 4 — Voice + Integrations (🔴 Pendiente)

**Dominios**: `08_VOICE/`, `09_INTEGRATIONS/`

### 4A — Voice (08_VOICE/)
- **TTS**: ElevenLabs, OpenAI TTS, Google Cloud TTS, Azure Speech, eSpeak NG, Coqui TTS
- **STT**: OpenAI Whisper, Deepgram, Azure Speech, Google STT
- **Wake word**: Porcupine, Snowboy (deprecated), custom
- **Voice pipelines**: realtime streaming, batching, buffering
- **Latency budgets**: <500ms target para conversación natural

### 4B — Integrations (09_INTEGRATIONS/)
- **Google**: Gmail REST API, Calendar API, OAuth2 + PKCE
- **Microsoft**: Graph API (Outlook, Calendar, OneDrive)
- **Telegram**: python-telegram-bot v21, polling vs webhook
- **Discord**: discord.py, discord.js
- **WhatsApp**: Business API, third-party (Baileys)
- **Slack**: Bolt SDK
- **Notion, Linear, Jira, GitHub** (productivity)

**Output esperado**:
- `08_VOICE/README.md` comparativa TTS/STT
- `08_VOICE/elevenlabs.md`, `openai-tts.md`, `whisper.md`, `voice-pipelines.md`
- `09_INTEGRATIONS/README.md` overview
- `09_INTEGRATIONS/google-oauth.md`, `gmail.md`, `calendar.md`, `telegram.md`

---

## FASE 5 — Automation + Security (🔴 Pendiente)

**Dominios**: `10_AUTOMATION/`, `11_SECURITY/`

### 5A — Automation (10_AUTOMATION/)
- Schedulers: APScheduler, Celery beat, cron, BullMQ
- Rules engines: JSON-based, visual (n8n), custom DSL
- Triggers: time-based, event-based, webhook-based, email-based
- Actions: telegram_message, email_summary, agent_task, chat_query
- Approval flows: human-in-the-loop, sensitive action gates

### 5B — Security (11_SECURITY/)
- API key management: env vars, encrypted DB, keyring, secrets managers
- Sandboxing: tool whitelists, path traversal prevention, command injection
- OAuth security: PKCE, state parameter, token refresh, scope minimization
- Prompt injection defenses: input validation, output filtering
- Data privacy: local-first patterns, encryption at rest

**Output esperado**:
- `10_AUTOMATION/README.md`, `apscheduler.md`, `rules-engines.md`
- `11_SECURITY/README.md`, `api-keys.md`, `sandboxing.md`, `oauth-security.md`, `prompt-injection.md`

---

## FASE 6 — Tooling + Deployment (🔴 Pendiente)

**Dominios**: `12_TOOLING/`, `13_DEPLOYMENT/`

### 6A — Tooling (12_TOOLING/)
- Execution engines: validación + ejecución controlada
- Tool managers: registro centralizado, whitelist por agente
- Validadores: path traversal, command injection, JSON schema
- Filesystem tools: read/write/list, sandboxed paths
- Shell tools: comando whitelist (python, git, npm, uvicorn)
- Git tools: status, log, diff, commit
- Email/Calendar tools: Gmail REST, Google Calendar

### 6B — Deployment (13_DEPLOYMENT/)
- **Electron packaging**: electron-builder, NSIS installers
- **Tauri packaging**: bundle creation, signing
- **Docker**: docker-compose para backend + DB
- **Auto-update**: electron-updater, squirrel
- **Code signing**: Windows certificates, EV certs
- **Distribution**: GitHub Releases, Microsoft Store, self-hosted
- **PWA**: manifest, service worker, offline-first
- **CI/CD**: GitHub Actions, GitLab CI

**Output esperado**:
- `12_TOOLING/README.md`, `execution-engine.md`, `tool-manager.md`
- `13_DEPLOYMENT/README.md`, `electron-builder.md`, `tauri-build.md`, `docker.md`, `pwa.md`

---

## FASE 7 — Best Practices + Known Pitfalls (🔴 Pendiente)

**Dominios**: `14_BEST_PRACTICES/`, `15_KNOWN_PITFALLS/`

### 7A — Best Practices (14_BEST_PRACTICES/)
- Arquitectura: cuándo FastAPI vs Tauri vs Electron
- Performance: streaming, batching, caching
- UX: feedback loops, error handling, voice latency
- Convenciones de código: estructura de carpetas, naming, schemas
- Testing: unit vs integration vs e2e
- Observability: logs, metrics, traces

### 7B — Known Pitfalls (15_KNOWN_PITFALLS/)
- Bugs históricos resueltos (para no repetirlos)
- Regresiones conocidas por framework/versión
- Incompatibilidades entre librerías
- MiniMax API changes (cambia endpoint cada X meses)
- ChromaDB + sentence-transformers (~1.5GB descarga)
- Electron + Node version compatibility
- React 18 strict mode double-render con streaming
- Pydantic v1 vs v2 incompatibilities

**Output esperado**:
- `14_BEST_PRACTICES/README.md`, `architecture.md`, `performance.md`, `ux.md`, `conventions.md`, `observability.md`
- `15_KNOWN_PITFALLS/README.md`, `streaming-issues.md`, `mini-max-api.md`, `chromadb-gotchas.md`, `electron-pitfalls.md`

---

## FASE 8 — SOPs + Mantenimiento (🔴 Pendiente, continuo)

**Dominio**: `16_SOPS/`

Procedimientos paso-a-paso, todos con la plantilla estándar:

- Añadir un proveedor IA nuevo
- Crear un tool nuevo para ToolManager
- Crear un agente nuevo
- Configurar OAuth para un proveedor nuevo
- Configurar un scheduler para automatizaciones
- Hacer deploy con Electron builder
- Configurar PWA service worker
- Migrar de SQLite a PostgreSQL
- Actualizar sentence-transformers
- Backup y restore de la BD
- Rotación de API keys
- Debug de streaming que se congela
- Debug de ChromaDB que no arranca
- Debug de OAuth que falla en refresh

**Tiempo estimado**: continuo a partir de la semana 3.

---

## Cómo ejecutar este roadmap

1. Mavis (orquestador) escoge la fase activa.
2. Descompone la fase en tareas concretas para Investigador y Escriba.
3. Investigador investiga → entrega a Escriba → validador de dominio revisa → Auditor firma.
4. Se cierra la fase y se actualiza `00_INDEX/status.md`.

---

*Roadmap v1.0 — 2026-06-30 (Fase 0 bootstrap).*
*Meta: mayor wiki existente sobre proyectos JARVIS-like en 15-30 días.*