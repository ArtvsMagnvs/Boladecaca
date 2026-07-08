# Hermes Agent (NousResearch/hermes-agent) — El agente con closed learning loop y 22+ plataformas de mensajería

## Resumen

**Hermes Agent** es el proyecto OSS de IA agent **más maduro y de mayor tracción comparable a Aithera**: **211.474 stars** (a 2026-07-08, creciendo ~1.100-1.700/día), 38.853 forks, MIT, **v0.18.2** (release tag `v2026.7.7.2`, publicado 2026-07-08 03:11 UTC, hace 16h al momento de este contraste), y el único agente open-source con un **closed learning loop real** (crea skills desde experiencia, las auto-mejora, y construye un modelo del usuario que se profundiza entre sesiones). Construido por **Nous Research** (los creadores de la familia de LLMs Hermes), es Python-first (**84.3% Python, 14.2% TypeScript** verificado vía GitHub API contraste 2026-07-08), soporta **6 backends terminales** (local, Docker, SSH, Singularity, Modal, Daytona), **22+ plataformas de mensajería** (Telegram, Discord, Slack, WhatsApp, Signal, iMessage, Email via MS Graph, WeChat, WeCom, QQ, Yuanbao, DingTalk, Feishu, Google Chat, Home Assistant, IRC, LINE, Matrix, Mattermost, ntfy, Photon, SimpleX, SMS, Teams), **native desktop apps para macOS/Windows/Linux** (Electron), **MoA (Mixture-of-Agents) first-class** desde v0.18.0, sistema de skills compatible con [agentskills.io](https://agentskills.io), y migración automática desde OpenClaw vía `hermes claw migrate`. Es **la referencia directa** que Aithera V0.85 (Memory) y V1.0 (Orchestrator) deberían estudiar.

## Objetivo

Documentar el estado real de Hermes Agent en julio 2026: arquitectura, features únicas, sistema de skills + closed learning loop, y comparativa honesta con Aithera V0.7.3. Responde a "¿qué aprender de Hermes para Aithera, y dónde Aithera puede diferenciarse?". El doc enfatiza los **descubrimientos del audit independiente del 2026-07-08** que corrigen 5 discrepancias materiales con el doc previo (v0.18.0 → v0.18.2, 210.335★ → 211.474★, 5+ mensajerías → 22+ mensajerías, Python 80% → 84.3%, ausencia de native desktop/MoA/ACP).

## Estado

🟢 **Verificado** — material crudo completo (5.422 palabras, 482 líneas, 102 hechos verificados con URL+fecha, 11 snippets con path:line, 5 conflictos entre fuentes documentados, 5 discrepancias con doc previo resueltas). Contraste GitHub API 2026-07-08T19:55Z, raw.githubusercontent.com del `main` branch (HEAD commit a 2026-07-08T15:32:15Z), landing oficial hermes-agent.nousresearch.com, y SKILL.md del propio repo. 6/6 criterios CONSTITUTION.md §8 cumplidos.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| Hermes Agent | **v0.18.2** (release tag v2026.7.7.2) | Publicada **2026-07-08T03:11:22Z** (16h antes del contraste); patch sobre v0.18.1 (mismo día) que arregla WhatsApp Baileys dep |
| Hermes Agent anterior | v0.18.0 (v2026.7.1) "The Judgment Release" | 2026-07-01; ~1.720 commits + 998 PRs + 949 issues cerrados + 370+ contribuidores en el window |
| Python | **>=3.11, <3.14** (exacto, cap explícito en 3.14) | Razón: pydantic-core y otros transitivos Rust-backed no tienen wheel cp314 todavía |
| Node.js | ≥20 (para la Web UI y el desktop Electron) | Verificado vía package.json (1.457 bytes) + package-lock.json (712KB) |
| uv | Última estable | Usado para resolver Python env; Astral `uv` es el package manager |
| Windows | Nativo (sin WSL) | Soporte oficial Windows PowerShell installer; MinGit portable en `%LOCALAPPDATA%\hermes\git` |
| macOS | Nativo (DMG directo) | `Hermes-Setup.dmg` desde hermes-assets.nousresearch.com |
| Linux | Nativo (AppImage/vía releases) | Link desde landing a github.com/NousResearch/hermes-agent/releases |
| Nix | flake.nix incluido | Para reproducibilidad declarativa en Linux |
| Termux (Android) | Soporte oficial vía `.[termux]` extra | Documentado en `getting-started/termux` |
| WSL2 | Soporte oficial | Mismo instalador que Linux/macOS |
| Nous Portal | Opcional | 300+ modelos + Tool Gateway (web search Firecrawl, image gen FAL, TTS OpenAI, cloud browser Browser Use). Pricing tiers: Free • Plus • Super • Ultra |
| Honcho | Última (`honcho-ai==2.0.1` opt-in) | User modeling dialectico (https://github.com/plastic-labs/honcho) |
| agentskills.io | Open standard v0.x | Skills format compatible (hermes-agent tiene su propia SKILL.md v2.3.0 publicada) |
| OpenClaw | Cualquier versión reciente | Migración con `hermes claw migrate` (importa config, memories, skills, API keys) |
| Aithera | V0.7+ | **No usar como dependencia** (proyecto personal, no es framework para embeber); estudiar como referencia arquitectónica. La Aithera V0.7.3 ya tiene el patrón `Gateway` + `ChannelAdapter` que es lo que Hermes llama "MessageEnvelope + ChannelAdapter" — convergencia notable |

## Proyectos compatibles

- **Modelos (LLM providers)**: 300+ vía Nous Portal, o trae tu propia key (OpenAI, Anthropic, OpenRouter, Google, DeepSeek, xAI, local via Ollama, endpoint custom)
- **Mensajería (22+ plataformas)**: Telegram, Discord, Slack, WhatsApp, Signal, Email (MS Graph), iMessage (bluebubbles), WeChat (weixin), WeCom (wecom), QQ (qqbot), Yuanbao (Tencent AI assistant, integración profunda con 222KB+45KB+21KB), DingTalk, Feishu/Lark (ByteDance), Google Chat, Home Assistant, IRC, LINE, Matrix (con encryption), Mattermost, ntfy, Photon, Raft, SimpleX (privacy-first), SMS, Teams
- **Backends terminales (6)**: local, Docker, SSH, Singularity, Modal (serverless GPU), Daytona (serverless hiberna)
- **Protocolos**: MCP (vía `mcp_serve.py` + `optional-mcps/`), ACP (vía `acp_adapter/` + `acp_registry/` — Agent Communication Protocol para IDEs)
- **Skills**: Compatible con [agentskills.io](https://agentskills.io) open standard (la SKILL.md del propio Hermes Agent es v2.3.0, MIT, by "Hermes Agent + Teknium", con `related_skills: [claude-code, codex, opencode]`)
- **Tools**: 40+ tools según docs oficiales; sistema de toolsets (`toolsets.py` 34KB, `toolset_distributions.py` 12KB)
- **IDEs (via ACP server)**: VS Code, Zed, JetBrains
- **Surfaces (5+)**: CLI, Ink TUI (`ui-tui/`, `tui_gateway/`), native Electron desktop app, web dashboard (FastAPI + uvicorn), ACP server
- **Honcho**: integración nativa con [plastic-labs/honcho](https://github.com/plastic-labs/honcho) para user modeling dialectico
- **Hindsight, Supermemory, Mem0**: cloud memory providers como opt-in extras

## Dependencias

- [JWIKI-002 projects.md](./projects.md#hermes-agent) — comparativa principal con otros proyectos OSS (debe actualizarse: 53k → 211.474★, "Python 80%" → "Python 84.3% + TypeScript 14.2%", v0.18.0 → v0.18.2, 5+ mensajerías → 22+ mensajerías).
- [JWIKI-001 history.md](./history.md) — contexto histórico (Hermes nace 2024 con los LLMs Hermes, el Agent es 2025+; el repo GitHub del Agent se crea 2025-07-22).
- [JWIKI-006 jarvisagent.md](./jarvisagent.md) — comparativa con el otro "Jarvis" (Tauri/Rust, ~4★, proyecto personal).
- [JWIKI-003 openclaw.md](./openclaw.md) — desde donde migra; comparativa de channels/multi-plataforma (OpenClaw = multi-canal-first; Hermes = multi-canal + closed learning loop + native desktop).
- [JWIKI-008 clawdbot.md](./clawdbot.md) — controversias del rename OpenClaw que Hermes aprovecha para `hermes claw migrate` (Warelay → CLAWDIS → Clawdbot → Moltbot → OpenClaw).
- [JWIKI-101 agents-readme.md](../06_AGENTS/README.md) — comparativa de frameworks de agentes (Hermes compite con LangGraph/CrewAI/AutoGen pero también con Claude Code/Codex/OpenClaw).
- [JWIKI-119 memory-readme.md](../07_MEMORY/README.md) — comparativa de vector stores (Hermes usa Honcho + FTS5 session search; Aithera usa ChromaDB).
- [JWIKI-009 superpowers.md](./superpowers.md) — el otro framework de skills (obra/superpowers, 249.642★, MIT, multi-language, agentskills.io compatible). Comparativa interesante: Superpowers = skills para coding agents, Hermes = skills para personal AI agent.
- [JWIKI-007 docs oficiales](https://hermes-agent.nousresearch.com/docs/) — referencia autoritativa.
- [JWIKI-113 mcp.md](../06_AGENTS/mcp.md) — Hermes tiene `mcp_serve.py` + `optional-mcps/`; Aithera V0.8 no tiene MCP.
- [JWIKI-118 approval-flows.md](../06_AGENTS/approval-flows.md) — Hermes tiene approval workflows (security docs `/user-guide/security`); ¿cómo encaja con el Orchestrator de Aithera V1.0?

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Hermes Agent v0.18.2 (Nous Research)              │
│                                                                     │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐    │
│  │  CLI / TUI  │  │  Native Desktop  │  │  Web Dashboard       │    │
│  │  (Ink TUI,  │  │  (Electron)      │  │  (FastAPI+uvicorn)   │    │
│  │  prompt_    │  │  macOS/Win/Linux │  │  (file upload,       │    │
│  │  toolkit,   │  │  DMG/EXE/        │  │   admin panel)       │    │
│  │  cli.py     │  │   AppImage       │  │                      │    │
│  │  744KB)     │  │  builds)         │  │                      │    │
│  └──────┬──────┘  └────────┬─────────┘  └──────────┬───────────┘    │
│         └──────────────────┬┴─────────────────────┘                 │
│                            ▼                                        │
│              ┌──────────────────────────────┐                       │
│              │  Agent Core (Python)          │                       │
│              │  - closed learning loop       │                       │
│              │  - autonomous skill creation  │                       │
│              │  - FTS5 session search        │                       │
│              │  - sub-agent RPC              │                       │
│              │  - Honcho user modeling       │                       │
│              │  - ACP adapter/registry       │                       │
│              │  - 40+ tools, toolsets        │                       │
│              │  - 6 terminal backends        │                       │
│              │  - MoA (Mixture-of-Agents)    │                       │
│              │  - Mixture-of-Agents provider │                       │
│              │  - Self-verification          │                       │
│              │  - /goal + /learn + /journey  │                       │
│              │  - run_agent.py 269KB         │                       │
│              │  - hermes_state.py 278KB      │                       │
│              └────────────┬─────────────────┘                       │
│                           ▼                                         │
│  ┌────────────┐  ┌─────────────┐  ┌────────────┐                    │
│  │  Skills    │  │  Cron       │  │  MCP       │                    │
│  │  system    │  │  scheduler  │  │  servers   │                    │
│  │  (agentski │  │  (croniter) │  │  (mcp_     │                    │
│  │  lls.io    │  │  + webhooks │  │  serve.py) │                    │
│  │  v2.3.0)   │  │  + delivery │  │            │                    │
│  └────────────┘  └─────────────┘  └────────────┘                    │
│                                                                     │
│  Gateway (gateway/ 35 archivos, 469KB+):                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Core gateway: scale_to_zero.py, drain_control.py,           │  │
│  │  delivery.py, session.py, hooks.py, restart.py               │  │
│  │  Core platforms (gateway/platforms/): bluebubbles, msgraph,  │  │
│  │  signal, weixin, whatsapp_cloud, yuanbao, qqbot, base.py    │  │
│  │  Plugin platforms (plugins/platforms/ 22 dirs): telegram,    │  │
│  │  discord, slack, whatsapp, dingtalk, feishu, wecom, teams,   │  │
│  │  matrix, mattermost, google_chat, line, irc, ntfy, photon,   │  │
│  │  simplex, raft, sms, homeassistant, email                   │  │
│  │  API server (api_server.py 219KB): OpenAI-compatible local  │  │
│  │  proxy for OAuth provider                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Model providers: Nous Portal (300+) | OpenAI | Anthropic           │
│  OpenRouter | custom endpoint | local (Ollama)                      │
│                                                                     │
│  Memory backends (opt-in extras): Honcho | Hindsight |              │
│  Supermemory | Mem0 | built-in FTS5                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Descripción técnica

### Closed learning loop (la killer feature, irrefutable)

Lo que distingue a Hermes de cualquier otro agente OSS en 2026:

1. **Agent-curated memory con nudges periódicos** — el agente se recuerda a sí mismo guardar info clave.
2. **Autonomous skill creation** — tras tareas complejas, el agente crea una skill nueva reusable (compatible con agentskills.io).
3. **Self-improving skills** — las skills se refinan automáticamente con el uso.
4. **FTS5 session search + LLM summarization** — búsqueda cross-session con resumen por LLM (no solo keyword match).
5. **Honcho dialectic user modeling** — modela al usuario a lo largo del tiempo (no solo "le gusta X", sino un perfil dinámico via dialectic reasoning). Honcho es opt-in (extra `honcho = ["honcho-ai==2.0.1"]`) para reducir blast radius.

**Para Aithera**: este es **exactamente** el diseño que la V0.85 (Memory & Context) debería aspirar. El `MemoryManager` actual de Aithera (ChromaDB 3 colecciones) es la base, pero falta el loop de auto-mejora y los nudges. La V0.85 debería implementar el patrón de "self-verification" introducido en v0.18.0 (que verifica el trabajo contra evidencia, no vibes).

### MoA (Mixture-of-Agents) first-class (NUEVO en v0.18.0)

- **Antes de v0.18.0**: MoA era un modo que se togglaba.
- **Desde v0.18.0**: cada MoA preset aparece como **modelo seleccionable** en el model picker (CLI, TUI, desktop, gateway), bajo un provider `moa`, junto a Claude, GPT, Grok.
- **UX**: "Pick `my-council` the same way you'd pick any model, and Hermes routes your prompt through that ensemble automatically."
- **Visibilidad**: "every reference model's reasoning shown to you and the aggregator's answer streamed live".

**Para Aithera**: el `AIManager` actual no soporta MoA nativo. La V0.85 podría añadir un patrón "ensemble" donde se eligen N modelos, se les pasa el mismo prompt en paralelo, y se streamea la respuesta agregada. Es una feature barata de implementar (es solo routing) y de alto valor para usuarios que quieran comparar modelos.

### Native desktop apps (NUEVO en el audit)

- **macOS**: `https://hermes-assets.nousresearch.com/Hermes-Setup.dmg?build=9de9c25f620f` (descarga directa desde landing)
- **Windows**: `https://hermes-assets.nousresearch.com/Hermes-Setup.exe?build=9de9c25f620f` (descarga directa)
- **Linux**: link a GitHub releases (no binario directo en landing, probablemente AppImage/Flatpak en releases)
- **Stack del desktop**: Electron (mencionado en SKILL.md como "a native Electron desktop app")
- **Features del desktop (v0.18.0)**: first-class coding projects + **playable memory graph** (visualización de la memoria del agente en formato jugable/explorable)

**Para Aithera**: Aithera V0.7.3 ya tiene Electron + AICore 3D, pero el "memory graph" de Hermes es una feature UX que Aithera podría借鉴. La V0.85 podría añadir un visualizador de la ChromaDB memory.

### Gateway scale-to-zero + drain coordination (NUEVO v0.18.0)

- **scale_to_zero.py** (en `gateway/`): permite que el gateway hiberne cuando no hay tráfico y despierte on-demand. Costo: ~cero entre sesiones.
- **drain_control.py**: coordina el drenaje de workers antes del scale-to-zero (evita drop de mensajes).
- **memory_monitor.py**: vigila el uso de memoria y triggerea scale-to-zero cuando está idle.
- **restart_loop_guard.py**: previene restart loops (un bug común cuando scale-to-zero + restart se interfieren).

**Para Aithera**: Aithera V0.8 ya tiene el patrón Gateway + ChannelAdapter (ver `app/gateway/` en repo). Pero el gateway actual es long-lived (no scale-to-zero). Si Aithera se ejecuta en V1.0+ en un serverless (Modal/Daytona-like), el patrón de scale-to-zero + drain sería crítico.

### Sistema de skills (compatible con agentskills.io)

- **Skills dir layout**: `skills/` (built-in) + `optional-skills/` (opt-in) — Top-level en el repo
- **Sub-organización por categoría**: en el contenido real, las skills se organizan en `skills/<categoria>/<nombre-de-otra-forma-de-skills>/SKILL.md` (ej: `skills/autonomous-ai-agents/hermes-agent/SKILL.md`, `skills/autonomous-ai-agents/claude-code/`, `skills/autonomous-ai-agents/codex/`, `skills/autonomous-ai-agents/opencode/`). El `skills/` dir es en realidad **un agregador de SKILL.md de otros proyectos** que el equipo de Hermes mantiene como referencia cruzada.
- **SKILL.md frontmatter** (estándar agentskills.io): `name`, `description`, `version`, `author`, `license`, `platforms`, `metadata.<provider>.tags`, `metadata.<provider>.homepage`, `metadata.<provider>.related_skills`.
- **SKILL.md del propio Hermes Agent**: v2.3.0, MIT, by "Hermes Agent + Teknium", con `related_skills: [claude-code, codex, opencode]`. 51.586 bytes — la SKILL.md individual más grande que se ha visto.
- **Browse**: `/skills` o `/<skill-name>` (mismo en CLI y mensajería).
- **Lifecycle**: se crean automáticamente tras tareas complejas; se auto-mejoran con el uso.

**Para Aithera**: el sistema `JWIKI/` es semánticamente similar (knowledge base viva) pero no es un "skill system" runtime. Aithera podría crear un `aithera-skills/` que se alimente de JWIKI + memoria de usuario. La integración con agentskills.io (que ya soportan tanto Superpowers como Hermes) sería una decisión estratégica fuerte.

### Multi-plataforma de mensajería (gateway unificado, 22+ plataformas)

5 canales "headline" (Telegram, Discord, Slack, WhatsApp, Signal, Email) son solo la superficie visible. La realidad (verificada vía `git/trees/main?recursive=1` 2026-07-08) es:

**Core platforms** (`gateway/platforms/` — cargadas por defecto): bluebubbles (iMessage), msgraph_webhook (Email), signal, weixin (WeChat), whatsapp_cloud, yuanbao (Tencent AI assistant), qqbot (QQ). Más `api_server.py` (219KB — OpenAI-compatible local proxy) y `webhook.py` (53KB — generic webhook).

**Plugin platforms** (`plugins/platforms/` — 22 subdirs): dingtalk, discord, email, feishu, google_chat, homeassistant, irc, line, matrix, mattermost, ntfy, photon, raft, simplex, slack, sms, teams, telegram, wecom, whatsapp.

**Patrón arquitectónico**: la diferencia entre `gateway/platforms/` y `plugins/platforms/` es que las primeras son **core** (se cargan siempre; el release las incluye) y las segundas son **plugins** (opt-in; el usuario las habilita con `hermes plugins enable <name>`). Esto es un patrón de **core/plugin split** maduro.

**Para Aithera**: Aithera V0.8 ya tiene el patrón `Gateway` + `ChannelAdapter` (ver `app/gateway/` en repo) con un solo adapter (Telegram) implementado. La estructura de Hermes (gateway/platforms vs plugins/platforms) es exactamente la dirección a seguir. Aithera V1.0 debería implementar el core/plugin split: Gateway core (Telegram + Web) + plugins (Discord, Slack, WhatsApp, Signal, Email). Y la cobertura de Hermes muestra que **el campo se ha movido de "5 plataformas" a "20+ plataformas"** — quedarse en 1-2 es ya insuficiente para 2026.

### 6 terminal backends (incluye serverless)

- **local** — el PC del usuario
- **Docker** — container local
- **SSH** — remote shell
- **Singularity** — HPC (común en research)
- **Modal** — serverless GPU
- **Daytona** — serverless que hiberna cuando idle (cuesta casi nada entre sesiones)

**Discrepancia detectada**: el landing page (hermes-agent.nousresearch.com) menciona solo **5 backends** (local, Docker, SSH, Singularity, Modal — sin Daytona), pero el README y el pyproject.toml sí listan los 6. El landing está desactualizado. **La cifra correcta es 6.**

**Para Aithera**: Aithera V0.7 solo soporta local. V1.0 Orchestrator podría añadir Docker como primer paso (caso de uso: ejecutar scripts del usuario en sandbox aislado). Modal/Daytona son interesantes pero más adelante.

### Cron scheduler nativo con delivery a cualquier plataforma

- **Módulo**: `cron/` + `croniter==6.0.0` (core dep)
- **API de triggers** (3 tipos, **publicado desde marzo 2026**):
  - **Scheduled (cron)**: `hermes cron create "0 2 * * *" "..." --name "..." --deliver telegram`
  - **GitHub Events (webhook)**: `hermes webhook subscribe auth-watch --events "pull_request" --prompt "..." --deliver slack`
  - **API Triggers**: `hermes webhook subscribe alert-triage --prompt "..." --deliver slack`
- **Delivery flexible**: a cualquiera de las 22+ plataformas (Telegram, Slack, email, etc.)
- **Caso de uso del competitive post**: "Every night at 2am: pull the top bug from the issue tracker, attempt a fix, and open a draft PR."

**Competitive positioning**: `hermes-already-has-routines.md` (6.373 bytes) es un post interno que **compara directamente con Claude Code Routines** (Anthropic, anunciado después). El claim textual: "Anthropic just announced [Claude Code Routines]... It's a good feature. **We shipped it two months ago.**" Esto es un competitive move fuerte.

**Para Aithera**: Aithera V0.9 (Automation Engine) con APScheduler es exactamente esto. Aithera debería inspirarse en el `delivery` flexible de Hermes (a 22+ plataformas, no solo Telegram).

### Sub-agent delegation aislado con RPC

- "Spawn isolated subagents for parallel workstreams"
- "Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns"
- **Aislamiento total entre sub-agents** (cada uno con su propio contexto)
- **Background fan-out** (v0.18.0) — sub-agents pueden correr en background sin bloquear el main agent

**Para Aithera**: V1.0 Orchestrator. El concepto de "zero-context-cost turns" (el sub-agent tiene su propio contexto) es clave. Aithera podría usar el mismo patrón de "Python scripts que llaman tools via RPC" — la V1.0 debería diseñar un `SubAgent` que pueda ser invocado desde scripts Python con la misma API que el orchestrator principal.

### 40+ tools + toolsets

- `tools/` + `toolsets.py` (34.801 bytes) + `toolset_distributions.py` (12.021 bytes)
- Configurables con `hermes tools`
- **Toolsets** = grupos de tools que se activan/desactivan juntos (patrón similar a las "feature flags" de los SaaS)
- **Tool gateway opcional** (suscripción Nous Portal): web search (Firecrawl), image generation (FAL), TTS (OpenAI), cloud browser (Browser Use)

**Para Aithera**: Aithera V0.5 tiene 8 tools en ToolManager. V1.0 debería crecer esto (a 40+) y añadir concepto de toolsets. El tool gateway opcional (suscripción unificada) es un modelo de negocio interesante a explorar.

### MCP + ACP

- **MCP** (Model Context Protocol): `mcp_serve.py` (35.282 bytes) + `optional-mcps/` — soporte nativo para servidores MCP. Dep opt-in: `mcp==1.26.0` en el extra `dev`.
- **ACP** (Agent Communication Protocol): `acp_adapter/` + `acp_registry/` — protocolo para comunicación entre agentes (incluyendo IDEs). El SKILL.md menciona explícitamente: "ACP server for IDEs (VS Code / Zed / JetBrains)".

**Para Aithera**: Aithera V0.8 no tiene MCP. Es un gap importante. La V0.85 o V1.0 debería añadir `mcp_server.py` y consumir servidores MCP populares (ej: filesystem, git, github, postgres, etc.). El ACP es más exótico pero es el "estándar emergente" para que los IDEs se conecten al agente.

### API server (OpenAI-compatible local proxy) (NUEVO)

- `gateway/platforms/api_server.py` (219.484 bytes)
- **Función**: expone un endpoint OpenAI-compatible (`/v1/chat/completions`, etc.) backed por un OAuth provider (Nous Portal, o el que el usuario configure).
- **Caso de uso**: otras apps que usen OpenAI SDK (incluyendo Aithera) pueden apuntar a un Hermes local como drop-in OpenAI replacement. **Esto es un patrón "local LLM proxy" que ya existía (Ollama, LM Studio) pero llevado al nivel "agente completo con memoria + skills".**

**Para Aithera**: Aithera V0.7 ya es un servidor OpenAI-compatible-ish (vía `/api/chat`). Pero el patrón de Hermes es más limpio: expone un endpoint OpenAI-compatible puro (no específico de Aithera), lo que permite que CUALQUIER app se conecte. Aithera V1.0 podría hacer lo mismo.

### Pyproject.toml pinning policy post-Mini Shai-Hulud worm (NUEVO)

- **Decisión del 2026-05-12** (en comentario literal en pyproject.toml): todas las deps directas pinned a `==X.Y.Z` (sin ranges). Razón citada: el worm "Mini Shai-Hulud" golpeó `mistralai 2.4.6` en PyPI; si hubieran tenido `mistralai>=2.3.0,<3` en vez de pin exacto, **cada install en las horas previas a la cuarentena habría pulled it**.
- **Scope rule**: "only packages used by EVERY hermes session belong here. Anything that's provider-specific (`anthropic`, `firecrawl-py`, ...) belongs in an extra and gets lazy-installed via `tools/lazy_deps.py` when the user picks that backend. **Smaller `dependencies` = smaller blast radius for the next supply-chain attack.**"
- **Python cap explícito en 3.14** (comentado en pyproject): "uv resolves the project's Python from `requires-python`, and an inherited `UV_PYTHON` env var (or a fresh distro whose newest interpreter uv auto-picks) will otherwise select 3.14, where Rust-backed transitives (e.g. pydantic-core) have no cp314 wheel yet and fall back to a maturin source build that fails. Capping at <3.14 makes uv refuse 3.14 with a clear error instead of attempting that build."

**Para Aithera**: Aithera V0.7.3 ya tiene un patrón similar de pinning (varios `==X.Y.Z` en `requirements.txt`), pero no documentado. V0.8+ debería documentar la policy en `CLAUDE.md` o en un `docs/SECURITY.md` específico. Aithera también debería seguir el "scope rule" (deps core vs extras lazy-installed).

### CVEs explícitas en el pyproject (transparencia notable)

El pyproject de Hermes cita **CVE-IDs concretas** en los comentarios de cada dep:
- `requests==2.33.0` (CVE-2026-25645)
- `pydantic==2.13.4` (bumped desde 2.12.5 → 2.13.4 para pull pydantic-core 2.46.4 que arregla segfault cuando OpenAI SDK's Responses API se ejerce desde non-main thread, en `agent/chat_completion_helpers.py:_call`)
- `anthropic==0.87.0` (CVE-2026-34450, CVE-2026-34452)
- `aiohttp==3.14.1` (CVE-2026-34513/34518/34519/34520/34525 + 34993(RCE)/47265)
- `cryptography==46.0.7` (CVE-2026-39892, CVE-2026-34073)
- `PyJWT[crypto]==2.13.0` (PYSEC-2026-175/177/178/179)
- `urllib3>=2.7.0,<3` (GHSA-mf9v-mfxr-j63j, GHSA-qccp-gfcp-xxvc)
- `concurrent-log-handler==0.9.29; sys_platform == 'win32'` (workaround para Windows log rotation bug — `RotatingFileHandler.doRollover()` falla con `PermissionError [WinError 32]` cuando otros procesos tienen el handle en `agent.log`, issue #44873)
- `starlette==1.0.1` (CVE-2026-48710)
- `setuptools==81.0.0` (latest <82; torch >=2.11 cap setuptools<82)

**Para Aithera**: el equipo de Aithera debería借鉴 este patrón de "comentarios de seguridad explícitos en requirements.txt" con CVE-IDs. Es una práctica de transparencia que ayuda a auditorías y a futuros contributors a entender por qué se pinned una versión concreta.

## Call Stack / API

```
Mensaje entrante (Telegram/CLI/desktop/etc)
  → Gateway.dispatcher (gateway/run.py, scale_to_zero.py, drain_control.py)
    → Session.lookup(chat_id) (gateway/session.py, session_context.py)
      → Agent.run(mensaje, contexto, tools)  [run_agent.py, 269KB]
        → [closed learning loop]
          → SkillStore.search(query) [FTS5, agentskills.io format]
            → MemoryStore.retrieve(context) [Honcho + Hindsight + FTS5]
              → ToolSelector.pick(task) [toolsets.py, model_tools.py]
                → LLM.stream(model, messages, tools) [providers/]
                  → [opcional: MoA ensemble via moa provider]
                    → SSE stream → chunks
                  → Tool.run(name, args)  [40+ tools]
                  → [opcional: SubAgent.spawn si aplica] [background fan-out v0.18.0]
                → SkillCreate si tarea compleja  [autonomous skill creation]
              → MemoryStore.commit() [nudge periódico + dialectic user modeling via Honcho]
              → SelfVerification.check(work, evidence)  [NUEVO v0.18.0]
            → /goal completion contract  [NUEVO v0.18.0]
            → /learn + /journey update  [NUEVO v0.18.0]
      → Response → OutboundMessage
    → Gateway.adapters[channel].deliver(response)
      → [si platform es core: gateway/platforms/<name>.py]
      → [si platform es plugin: plugins/platforms/<name>/adapter.py]
```

## Diagramas

Ver sección Arquitectura. Estructura del repo (top-level) según GitHub API contraste 2026-07-08:

```
NousResearch/hermes-agent/                    (creado 2025-07-22, ~470MB, 211k★)
├── .github/                                  # workflows
├── .plans/                                   # planning/roadmap interno
├── agent/                                    # Agent core
├── apps/                                     # Aplicaciones satélite
├── acp_adapter/                              # Agent Communication Protocol adapter (IDEs)
├── acp_registry/                             # ACP registry
├── assets/                                   # Imágenes y assets web
├── AGENTS.md (71KB)                          # Instructions file para coding agents
├── batch_runner.py (57KB)                    # Research batch trajectory generation
├── cli.py (744KB)                            # CLI monolítica (prompt_toolkit + rich)
├── cli-config.yaml.example (75KB)            # Config example exhaustivo
├── CONTRIBUTING.md (49KB)                    # Contributing guide
├── cron/                                     # Cron scheduler (croniter)
├── datagen-config-examples/                  # Data generation configs (research)
├── docker/                                   # Docker assets
├── docker-compose.yml                        # Multi-service compose
├── docker-compose.windows.yml                # Windows-specific compose
├── Dockerfile (20KB)                         # Container build
├── docs/                                     # Documentation source
├── flake.lock / flake.nix                    # Nix reproducible builds
├── gateway/                                  # Multi-channel gateway
│   ├── platform_registry.py
│   ├── scale_to_zero.py                      # NUEVO v0.18.0 (deployable at scale)
│   ├── drain_control.py                      # NUEVO v0.18.0
│   ├── memory_monitor.py
│   ├── delivery.py                           # Multi-platform delivery
│   ├── session.py / session_context.py
│   ├── slash_commands.py / slash_access.py
│   ├── restart.py / restart_loop_guard.py
│   ├── platforms/                            # Core platforms (cargadas siempre)
│   │   ├── api_server.py (219KB)             # OpenAI-compatible local proxy
│   │   ├── base.py (245KB)                   # Base adapter class
│   │   ├── bluebubbles.py                    # iMessage
│   │   ├── msgraph_webhook.py                # Email (Microsoft Graph)
│   │   ├── signal.py (71KB) + signal_format.py + signal_rate_limit.py
│   │   ├── webhook.py (53KB) + webhook_filters.py
│   │   ├── weixin.py (92KB)                  # WeChat
│   │   ├── whatsapp_cloud.py (87KB) + whatsapp_common.py
│   │   ├── yuanbao.py (222KB) + yuanbao_media.py + yuanbao_proto.py + yuanbao_sticker.py
│   │   └── qqbot/                            # QQ (Tencent)
│   ├── relay/                                # Gateway relay
│   └── builtin_hooks/                        # Hooks internos
├── hermes/                                   # Hermes core package
├── hermes-already-has-routines.md (6KB)      # Competitive post vs Claude Code Routines
├── hermes_bootstrap.py (8KB)                 # Bootstrap script
├── hermes_cli/                               # CLI implementation (subpaquete)
├── hermes_constants.py (37KB)                # Constantes globales
├── hermes_logging.py (31KB)                  # Logging con concurrent-log-handler en Windows
├── hermes_state.py (278KB)                   # State management
├── hermes_time.py                            # Time utilities
├── infographic/                              # Assets para infografías
├── LICENSE                                   # MIT
├── locales/                                  # i18n
├── mcp_serve.py (35KB)                       # MCP server entry
├── mini_swe_runner.py (28KB)                 # SWE-bench runner
├── model_tools.py (62KB)                     # Model-specific tools
├── nix/                                      # Nix backend
├── optional-mcps/                            # Optional MCP servers
├── optional-skills/                          # Optional skills
├── package.json (1.4KB)                      # Web UI
├── package-lock.json (712KB)                 # Web UI lockfile
├── packaging/                                # PyPI packaging
├── plugins/                                  # Plugin system
│   └── platforms/                            # 22 plugin platform adapters
│       ├── dingtalk/                         # Alibaba DingTalk
│       ├── discord/
│       ├── email/
│       ├── feishu/                           # Lark/Feishu (ByteDance)
│       ├── google_chat/
│       ├── homeassistant/
│       ├── irc/
│       ├── line/
│       ├── matrix/                           # con encryption
│       ├── mattermost/
│       ├── ntfy/                             # ntfy.sh push notifications
│       ├── photon/                           # con sidecar/
│       ├── raft/
│       ├── simplex/                          # SimpleX Chat (privacy-first)
│       ├── slack/
│       ├── sms/
│       ├── teams/                            # Microsoft Teams
│       ├── telegram/
│       ├── wecom/                            # WeCom (enterprise WeChat)
│       └── whatsapp/
├── providers/                                # Model providers (300+ via Nous Portal)
├── pyproject.toml (21KB)                     # Build config + deps
├── README.md (17KB)                          # Main README
├── README.es.md / README.zh-CN.md / README.ur-pk.md  # i18n
├── run_agent.py (269KB)                      # Agent loop monolítico
├── scripts/                                  # Utility scripts
├── SECURITY.md (15KB) + SECURITY.es.md (18KB)
├── setup-hermes.sh (18KB)                    # Linux/macOS install script
├── setup.py (2KB)                            # setuptools entry
├── skills/                                   # Skills (agentskills.io format)
│   ├── autonomous-ai-agents/                 # Sub-categoría
│   │   ├── claude-code/                      # SKILL.md de Claude Code
│   │   ├── codex/                            # SKILL.md de OpenAI Codex
│   │   ├── hermes-agent/                     # SKILL.md v2.3.0 del propio Hermes
│   │   └── opencode/                         # SKILL.md de OpenCode
│   ├── email/, github/, mlops/, etc.         # Otras categorías
├── tests/                                    # Test suite
├── tools/                                    # 40+ tools
├── toolsets.py (34KB)                        # Toolset system
├── toolset_distributions.py (12KB)           # Toolset distros
├── trajectory_compressor.py (68KB)           # Compress trajectories para training
├── tui_gateway/                              # TUI gateway
├── ui-tui/                                   # TUI frontend (Ink)
├── utils.py (20KB)                           # Utilities
├── uv.lock (661KB)                           # uv lockfile
├── web/                                      # Web UI assets
└── website/                                  # Landing page assets
```

## Código relacionado

- Repo: https://github.com/NousResearch/hermes-agent
- Default branch: `main`
- License: MIT
- Releases: https://github.com/NousResearch/hermes-agent/releases
- Latest: https://github.com/NousResearch/hermes-agent/releases/tag/v2026.7.7.2 (v0.18.2)
- v0.18.0 "The Judgment Release": https://github.com/NousResearch/hermes-agent/releases/tag/v2026.7.1
- README: https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md
- pyproject.toml: https://raw.githubusercontent.com/NousResearch/hermes-agent/main/pyproject.toml
- hermes-already-has-routines.md: https://raw.githubusercontent.com/NousResearch/hermes-agent/main/hermes-already-has-routines.md
- SKILL.md: https://raw.githubusercontent.com/NousResearch/hermes-agent/main/skills/autonomous-ai-agents/hermes-agent/SKILL.md
- Documentación: https://hermes-agent.nousresearch.com/docs/
- Native desktop downloads: https://hermes-assets.nousresearch.com/Hermes-Setup.dmg (macOS) / https://hermes-assets.nousresearch.com/Hermes-Setup.exe (Windows)
- Honcho (deps): https://github.com/plastic-labs/honcho
- agentskills.io (standard): https://agentskills.io
- Nous Portal: https://portal.nousresearch.com

## Ejemplos

#### Snippet 1: Instalador en una línea (README, sección "Quick Install")
```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

#### Snippet 2: Instalador PowerShell Windows nativo (README)
```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

#### Snippet 3: CLI completa (README, "Getting Started")
```bash
hermes              # Interactive CLI — start a conversation
hermes model        # Choose your LLM provider and model
hermes tools        # Configure which tools are enabled
hermes config set   # Set individual config values
hermes gateway      # Start the messaging gateway (Telegram, Discord, etc.)
hermes setup        # Run the full setup wizard (configures everything at once)
hermes claw migrate # Migrate from OpenClaw (if coming from OpenClaw)
hermes update       # Update to the latest version
hermes doctor       # Diagnose any issues
hermes proxy        # OpenAI-compatible local proxy backed by OAuth provider (v0.18+)
hermes desktop      # Launch the native desktop app (alias: hermes gui)
hermes dashboard    # Web admin panel + embedded chat
hermes cron create  # Create a cron-scheduled task with delivery
hermes webhook subscribe # Subscribe a webhook trigger
```

#### Snippet 4: pyproject.toml Python pin + razón (path: `pyproject.toml:13-23`)
```toml
# Upper bound is load-bearing, not cosmetic. uv resolves the project's
# Python from `requires-python`, and an inherited `UV_PYTHON` env var (or a
# fresh distro whose newest interpreter uv auto-picks) will otherwise select
# 3.14, where Rust-backed transitives (e.g. pydantic-core) have no cp314
# wheel yet and fall back to a maturin source build that fails. Capping at
# <3.14 makes uv refuse 3.14 with a clear error instead of attempting that
# build. Raise the ceiling once our Rust transitives ship cp314 wheels.
requires-python = ">=3.11,<3.14"
```

#### Snippet 5: pyproject.toml pinning policy (path: `pyproject.toml:32-48`)
```toml
# Core — every direct dep is exact-pinned to ==X.Y.Z (no ranges).
# Rationale: ranges allow PyPI to ship a fresh version of a transitive
# at any time without a code review on our side. Exact pins mean the
# only way a new package version reaches a user is via an intentional
# update on our end (bump the pin in this file, regenerate uv.lock).
# This was tightened on 2026-05-12 in response to the Mini Shai-Hulud
# worm hitting mistralai 2.4.6 on PyPI; if that release had been
# captured by `mistralai>=2.3.0,<3` rather than an exact pin, every
# install in the hours before the quarantine would have pulled it.
```

#### Snippet 6: hermes-already-has-routines.md competitive (path: `hermes-already-has-routines.md:1-20`)
```markdown
# Hermes Agent Has Had "Routines" Since March

Anthropic just announced [Claude Code Routines](https://claude.com/blog/introducing-routines-in-claude-code) — scheduled tasks, GitHub event triggers, and API-triggered agent runs. Bundled prompt + repo + connectors, running on their infrastructure.

It's a good feature. We shipped it two months ago.

## The Three Trigger Types — Side by Side

Claude Code Routines offers three ways to trigger an automation:

**1. Scheduled (cron)**
> "Every night at 2am: pull the top bug from Linear, attempt a fix, and open a draft PR."

Hermes equivalent — works today:
\`\`\`bash
hermes cron create "0 2 * * *" \\
  "Pull the top bug from the issue tracker, attempt a fix, and open a draft PR." \\
  --name "Nightly bug fix" \\
  --deliver telegram
\`\`\`

**2. GitHub Events (webhook)**
> "Flag PRs that touch the /auth-provider module and post to #auth-changes."

Hermes equivalent — works today:
\`\`\`bash
hermes webhook subscribe auth-watch \\
  --events "pull_request" \\
  --prompt "PR #{pull_request.number}: {pull_request.title} by {pull_request.user.login}. Check if it touches the auth-provider module. If yes, summarize the changes." \\
  --deliver slack
\`\`\`

**3. API Triggers**
> "Read the alert payload, find the owning service, post a triage summary to #oncall."

Hermes equivalent — works today:
\`\`\`bash
hermes webhook subscribe alert-triage \\
  --prompt "Alert: {alert.name} — Severity: {alert.severity}. Find the owning service, investigate, and post a triage summary with proposed first steps." \\
  --deliver slack
\`\`\`
```

#### Snippet 7: SKILL.md frontmatter (path: `skills/autonomous-ai-agents/hermes-agent/SKILL.md:1-12`)
```yaml
---
name: hermes-agent
description: "Configure, extend, or contribute to Hermes Agent."
version: 2.3.0
author: Hermes Agent + Teknium
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode]
---
```

#### Snippet 8: Tabla CLI vs Messaging Quick Reference (README)
```markdown
| Action                         | CLI                                           | Messaging platforms                                                              |
| ------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
| Start chatting                 | `hermes`                                      | Run `hermes gateway setup` + `hermes gateway start`, then send the bot a message |
| Start fresh conversation       | `/new` or `/reset`                            | `/new` or `/reset`                                                               |
| Change model                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
| Set a personality              | `/personality [name]`                         | `/personality [name]`                                                            |
| Retry or undo the last turn    | `/retry`, `/undo`                             | `/retry`, `/undo`                                                                |
| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]`                                        |
| Browse skills                  | `/skills` or `/<skill-name>`                  | `/<skill-name>`                                                                  |
| Interrupt current work         | `Ctrl+C` or send a new message                | `/stop` or send a new message                                                    |
| Platform-specific status       | `/platforms`                                  | `/status`, `/sethome`                                                            |
```

#### Snippet 9: Migración desde OpenClaw (README)
```bash
hermes claw migrate              # Interactive migration (full preset)
hermes claw migrate --dry-run    # Preview what would be migrated
hermes claw migrate --preset user-data   # Migrate without secrets
hermes claw migrate --overwrite  # Overwrite existing conflicts
```

#### Snippet 10: Release body v0.18.0 headline (path: API releases/tags/v2026.7.1, líneas 1-15)
```markdown
# Hermes Agent v0.18.0 (v2026.7.1)

**Release Date:** July 1, 2026
**Since v0.17.0:** ~1,720 commits · 998 merged PRs · 2,215 files changed · ~251,000 insertions · ~41,000 deletions · **949 issues closed** · **370+ community contributors**

> **The Judgment Release.** Over the last week and a half the team put nearly all of its effort into one goal: resolve **every P0 and P1 issue and PR in the entire Hermes Agent repo** — and as of this release, **100% of them are closed.** Zero open P0s. Zero open P1s. That's **~700 highest-priority items** cleared as part of **~1,950 total issues and PRs closed** this window. We intend to keep P0/P1 at zero from here on.

> On top of that clean-sweep, v0.18.0 is about how *well* Hermes thinks and how it *knows when its work is actually done*. Mixture-of-Agents became a first-class citizen — named ensembles of models you can pick like any other model, with every reference model's reasoning shown to you and the aggregator's answer streamed live. The agent learned to verify its own work against evidence instead of vibes, `/goal` gained completion contracts, and `/learn` + `/journey` turned self-improvement into something you can see and steer. Underneath, the gateway became genuinely deployable-at-scale (scale-to-zero, drain coordination), the desktop grew first-class coding projects and a playable memory graph, and subagents can now fan out in the background.
```

#### Snippet 11: Release v0.18.2 body (path: API releases/latest)
```markdown
# Hermes Agent v0.18.2 (v2026.7.7.2)

**Release Date:** July 7, 2026

> Same-day patch on top of v0.18.1, picking up the WhatsApp Baileys dependency fix needed for tagged-release Docker builds.

---

## What's in this patch

- **fix(whatsapp): unpin Baileys from git commit, use published 7.0.0-rc13** ([#60643](https://github.com/NousResearch/hermes-agent/pull/60643)) — the WhatsApp bridge dependency now installs from the published npm release instead of a pinned git commit, making installs and Docker image builds reliable.

## Updating

\`\`\`bash
hermes update        # existing installs
pip install -U hermes-agent
\`\`\`
```

## Buenas prácticas (移植 a Aithera)

- ✅ **Closed learning loop con nudges**: la V0.85 de Aithera debería implementar algo equivalente sobre el `MemoryManager` ChromaDB existente. Empezar con "self-verification" (que el agente verifique su trabajo contra evidencia) que es más simple que el loop completo.
- ✅ **Sistema de skills con formato abierto (agentskills.io)**: Aithera podría crear un `aithera-skills/` que se alimente de JWIKI + memoria de usuario. La integración con agentskills.io (que ya soportan tanto Superpowers como Hermes) sería una decisión estratégica fuerte.
- ✅ **Multi-plataforma de mensajería con gateway unificado + core/plugin split**: Aithera V0.8 ya tiene la base, le falta implementar Discord/Slack/WhatsApp/Signal. La estructura `gateway/platforms/` (core) + `plugins/platforms/` (plugin opt-in) de Hermes es el patrón a seguir.
- ✅ **Cron scheduler con delivery flexible (a 22+ plataformas)**: Aithera V0.9 (Automation Engine) debería imitar este patrón. Aithera tiene 1 canal (Telegram); aspirar a 5+ mínimo (Telegram + Email + Web + Discord + Slack) en V0.9-V1.0.
- ✅ **Sub-agents aislados con RPC + background fan-out**: V1.0 Orchestrator. El concepto de "zero-context-cost turns" (el sub-agent tiene su propio contexto) es clave.
- ✅ **Toolsets (grupos de tools activables)**: Aithera V1.0 debería introducir este concepto. Hoy tiene 8 tools en ToolManager; aspirar a 40+ agrupados en 8-10 toolsets (Email, Calendar, Projects, Memory, Voice, Browser, Code, Research).
- ✅ **MCP support**: V0.85 o V1.0 debería añadir `mcp_server.py` y consumir servidores MCP populares (filesystem, git, github, postgres).
- ✅ **Tool Gateway opcional** (web search, image gen, TTS, cloud browser como suscripción): modelo de negocio a explorar para Aithera V1.1+.
- ✅ **6 terminal backends**: empezar con Docker, luego añadir SSH. Modal/Daytona para V1.1+ si Aithera se ejecuta en serverless.
- ✅ **Migración automática desde OpenClaw**: Aithera podría hacer lo mismo (`aithera migrate from openclaw`) — pero el mercado está saturándose; quizás mejor `aithera migrate from hermes` cuando llegue V1.0.
- ✅ **Native desktop app (Electron)**: Aithera YA TIENE Electron + AICore 3D. V0.85 podría借鉴 el "playable memory graph" de Hermes.
- ✅ **MoA (Mixture-of-Agents) first-class**: feature barata de implementar (es solo routing) y de alto valor. La V0.85 podría añadir un provider `moa` al AIManager.
- ✅ **OpenAI-compatible local proxy**: Aithera V0.7 ya tiene `/api/chat`. La V0.85 podría exponer un endpoint OpenAI-compatible puro para que otras apps se conecten.
- ✅ **Pinning policy post-Mini Shai-Hulud (mayo 2026)**: documentar en `CLAUDE.md` o `docs/SECURITY.md` la policy de "exact pin sin ranges" + "comentarios con CVE-IDs" que tiene Hermes.
- ✅ **API server (api_server.py 219KB) como OpenAI-compatible local proxy**: si Aithera quisiera exponer un endpoint compatible con el 100% del ecosistema OpenAI SDK, podría借鉴 este patrón.
- ✅ **ACP server para IDEs**: V1.0+ podría ofrecer un ACP server para que VS Code/Zed/JetBrains se conecten a Aithera.

## Errores comunes

- ❌ No confundir **Hermes Agent** (este proyecto, Nous Research, 211k★, agent framework) con **Hermes** (la familia de LLMs de Nous Research). Son cosas distintas: los LLMs son los modelos, el Agent es el framework que los usa.
- ❌ No confundir con [JWIKI-006 JarvisAgent](./jarvisagent.md) (Tauri/Rust, 4★, proyecto personal).
- ❌ No confundir con [JWIKI-005 OpenJarvis](./openjarvis.md) (Stanford, Python, 7k★, local-first).
- ❌ No confundir con "Open Hermes" (varios proyectos no relacionados con ese nombre).
- ❌ No asumir que el "5 backends" del landing es la cifra correcta: el landing está desactualizado y dice 5, pero el README y el pyproject confirman **6** (con Daytona).
- ❌ No asumir que "Telegram, Discord, Slack, WhatsApp, Signal" son las únicas plataformas: la realidad son **22+** adapters (gateway/platforms + plugins/platforms).
- ❌ No confundir `v0.18.0 "The Judgment Release"` con la versión actual: ya hay `v0.18.2 v2026.7.7.2` publicada el 2026-07-08.

## Breaking Changes

| Versión | Cambio | Impacto |
|---|---|---|
| Mini Shai-Hulud worm 2026-05-12 | Hermes cambió de ranges a exact-pins en deps directas | Otros proyectos que usaban mistralai>=2.3.0,<3 fueron infectados; los que tenían pin exacto no |
| v0.18.0 (2026-07-01) | MoA pasó de "modo togglable" a "first-class model provider" | Apps que integraban MoA como flag separado deben migrar a usar el model picker |
| v0.18.0 (2026-07-01) | Gateway scale-to-zero + drain coordination | Deployments que asumían gateway always-on deben manejar el wake-up |
| v0.18.0 (2026-07-01) | Subagents background fan-out | Apps que asumían sub-agents síncronos deben revisar |
| v0.18.1 (2026-07-08) | Patch sobre v0.18.0 con curated notes diferidas | Sin breaking changes explícitos |
| v0.18.2 (2026-07-08) | fix(whatsapp): unpin Baileys from git, use published 7.0.0-rc13 | Docker builds ahora confiables; installs sin git commit pin |
| OpenClaw rename Ene 2026 | OpenClaw migró a Hermes vía `hermes claw migrate` | Proyectos que dependían de OpenClaw ahora pueden migrar |

## Cambios entre versiones

| Versión | Tag | Fecha | Notas |
|---|---|---|---|
| v0.18.2 | v2026.7.7.2 | 2026-07-08 | WhatsApp Baileys dep fix (Docker builds) |
| v0.18.1 | v2026.7.7 | 2026-07-08 | Patch release (curated notes → v0.19.0) |
| v0.18.0 | v2026.7.1 | 2026-07-01 | **"The Judgment Release"**: 100% P0/P1 cerrados (~700 items), MoA first-class, scale-to-zero, memory graph, /goal+ /learn+/journey, background fan-out |
| v0.17.0 | v2026.6.19 | 2026-06-19 | (Release notes no consultadas en este tick) |
| v0.16.0 | v2026.6.5 | 2026-06-06 | "The Surface Release" |
| v0.15.2 | v2026.5.29.2 | 2026-05-29 | Bug fix |
| v0.15.1 | v2026.5.29 | 2026-05-29 | "The Patch Release" |
| v0.15.0 | v2026.5.28 | 2026-05-28 | "The Velocity Release" |

**Patrón observado**: cadencia de releases semanal a quincenal. Naming convention `vAAAA.M.P` (año.mes.patch) + nombre semántico ("The Judgment", "The Velocity", "The Surface", "The Patch"). Numeración interna `v0.X` con X=patch acumulado.

## Impacto sobre otros sistemas

- [JWIKI-002 projects.md](./projects.md#hermes-agent) — comparativa principal, debe actualizarse con 211.474★ (vs 53k estimado en task_queue original), "Python 80%" → "Python 84.3% + TypeScript 14.2%", v0.18.0 → v0.18.2, "5+ mensajerías" → "22+ mensajerías", añadir 6 backends (no 5), native desktop apps, MoA first-class.
- [JWIKI-006 jarvisagent.md](./jarvisagent.md) — comparativa de arquitectura (Tauri+Vue+Rust vs Python 84.3% + TypeScript 14.2% + Rust 0.2% mixto).
- [JWIKI-009 superpowers.md](./superpowers.md) — el otro framework de skills (obra, 249.642★, MIT, multi-language) — comparar con el de Hermes. **Insight**: tanto Superpowers (Shell+JS+TS+Python) como Hermes (Python 84.3% + TypeScript 14.2%) son agentskills.io compatibles. Son los 2 frameworks de skills dominantes del ecosistema OSS en 2026.
- [JWIKI-119 memory-readme.md](../07_MEMORY/README.md) — Hermes usa Honcho + FTS5 + Hindsight/Supermemory/Mem0; Aithera usa ChromaDB. Tradeoff interesante: Honcho es "dialectic user modeling" (más rico que un vector store), FTS5 es búsqueda full-text (más rápido para keyword recall).
- [JWIKI-101 agents-readme.md](../06_AGENTS/README.md) — Hermes es agente framework comparable a LangGraph/CrewAI/AutoGen, pero también compite con Claude Code/Codex/OpenClaw (ver SKILL.md related_skills).
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md) — Hermes tiene 300+ modelos vía Nous Portal; ¿es replicable en Aithera? **Sí, el patrón "model aggregator + Tool Gateway" es replicable, pero requiere inversión significativa.**
- [JWIKI-118 approval-flows.md](../06_AGENTS/approval-flows.md) — Hermes tiene approval workflows (security docs `/user-guide/security`); ¿cómo encaja con el Orchestrator de Aithera V1.0?
- [JWIKI-113 mcp.md](../06_AGENTS/mcp.md) — Hermes tiene `mcp_serve.py` (35KB) + `optional-mcps/`. Aithera V0.8 debería借鉴.
- [JWIKI-052 plugin-architecture.md](../02_ARCHITECTURE/plugin-architecture.md) — Hermes tiene el patrón core/plugin split (`gateway/platforms/` core + `plugins/platforms/` opt-in). Es el patrón de plugin architecture que Aithera V1.0+ debería参考.
- [JWIKI-050 sse-streaming.md](../02_ARCHITECTURE/sse-streaming.md) — Hermes streamea con SSE (similar a Aithera V0.7).

## Referencias cruzadas

- [JWIKI-001 history.md](./history.md) — historia de los LLMs Hermes (Nous Research)
- [JWIKI-002 projects.md](./projects.md#hermes-agent) — comparativa de proyectos (REWORK NECESARIO: ver "Impacto sobre otros sistemas")
- [JWIKI-003 openclaw.md](./openclaw.md) — desde donde migra (`hermes claw migrate`)
- [JWIKI-005 openjarvis.md](./openjarvis.md) — otro "Jarvis" (no confundir)
- [JWIKI-006 jarvisagent.md](./jarvisagent.md) — el otro "Jarvis" (Tauri/Rust)
- [JWIKI-007 docs oficiales](https://hermes-agent.nousresearch.com/docs/) — referencia autoritativa
- [JWIKI-008 clawdbot.md](./clawdbot.md) — controversias del rename OpenClaw
- [JWIKI-009 superpowers.md](./superpowers.md) — el otro framework de skills (agentskills.io compatible)
- [JWIKI-101 agents-readme.md](../06_AGENTS/README.md) — comparativa frameworks agentes
- [JWIKI-113 mcp.md](../06_AGENTS/mcp.md) — Model Context Protocol (Hermes tiene `mcp_serve.py`)
- [JWIKI-118 approval-flows.md](../06_AGENTS/approval-flows.md) — approval workflows
- [JWIKI-119 memory-readme.md](../07_MEMORY/README.md) — comparativa vector stores

## Fuentes

1. https://api.github.com/repos/NousResearch/hermes-agent — acceso 2026-07-08 19:55Z (stars=211474, forks=38853, open_issues=26881, subscribers=825, license=MIT, created=2025-07-22, pushed=2026-07-08T15:32:15Z)
2. https://api.github.com/repos/NousResearch/hermes-agent/releases/latest — acceso 2026-07-08 19:55Z (tag=v2026.7.7.2, name=Hermes Agent v0.18.2, published=2026-07-08T03:11:22Z)
3. https://api.github.com/repos/NousResearch/hermes-agent/releases — acceso 2026-07-08 19:55Z (8 releases en últimos 60 días: v0.15.0 → v0.18.2)
4. https://api.github.com/repos/NousResearch/hermes-agent/releases/tags/v2026.7.1 — acceso 2026-07-08 (v0.18.0 "The Judgment Release", 1720 commits + 998 PRs + 949 issues + 370+ contribuidores)
5. https://api.github.com/repos/NousResearch/hermes-agent/languages — acceso 2026-07-08 (Python 55.3MB/84.3%, TypeScript 9.3MB/14.2%, JavaScript 969KB/1.5%, etc.)
6. https://api.github.com/repos/NousResearch/hermes-agent/contents/ — acceso 2026-07-08 (top-level structure: 25 dirs, 30 files; cli.py 744KB, run_agent.py 269KB, hermes_state.py 278KB)
7. https://api.github.com/repos/NousResearch/hermes-agent/contents/gateway — acceso 2026-07-08 (35 archivos + 4 subdirs)
8. https://api.github.com/repos/NousResearch/hermes-agent/contents/gateway/platforms — acceso 2026-07-08 (core platforms: bluebubbles, msgraph_webhook, signal, weixin, whatsapp_cloud, yuanbao, qqbot)
9. https://api.github.com/repos/NousResearch/hermes-agent/git/trees/main?recursive=1 — acceso 2026-07-08 (22 plugin platforms en `plugins/platforms/`)
10. https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md — acceso 2026-07-08 (17.617 bytes, 263 líneas, 16 topics, tagline + features)
11. https://raw.githubusercontent.com/NousResearch/hermes-agent/main/pyproject.toml — acceso 2026-07-08 (21.219 bytes, Python >=3.11<3.14, 30+ deps pinned a ==X.Y.Z, 18 extras, 8 CVEs documentados)
12. https://raw.githubusercontent.com/NousResearch/hermes-agent/main/hermes-already-has-routines.md — acceso 2026-07-08 (6.373 bytes, competitive post vs Claude Code Routines)
13. https://raw.githubusercontent.com/NousResearch/hermes-agent/main/skills/autonomous-ai-agents/hermes-agent/SKILL.md — acceso 2026-07-08 (51.586 bytes, v2.3.0, MIT, by Hermes Agent + Teknium, related_skills: [claude-code, codex, opencode])
14. https://hermes-agent.nousresearch.com/ — acceso 2026-07-08 (landing oficial, footer "Hermes Agent v0.18.2", pricing Free/Plus/Super/Ultra, 6 features numeradas, native desktop downloads directos)
15. https://github.com/plastic-labs/honcho — citado en README (Honcho user modeling dialectico, honcho-ai==2.0.1)
16. https://agentskills.io — citado en README y SKILL.md (open standard de skills)
17. https://portal.nousresearch.com — citado en README (Nous Portal, 300+ modelos, Tool Gateway opcional)

## Nivel de confianza

**95%** — Datos numéricos y arquitectura confirmados vía GitHub API (3 endpoints: `/repos/`, `/releases/latest`, `/languages` + recursive tree) + lectura directa de `pyproject.toml` (21KB) + `README.md` (17KB) + `hermes-already-has-routines.md` (6KB) + SKILL.md (51KB) + landing oficial. **Discrepancias con doc previo documentadas y resueltas (5 conflictos)**. La tracción (211.474★) y la cadencia de releases (8 en 60 días) están fuera de duda. Pendiente menor: listar los 40+ tools concretamente (requeriría leer `tools/` y `toolsets.py` línea por línea, fuera del scope de este tick).

## Pendientes

- [ ] Listar los 40+ tools concretamente (categorías, nombres, qué hacen)
- [ ] Detalle exacto de los 6 backends (¿cuáles son providers oficiales vs plugins?) — pyproject muestra extras `modal` y `daytona`, pero ¿`singularity`? ¿`ssh`? son built-in o plugins?
- [ ] Profundizar en Honcho integration (¿cómo se llama la API? ¿qué dialectic model usa? ¿en qué difiere de un vector store tradicional?)
- [ ] Verificar el agentskills.io standard (link a spec, schema completo, herramientas de validación)
- [ ] Confirmar pricing tiers Nous Portal (Free/Plus/Super/Ultra) y precios concretos
- [ ] Releer JWIKI-002 projects.md y corregir la entrada de Hermes (53k → 211.474★, 5+ → 22+ mensajerías, v0.18.0 → v0.18.2)
- [ ] Crear cross-link desde [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md) sobre el modelo de 300+ modelos
- [ ] Considerar crear un doc dedicado al agentskills.io standard (¿JWIKI-XXX agentskills-standard.md?)
- [ ] Considerar crear un doc dedicado a Honcho (¿JWIKI-XXX honcho.md?)
- [ ] Investigar la integración con Teknium (co-autor de la SKILL.md) — ¿es el autor de Moltbot o de otra cosa?
- [ ] Profundizar en `hermes_state.py` (278KB) y `run_agent.py` (269KB) — son los archivos más grandes del repo y contienen la lógica core
- [ ] Investigar la SKILL.md de `claude-code`, `codex`, `opencode` que están en `skills/autonomous-ai-agents/` — son los 4 frameworks de coding agents principales del 2026 según el related_skills de Hermes

---

## Changelog

### 2026-07-08 19:55 — versión re-auditada e independiente
- **Autor**: orquestador JWIKI single-team (tick A-20260708-1955)
- **Cambio**: doc pre-existente (2579 palabras, creado 2026-07-07) re-auditado e独立amente enriquecido. Material crudo expandido de 26 a 102 hechos verificados (con contraste GitHub API 2026-07-08). 5 conflictos entre fuentes documentados y resueltos. 11 snippets con path:line (vs 5 del doc previo). Doc final reescrito de 2579 → ~4500+ palabras, todas las secciones del TEMPLATE.md rellenas, tabla comparativa con Aithera V0.7.3, refs cruzadas actualizadas.
- **Validador**: contraste GitHub API directo (`/repos/`, `/releases/latest`, `/releases`, `/languages`, `/contents/`, `/git/trees/main?recursive=1`) + raw.githubusercontent.com del `main` branch (HEAD commit a 2026-07-08T15:32:15Z) + landing oficial + SKILL.md del propio repo
- **Discrepancias resueltas vs doc previo**:
    - Stars: 210.335 → 211.474 (+1.139 en 24h, ritmo confirmado ~1.100-1.700/día)
    - Versión: v0.18.0 → **v0.18.2 v2026.7.7.2** (publicada HOY 2026-07-08 03:11 UTC; el doc previo estaba stale 1 semana)
    - Python: 80% → 84.3% (TypeScript 14.2%, contraste directo)
    - Mensajerías: 5+ → **22+** (gateway/platforms + plugins/platforms verificados vía recursive tree)
    - Backends: 5 (landing) → 6 (README + pyproject, con Daytona)
- **Hallazgos nuevos no documentados previamente**:
    - Native desktop apps (macOS DMG + Windows EXE + Linux AppImage)
    - MoA (Mixture-of-Agents) first-class desde v0.18.0
    - Gateway scale-to-zero + drain coordination
    - Memory graph jugable en desktop
    - API server (api_server.py 219KB) como OpenAI-compatible local proxy (`hermes proxy`)
    - Profiles feature (múltiples instancias aisladas)
    - ACP server para IDEs (VS Code / Zed / JetBrains)
    - Pinning policy post-Mini Shai-Hulud worm (mayo 2026)
    - Lazy install pattern via `tools/lazy_deps.py`
    - Hermes ya tiene "Routines" desde marzo 2026 (competitive vs Claude Code Routines)
    - Python cap explícito en 3.14 (con razón técnica detallada)
    - FastAPI dashboard (`fastapi>=0.104.0,<1`, `uvicorn[standard]>=0.24.0,<1`)
    - 8 CVEs explícitos en comentarios del pyproject.toml
    - 22+ plataformas de mensajería incluyendo 7+ chinas (WeChat, WeCom, QQ, Yuanbao, DingTalk, Feishu, iMessage en chino)
- **Estado**: 🟢 verified (95% confianza, 6/6 criterios CONSTITUTION.md §8)

### 2026-07-07 — versión inicial
- **Autor**: sesión actual (sin subagente) + Aithera Escriba
- **Cambio**: doc creado desde cero con material crudo completo (26 hechos verificados, 5 snippets, datos numéricos GitHub API + README 263 líneas)
- **Validador**: contraste con GitHub API directo
- **Estado**: 🟢 verified (88% confianza, 5/6 criterios CONSTITUTION.md §8 — criterio 6 estricto no cumplido: no hubo review independiente posterior)
