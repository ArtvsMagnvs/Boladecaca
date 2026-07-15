# OpenHuman — Architecture (derived from code)

> **Source of truth**: `github.com/tinyhumansai/openhuman`, commit
> `407fd8edd75f155f345291ffa1e5c9e8af31fd75` (2026-07-13). Diagrams derived
> from imports, entry points, Cargo features, and `mod.rs` trees — **not from
> the README's marketing diagrams**. Path:line citations verified with
> `grep -n` and `read_file`.
>
> **Companion doc**: `openhuman-code-audit.md` (line-by-line analysis with
> ~80 verified path:line citations).

---

## 0. Mental model — what OpenHuman actually is

OpenHuman is a **Tauri 2 desktop application** that ships:

1. A **Tauri webview** (React + TypeScript + Rive) for the UI, the mascot
   animation, and the desktop-native shell.
2. A **Tauri host process** (Rust) that owns the windows, the
   autoupdater, native notifications, screen capture, the meeting auto-join,
   and the IPC bridge to the core.
3. A **headless Rust core** (`openhuman-core` binary) that owns all agent
   logic: the LLM agent loop, the 3-layer memory system, the 17 channels,
   the 3 sandbox backends, the 33 built-in sub-agents, the 8-tier model
   router, the Composio managed-proxy, the 20-min sync loop, the
   subconscious background loop, and the Sentry reporting.

The core is **embeddable** — `src/lib.rs:27`:
```rust
// verified path:line: src/lib.rs:25-27
/// Embeddable core composition API. Host the OpenHuman core in any process —
/// the Tauri shell, a CLI, a stdio MCP server, or a cloud/team server — via
/// [`CoreBuilder`] → [`CoreRuntime`]. See `docs/plans/pluggable-core/`.
pub use core::runtime::{CoreBuilder, CoreRuntime, ServiceSet, TokenSource};
```

So OpenHuman is a **library + binary** that can run in the Tauri shell
(default), as a CLI, as a stdio MCP server, or as a self-hosted cloud
service (the `docker-compose.yml` path).

---

## 1. Process & module topology

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ USER (single user, single machine)                                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
       ┌───────────────────────────────┼───────────────────────────────┐
       ▼                               ▼                               ▼
┌────────────────────┐       ┌────────────────────┐         ┌──────────────────┐
│ Tauri webview      │       │ Tauri host process │         │ Core subprocess  │
│ app/src/           │       │ app/src-tauri/src/ │  IPC    │ src/main.rs      │
│ (3,149 LoC TS)     │       │ (50+ LoC files Rust)│ ◄────► │ (openhuman-core  │
│ - React UI         │       │ - main.rs / lib.rs  │  HTTP   │  binary, 200+    │
│ - Rive mascot      │ ◄───► │ - core_process.rs   │  /pipe  │  Cargo bins)     │
│ - Channel views    │ Tauri │ - core_rpc.rs       │         │                  │
│ - Memory tree UI   │  IPC  │ - meet_*, mascot_*  │         │  Agent loop +    │
│ - Settings         │       │ - mcp_commands.rs   │         │  memory + tools  │
│ - 17 channel UIs   │       │ - deep_link_ipc.rs  │         │  + channels +    │
│ - Workflow canvas  │       │ - native_notif.     │         │  sync +          │
│ - Browser          │       │ - cef_preflight.rs  │         │  subconscious    │
└────────────────────┘       └────────────────────┘         └──────────────────┘
                                                                      │
                                                                      │ HTTP/WS
                                                                      ▼
                                              ┌──────────────────────────────────┐
                                              │  tinyhumans.ai backend           │
                                              │  (managed proxy, not in repo)    │
                                              │  - LLM inference (8 tiers)       │
                                              │  - Composio v3 proxy             │
                                              │  - Sentry sink                   │
                                              │  - tiny.place A2A                │
                                              │  - Updates / Tauri updater feed  │
                                              └──────────────────────────────────┘
```

This two-process design is **deliberate**: the Tauri host handles
desktop-OS-specific work (windows, IPC, autoupdater) while the
core is a normal headless Rust binary that can also run in Docker
(`docker-compose.yml`) or as an MCP stdio server.

### 1.1 Three-window desktop model

The Tauri host opens **multiple native windows** simultaneously:

```
$ ls app/src-tauri/src/*.rs | grep -E "window|notch|mascot" -i
app/src-tauri/src/lib.rs                     # main window registration
app/src-tauri/src/mascot_native_window.rs    # Rive mascot window
app/src-tauri/src/notch_window.rs            # macOS notch widget
app/src-tauri/src/ptt_overlay.rs             # push-to-talk overlay
app/src-tauri/src/companion_commands.rs      # Google Meet companion
app/src-tauri/src/native_notifications/      # system notifications
```

`app/src-tauri/tauri.conf.json:11-23`:
```json
"windows": [{
  "label": "main",
  "title": "OpenHuman",
  "width": 1000, "height": 800,
  "visible": false,
  "titleBarStyle": "Overlay", "hiddenTitle": true,
  "resizable": true
}]
```

The `visible: false` is a Tauri pattern where the main window is hidden
until the webview finishes initial render, then shown by an explicit
`window.show()` call after hydration.

---

## 2. Crate / module topology (Rust)

```
src/
├── main.rs                   # Sentry init + CLI dispatch (399 lines)
├── lib.rs                    # pub mod api; pub mod core; pub mod openhuman; pub mod rpc;
│                             # pub use openhuman::config::DaemonConfig;
│                             # pub use openhuman::memory_store::{MemoryClient, MemoryState};
│                             # pub use core::runtime::{CoreBuilder, CoreRuntime, …};
├── api/                      # Public HTTP API surface
│   ├── config.rs             # DEFAULT_API_BASE_URL = "https://api.tinyhumans.ai"
│   ├── jwt.rs                # Session JWT validation
│   ├── mod.rs
│   ├── models/
│   ├── rest.rs               # axum routes
│   ├── rest_tests.rs
│   └── socket.rs             # Socket.IO channel
├── core/                     # Embeddable core (CoreBuilder, CoreRuntime)
│   ├── cli.rs                # `cli` command dispatcher
│   ├── jsonrpc.rs            # JSON-RPC dispatcher
│   ├── runtime/              # Pluggable host composition
│   ├── event_bus/            # In-process pub/sub
│   ├── auth.rs               # API auth
│   ├── observability.rs      # Sentry filter pipeline
│   ├── shutdown.rs           # Graceful shutdown
│   ├── types.rs              # HostKind, …
│   └── socketio.rs
├── rpc/                      # JSON-RPC method registry
│   ├── mod.rs
│   └── structured_error.rs
├── openhuman/                # 133 sub-modules (the meat)
│   ├── agent/                # ReAct loop, dispatcher, harness, subagents
│   ├── agent_registry/       # 33 built-in sub-agents (TOML + prompt.md)
│   ├── agent_tool_policy/    # Per-agent tool gating
│   ├── channels/             # 17+ messaging channels
│   ├── codegraph/            # AST-aware code search
│   ├── composio/             # Managed-proxy client for Composio
│   ├── config/               # DaemonConfig, schema, validation
│   ├── credentials/          # OAuth/API key management
│   ├── cron/                 # Scheduled jobs
│   ├── cwd_jail/             # OS-level sandbox (Landlock/Seatbelt/AppContainer)
│   ├── desktop_companion/    # Google Meet auto-join
│   ├── embeddings/           # Cloud / Ollama / inert
│   ├── encryption/           # X25519 + ChaCha20-Poly1305 + Argon2id
│   ├── flows/                # tinyflows adapter
│   ├── harness_init/         # Boot wiring
│   ├── health/               # /health endpoint
│   ├── heartbeat/            # Subconscious heartbeat
│   ├── http_host/            # axum server
│   ├── image/                # Image gen
│   ├── inference/            # 8-tier LLM provider factory
│   ├── integrations/         # IntegrationClient + 270+ integrations
│   ├── javascript/           # JS execution
│   ├── keyring/              # OS keyring master key
│   ├── keyring_consent/      # User consent for keyring
│   ├── mcp_audit/            # MCP audit log
│   ├── mcp_client/           # MCP host
│   ├── mcp_registry/         # MCP server catalog
│   ├── mcp_server/           # MCP server (expose own tools)
│   ├── meet/                 # Google Meet integration
│   ├── meet_agent/           # Meet live transcript / answer-by-name
│   ├── agent_meetings/       # Calendar → auto-join scheduler
│   ├── memory/               # Top-level memory orchestrator
│   ├── memory_archivist/     # Background memory curator
│   ├── memory_conversations/ # Conversation index
│   ├── memory_diff/          # git-backed change ledger (libgit2)
│   ├── memory_goals/         # Long-term + per-thread goals
│   ├── memory_queue/         # Ingest queue
│   ├── memory_search/        # Cross-thread FTS5 + vector search
│   ├── memory_sources/       # Per-source mirror of the tree
│   ├── memory_store/         # SQLite persistence (vendored tinycortex)
│   ├── memory_sync/          # Periodic sync (20 min) + workspace sync
│   ├── memory_tools/         # Memory tools (search, store, archive)
│   ├── memory_tree/          # Summary-tree engine
│   ├── model_council/        # Multi-model debate / vote
│   ├── notifications/
│   ├── orchestration/        # Cross-agent orchestration
│   ├── overlay/              # Screen overlay
│   ├── people/               # Address book / contacts
│   ├── plan_review/          # Workflow plan UI backend
│   ├── profiles/             # User profiles
│   ├── prompt_injection/     # Injection defense
│   ├── provider_surfaces/    # Per-provider feature flags
│   ├── recall_calendar/      # Calendar recall
│   ├── redirect_links/       # OAuth redirect handler
│   ├── referral/
│   ├── rhai_workflows/       # Rhai .ragsh scripting
│   ├── routing/              # Quality / refusal detection
│   ├── runtime_node/         # Node.js sidecar
│   ├── runtime_python/       # Python sidecar
│   ├── runtime_python_server/
│   ├── sandbox/              # 3 backend kinds (None/Local/Docker)
│   ├── scheduler_gate/       # Battery / charging throttle
│   ├── screen_intelligence/  # Vision / screen capture
│   ├── search/               # Web search
│   ├── security/             # OS keyring, approval gate
│   ├── service/              # Daemon lifecycle
│   ├── session_db/           # Session persistence
│   ├── session_import/       # Cross-session import
│   ├── skill_registry/       # Skills catalog
│   ├── skill_runtime/        # Skills execution
│   ├── skills/               # SKILL.md loader
│   ├── socket/               # Socket.IO bridge
│   ├── subconscious/         # Background memory loop
│   ├── subconscious_triggers/# Trigger → reflection
│   ├── task_sources/         # Task source registry
│   ├── team/                 # Multi-agent team registry
│   ├── text_input/
│   ├── threads/              # Conversation threads
│   ├── thread_goals/         # Per-thread goal budget
│   ├── tinyagents/           # Adapter seam → vendored tinyagents
│   ├── tinycortex/           # Adapter seam → vendored tinycortex
│   ├── tinyflows/            # Adapter seam → vendored tinyflows
│   ├── tinyplace/            # Adapter seam → tiny.place A2A
│   ├── tls/                  # TLS cert handling
│   ├── tokenjuice/           # TokenJuice (token compression)
│   ├── tool_registry/        # Tool name → Tool
│   ├── tool_status/          # Per-tool liveness
│   ├── tool_timeout/         # Tool execution timeouts
│   ├── tools/                # Tool trait + 50+ impl
│   ├── update/               # Tauri updater backend
│   ├── util.rs
│   ├── voice/                # Whisper STT, Piper TTS, wake word
│   ├── wallet/               # Multi-chain wallet
│   ├── web3/                 # Web3 primitives
│   ├── webhooks/             # Webhook handlers
│   ├── webview_accounts/     # Account mgmt
│   ├── webview_apis/         # Webview-side API
│   ├── webview_notifications/
│   ├── whatsapp_data/        # WhatsApp data tools
│   ├── workspace/            # Workspace CRUD
│   └── x402/                 # x402 USDC protocol
└── bin/                      # 7 standalone binaries (slack-backfill,
                              # gmail-backfill-3d, memory-tree-init-smoke,
                              # inference-probe, harness-subagent-audit,
                              # test-mcp-stub, openhuman-fleet)
```

The **adapter-seam pattern** is critical: every "tiny-*" vendored crate
(`tinyagents`, `tinycortex`, `tinyflows`, `tinyjuice`, `tinychannels`,
`tinyplace`) has a **host-side adapter module** in `src/openhuman/` that
bridges OpenHuman's types onto the vendored crate's traits. The actual
business logic for agent execution / memory / workflows / compression
lives in the vendored crate, but RPC, tools, sync, and security gating
stay host-side. This is the project structure pattern documented in the
`Cargo.toml:51-91` comments.

---

## 3. The agent loop (data flow)

```
    ┌──────────────────────────────────────────────────────────────────┐
    │  USER TYPED MESSAGE  OR  CHANNEL MESSAGE  OR  CRON TRIGGER        │
    └──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │ Agent::turn(&mut self, user_message)  src/.../turn/core.rs:141   │
    │ ─────────────────────────────────────────────────────────────── │
    │ 1. first_turn = self.history.is_empty()                          │
    │ 2. Emit TurnStarted progress                                     │
    │ 3. If empty: try_load_session_transcript()  (KV cache reuse)     │
    │ 4. If first turn:                                                │
    │      - fetch_connected_integrations()                            │
    │      - fetch_learned_context()                                   │
    │      - build_system_prompt(learned)?    (built ONCE)            │
    │ 5. memory.store(user_msg, key=uuid)  (fire-and-forget)           │
    │ 6. collect_recall_citations(user_msg, limit=5, min_rel=0.4)      │
    │ 7. memory_loader.load_context(user_msg)                          │
    │ 8. STM cross-thread context (first turn only)                    │
    │ 9. Lane B: situational preferences (every turn)                 │
    │10. inject_agent_experience_context()                             │
    │11. inject_triggered_memory_agent_context()                       │
    │12. Inject pending integration / MCP / skill announcements       │
    │13. PIN effective_model = self.model_name (NO per-turn reclass)   │
    │14. run_turn_via_tinyagents_session(effective_model,              │
    │                                     max_iterations,              │
    │                                     run_super_context,           │
    │                                     artifact_store)              │
    │15. Result → spawn_session_memory_extraction() (if thresholds met)│
    │         → spawn_transcript_ingestion() (background)              │
    └──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │ tinyagents harness (vendored)   src/.../tinyagents/              │
    │ ─────────────────────────────────────────────────────────────── │
    │  Graph nodes (per cycle):                                        │
    │   - call_provider(model, messages, tools)                        │
    │   - parse_tool_calls (dispatcher: XML / JSON / P-Format)         │
    │   - for each tool call:                                          │
    │       * tool_policy_gate.check(call, origin)                     │
    │       * approval_gate.check(call)                                │
    │       * execute(call)                                            │
    │         ├── sandbox: None → host shell (NativeRuntime)           │
    │         ├── sandbox: Local → cwd_jail (Landlock/Seatbelt/AppCon) │
    │         └── sandbox: Docker → container (docker exec)            │
    │       * write tool_result back to message history                │
    │       * publish progress event → UI                              │
    │   - mid-flight: steering forwarder, abort guard, subagent fork   │
    │   - on terminal: persist transcript, emit TurnCompleted          │
    │  Loop cap: max_iterations (typically 8–10, 20 for orchestrator) │
    └──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │  LLM PROVIDER  (chosen by 8-tier router)                         │
    │ ─────────────────────────────────────────────────────────────── │
    │  PROVIDER_OPENHUMAN   → api.tinyhumans.ai (managed)              │
    │  ollama:<model>       → local Ollama                             │
    │  lmstudio:<model>     → local LM Studio                          │
    │  mlx:<model>          → local MLX                                │
    │  omlx:<model>         → local OMLX                               │
    │  local-openai:<model> → generic local OpenAI-compatible         │
    │  claude_agent_sdk     → Claude Code subprocess                   │
    │  <slug>:<model>       → cloud_providers entry (BYOK)             │
    │                                                                  │
    │  Tier hints (factory.rs:101-117):                                │
    │    reasoning | reasoning_quick | chat | agentic | burst          │
    │    coding | vision | summarization | subconscious                │
    │  Reliable layer: per-tier fallback on 429/408/502/503/504        │
    └──────────────────────────────────────────────────────────────────┘
```

### 3.1 Why the model is pinned (KV cache)

`src/openhuman/agent/harness/session/turn/core.rs:598-606`:
> *"Pin the main agent to its configured model for the lifetime of the
> session. Per-turn classification used to run here, but it would flip
> `effective_model` mid-conversation (e.g. reasoning → coding based on a
> single keyword). Every flip invalidates the backend's KV cache namespace
> for this session, costing full re-prefill on the very next turn. The
> main agent's job is to decide which sub-agent to spawn — that routing
> lives in the model prompt, not in the Rust-side classifier. Sub-agents
> pick their own tier via `ModelSpec::Hint(...)` in their definition."*

The main chat is always one model; **sub-agents are how OpenHuman gets
multi-model routing** (orchestrator decides, spawns `code_executor` which
has `model.hint = "coding"`, that sub-agent uses the coding-tier model
for the duration of the work).

### 3.2 Sub-agent delegation

`src/openhuman/tinyagents/subagent_graph.rs` implements the delegation.
The orchestrator's `delegate_*` tools spawn child agents that:
1. Inherit the parent's provider Arc (per `agent/harness/session/runtime.rs:63`:
   *"Clone the agent's model source. Used by the sub-agent runner /
   parent-context builder to share the parent's provider instance with
   spawned sub-agents (so they share connection pools, retry budgets,
   and rate-limit state)"*).
2. Get a filtered tool list (per-archetype, via `ToolScope` in the
   agent TOML).
3. Run on a separate transcript file (parent key → child key in the
   session_key chain, `agent/harness/session/runtime.rs:130-141`).
4. Are checkpointed to `SqlRunLedgerCheckpointer` for replay
   (`Cargo.toml:79-80` comment).

---

## 4. The 3-layer memory system

```
┌──────────────────────────────────────────────────────────────────────┐
│ Layer 1: memory_store  (src/openhuman/memory_store/)                 │
│ ────────────────────────────────────────────────────────────────────│
│  - SQLite (rusqlite = 0.40, vendored)                                │
│  - Vendored tinycortex (vendor/tinycortex/)                          │
│  - 1 collection per MemoryType (CONVERSATIONAL aliases "conversations")│
│  - Subsystems:                                                      │
│      chunks/    text chunks                                          │
│      vectors/   embedding storage                                    │
│      entities/  extracted entities (people, projects)                │
│      trees/     summary-tree persistence                             │
│      kv/        key-value                                            │
│      content/   full content + Obsidian vault export                 │
│      safety/    prompt-injection redaction                           │
│      unified/   facade re-export                                     │
└──────────────────────────────────────────────────────────────────────┘
                                  ▲  writes leaves
                                  │
┌──────────────────────────────────────────────────────────────────────┐
│ Layer 2: memory_tree  (src/openhuman/memory_tree/)                  │
│ ────────────────────────────────────────────────────────────────────│
│  Kind-agnostic summary-tree mechanics. 3 tree kinds:                 │
│      source-tree   (per integration: gmail, slack, …)               │
│      global-tree   (user's whole life)                               │
│      topic-tree    (auto-spawned by hotness)                         │
│  Sub-modules:                                                        │
│      tree/             append + cascade seal + flush                 │
│      summarise.rs      L_n → L_{n+1} text via LLM (temperature 0)   │
│      retrieval/        walk, drill_down, fetch_leaves, query_*       │
│      score/            scoring, embedding, entity extraction         │
│      nlp/              keyword extraction                           │
│      graph/            tree graph                                    │
│      tree_runtime/     LLM-callable summariser                       │
│      io.rs             TreeWriteRequest/TreeReadRequest (pure types)│
└──────────────────────────────────────────────────────────────────────┘
                                  ▲  ingestion paths
                                  │
┌──────────────────────────────────────────────────────────────────────┐
│ Layer 3: memory_sources + memory_sync  (memory_sources/, memory_sync/)│
│ ────────────────────────────────────────────────────────────────────│
│  - Per-integration adapters (Gmail/Slack/Notion/...)                 │
│  - memory_sync/composio/periodic.rs:81  TICK_SECONDS = 1200 (20 min)│
│  - memory_sync/workspace/periodic.rs:48 TICK_SECONDS = 1200         │
│  - memory_sync/composio/bus.rs:628 "scheduler (20-min tick)"         │
│  - Scheduler-gate throttles on battery / charging                    │
│  - Per-provider sync_interval_secs is the LOWER bound                │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.1 Ingestion → storage → summarisation flow

```
1. Tick (every 20 min)        memory_sync/composio/periodic.rs:81
         │
         ▼
2. For each active Composio connection:
   - Look up the matching native provider
   - If sync_interval_secs elapsed → fetch
         │
         ▼
3. Provider fetches data (HTTP API)  (gmail, slack, calendar, …)
         │
         ▼
4. tinycortex pipeline:
   - chunk
   - embed
   - extract entities
   - score relevance
         │
         ▼
5. Write to memory_sources tree leaves  (Layer 3 → Layer 2)
         │
         ▼
6. Bucket-seal cascade (memory_tree/tree/bucket_seal.rs):
   - When a bucket reaches N leaves, seal it
   - Trigger a summarise() call to the LLM
   - Promote the summary to a leaf at the next level
   - Recurse upward
         │
         ▼
7. Eventually, a global-tree leaf gets sealed → context assembled
   for the next user turn (Lane A — preflight on first turn)
         │
         ▼
8. Obsidian vault export:  (memory_store/content/obsidian.rs)
   - Drop a .obsidian/graph.json + .obsidian/types.json (idempotent)
   - Write the sealed tree's leaves as .md files into the vault
   - User can open the vault in Obsidian and edit leaves
```

### 4.2 The Obsidian vault, concretely

```
$ cat src/openhuman/memory_store/content/obsidian.rs:1-26
//! Obsidian vault defaults.
//!
//! When the memory_tree content root is first populated we drop a small
//! `.obsidian/` directory into it so a user opening the vault gets the
//! intended graph-view colour mapping (one colour per summary level) and
//! the front-matter type hints (`time_range_*` as `date`, `sealed_at` as
//! `datetime`) without any manual configuration.
//!
//! The bundled defaults live as static files under `obsidian_defaults/`
//! and are baked into the binary via `include_str!`. We only stage them
//! when the corresponding `.obsidian/<file>` doesn't already exist —
//! never overwrite a file the user has tweaked.
```

So the vault is **editable by the user** (it's a real Obsidian vault) and
OpenHuman respects user edits (idempotent staging, never overwrites).

---

## 5. Channels and the Composio managed-proxy

```
┌──────────────────────────────────────────────────────────────────────┐
│ External user-facing channels  (src/openhuman/channels/providers/)   │
│ ────────────────────────────────────────────────────────────────────│
│  dingtalk.rs  discord.rs  email_channel.rs  imessage.rs  irc.rs      │
│  lark.rs  linq.rs  mattermost.rs  qq.rs  signal.rs  slack.rs         │
│  telegram.rs  web.rs  whatsapp.rs  whatsapp_web.rs  yuanbao.rs      │
│                                                                      │
│  Plus: src/openhuman/meet/  (Google Meet auto-join, separate module) │
│  Plus: src/openhuman/desktop_companion/  (mascot in Meet)            │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Composio managed proxy  (src/openhuman/composio/)                    │
│ ────────────────────────────────────────────────────────────────────│
│  All calls proxied through:                                          │
│      https://api.tinyhumans.ai/agent-integrations/composio/*         │
│  Per: src/openhuman/composio/client.rs:1-9                           │
│                                                                      │
│  "Direct mode" exists for self-hosted / BYO Composio:                │
│      composio/direct_auth/  (per-user Composio v3 tenant)            │
│      memory_sync/composio/periodic.rs:18-31                          │
│                                                                      │
│  20-min sync tick:                                                   │
│      memory_sync/composio/periodic.rs:81  TICK_SECONDS = 1200        │
│      memory_sync/workspace/periodic.rs:48 TICK_SECONDS = 1200        │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ tinyhumans.ai backend  (NOT in repo, proprietary)                    │
│ ────────────────────────────────────────────────────────────────────│
│  - Composio v3 API forwarder                                         │
│  - LLM inference (8 tier hints → real models)                        │
│  - Sentry sink                                                       │
│  - tiny.place A2A @handles                                           │
│  - Tauri updater feed                                                │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.1 Why managed proxy (not direct)

The README positions OpenHuman as a "**privacy**" product. By proxying
Composio through their own backend, OpenHuman:

- **Avoids storing Composio credentials on the user's machine** in
  managed mode.
- Can **rate-limit and audit** all calls centrally.
- Can **fall back to the next provider** at the managed layer if the
  third-party is down.
- Provides a **stable interface** (`/agent-integrations/composio/*`) so
  the openhuman-core client is decoupled from Composio's v3 evolution.

The cost: managed mode **requires the backend to be up** for any
Composio-mediated integration. Self-hosted users / privacy-purists
can switch to `direct_mode` and self-host the Composio side.

---

## 6. Sandbox: 3 backends, 1 trait

```
RuntimeAdapter (src/openhuman/agent/host_runtime.rs:21-29)
─────────────────────────────────────────────────────────
trait RuntimeAdapter: Send + Sync {
    fn name(&self) -> &str;
    fn has_shell_access(&self) -> bool;
    fn has_filesystem_access(&self) -> bool;
    fn storage_path(&self) -> PathBuf;
    fn supports_long_running(&self) -> bool;
    fn memory_budget(&self) -> u64 { 0 }
    fn build_shell_command(&self, command: &str, workspace_dir: &Path)
        -> anyhow::Result<tokio::process::Command>;
}

Implementations:
─────────────────────────────────────────────────────────
NativeRuntime (host_runtime.rs)         — runs on host, no jail
DockerRuntime  (sandbox/docker.rs)      — docker exec
LocalRuntime   (sandbox/ + cwd_jail/)   — Landlock/Seatbelt/AppContainer

SandboxBackendKind (src/openhuman/sandbox/types.rs:12-22)
─────────────────────────────────────────────────────────
None   (default)  — no jail, host shell
Local  — OS-level jail (Landlock/Seatbelt/AppContainer)
Docker — container isolation
```

`src/openhuman/sandbox/types.rs:131-149`:
```rust
pub const ELEVATED_TOOLS: &[&str] = &[
    "git_operations",
    "install_tool",
    …
];
```

The **elevated op** path lets a tool request explicit host access out of
the sandbox, with the request reason logged for audit.

### 6.1 Per-agent sandbox mode

`src/openhuman/agent_registry/agents/code_executor/agent.toml:11`:
```
sandbox_mode = "sandboxed"
```

So each agent definition picks a `sandbox_mode` in its TOML, and the
runtime resolves the matching `SandboxPolicy` (per-agent, per-session).
The `code_executor` agent (full lifecycle code work) runs sandboxed; the
`orchestrator` runs with default host access for orchestration.

---

## 7. The 8-tier model router

`src/openhuman/inference/provider/factory.rs:101-117`:
```
hint/tier     →   model       →   role          →  provider
────────────────────────────────────────────────────────────
reasoning        MODEL_REASONING_V1       "reasoning"     (by tier default)
reasoning_quick  MODEL_REASONING_QUICK_V1 "chat"          (cheap)
chat             MODEL_CHAT_V1            "chat"          (default)
agentic          MODEL_AGENTIC_V1         "agentic"       (orchestration)
burst            MODEL_BURST_V1           "burst"         (fast fan-out)
coding           MODEL_CODING_V1          "coding"        (sub-agent code)
vision           MODEL_VISION_V1          "vision"        (image+multimodal)
summarization    MODEL_SUMMARIZATION_V1   "summarization" (memory_tree)
subconscious     MODEL_CHAT_V1            "subconscious"  (background)
```

Each tier can be pinned to a specific real model. With the managed
backend, the tier names are virtual and the backend maps them. With BYOK,
you point each tier at a slug in `cloud_providers`. The `reliable.rs`
layer adds **per-tier fallback chains** so a transient 429 on tier X
falls through to tier Y (e.g. burst → chat).

---

## 8. Subconscious: the background loop

`src/openhuman/subconscious/` — the README's "**a background loop that
diffs your world, advances your goals, and writes your morning
briefing**".

```
src/openhuman/subconscious/
├── mod.rs          # exports SubconsciousInstance, SubconsciousKind, factory
├── instance.rs     # per-user SubconsciousInstance (the "engine" runtime)
├── session.rs      # LongLivedSession (idempotent background turns)
├── factory.rs      # make_subconscious(), SubconsciousKind
├── registry.rs     # the live set of running subconscious instances
├── provider.rs     # provider selection (always light/cheap)
├── profile.rs      # SubconsciousProfile (Observation, Reflection)
├── profiles/
│   └── memory.rs   # the memory-instance: diffs memory, writes reflections
├── store.rs        # persistent state across restarts
├── heartbeat/      # periodic tick (battery-aware)
├── agent/          # the subconscious sub-agent type
├── decision_log.rs # decision audit
├── source_chunk.rs # in-memory chunk for diffing
└── user_thread.rs  # per-user thread budget
```

`subconscious/mod.rs:25-32`:
```rust
pub use factory::{make_subconscious, SubconsciousKind};
pub use instance::SubconsciousInstance;
pub use profile::{Observation, Reflection, SubconsciousProfile};
pub use profiles::memory::memory_instance;
```

The `memory_instance` is the **default** subconscious — it diffs the
memory tree, detects new patterns, advances long-term goals, and writes
the morning briefing. Other `SubconsciousKind` variants could be added
(e.g. a code-watcher, a meeting-prepper).

---

## 9. End-to-end message flow (chat)

```
USER TYPES IN CHAT BOX (or pastes an image / attaches a file)
                  │
                  ▼
React component dispatches an action in app/src/store/
                  │
                  ▼
Tauri command: invoke('chat_send', { messages, attachments, … })
                  │
                  ▼
app/src-tauri/src/core_rpc.rs forwards to the core subprocess
                  │
                  ▼
openhuman-core receives the JSON-RPC payload via axum (src/api/rest.rs)
                  │
                  ▼
JSON-RPC dispatch (src/core/jsonrpc.rs) → method='chat.send'
                  │
                  ▼
Chat route builds an Agent (or reuses the session's Agent)
                  │
                  ▼
Agent::turn(user_message)  — §3 above
                  │
                  ▼
Result streamed back over Socket.IO (src/api/socket.rs) as
an AgentProgress event stream:
   TurnStarted → ToolStarted(name) → ToolOutput(…) → ToolFinished →
   TextDelta(text_chunk) → TextDelta(…) → …
                  │
                  ▼
TS webview's <AgentProgress> component renders deltas live
(mascot speaks TTS chunks via Piper; animation via Rive)
                  │
                  ▼
TurnCompleted → transcript persisted to memory_store
                  │
                  ▼
If thresholds met (3-stage archivist), background archivist sub-agent
spawns to update MEMORY.md, plus transcript_ingestion to write durable
conversational memory.
```

---

## 10. End-to-end meeting flow (Meet auto-join)

```
Calendar event from Google Calendar (memory_sync/calendar pulls)
                  │
                  ▼
agent_meetings/upcoming.rs detects a meeting starting in N minutes
                  │
                  ▼
agent_meetings/ops.rs schedules an auto-join
                  │
                  ▼
Tauri host (app/src-tauri/src/meet_call/) drives the headless browser
(Chromium Embedded Framework — CEF, see app/src-tauri/src/cef_*.rs)
                  │
                  ▼
Browser joins the Meet URL silently as a hidden participant
                  │
                  ▼
Live transcript (Whisper, in-process via whisper-rs) streamed to core
                  │
                  ▼
meet_agent receives transcript chunks, detects questions
("Hey [name], what do you think?") and answers by name
                  │
                  ▼
agent_meetings/in_call.rs surfaces "raise hand" / "leave meeting" intents
                  │
                  ▼
agent_meetings/summary.rs writes a post-call summary with action items
to memory_store + optional .ics follow-up events
```

This is the **only** video-meeting flow implemented; the README's claim
of "**Zoom, Teams, and Webex**" is **not in the code**.

---

## 11. Build, distribution, and update

```
$ ls .github/workflows/
android-compile.yml    ios-appstore.yml         release-staging.yml
build-ci-image.yml     ios-compile.yml          tauri-cef-pin-guard.yml
build-desktop.yml      pr-quality.yml           test.yml
ci-full.yml            promote-main-to-release.yml  test-reusable.yml
ci-lite.yml            release-notes-preview.yml
e2e-agent-review.yml   release-packages.yml
e2e-playwright.yml     release-production.yml
e2e-reusable.yml
e2e.yml

$ cat tauri.conf.json (bundle targets excerpt)
"targets": ["app", "dmg", "deb", "nsis", "msi", "appimage"]

$ cat tauri.conf.json (updater excerpt)
"updater": {
  "active": true,
  "pubkey": "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IDc0OTREMjkxREFCNUIzRTEK…",
  "endpoints": [
    "https://github.com/tinyhumansai/openhuman/releases/latest/download/latest.json"
  ]
}
```

Three release lanes:
1. **Desktop** — `build-desktop.yml` → Tauri bundles for macOS (.app/.dmg),
   Linux (.deb/.AppImage), Windows (.msi/.nsis).
2. **Mobile** — `ios-appstore.yml` (Fastlane → TestFlight/App Store),
   `android-compile.yml` (Tauri Mobile).
3. **Self-hosted core** — `docker-compose.yml` for headless cloud deploy.

Auto-update is wired via Tauri's official updater plugin pointing at
GitHub Releases (minisign signature embedded in `tauri.conf.json`).

---

## 12. Security & privacy

```
┌──────────────────────────────────────────────────────────────────────┐
│ ENCRYPTION (src/openhuman/encryption/)                                │
│ ────────────────────────────────────────────────────────────────────│
│  KDF: Argon2id                       Cargo.toml:127  argon2 = "0.5"   │
│  AEAD: ChaCha20-Poly1305              Cargo.toml:157  chacha20poly1305│
│  Key agreement: X25519                Cargo.toml:162  x25519-dalek   │
│  HKDF: RFC 5869                      Cargo.toml:163  hkdf            │
│  Zeroize: wipe on drop                Cargo.toml:161  zeroize         │
│  Master key in OS keyring             Cargo.toml:217  keyring (3)     │
│      macOS Keychain / Windows Credential Manager / Linux Secret      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ APPROVAL GATE (src/openhuman/approval/)                              │
│ ────────────────────────────────────────────────────────────────────│
│  TurnOrigin task-local (src/openhuman/agent/turn_origin.rs)           │
│  Per-agent tool_policy (src/openhuman/agent_tool_policy/)             │
│  ElevatedOp escape hatch (src/openhuman/sandbox/types.rs:131)         │
│  Origin-aware: web/chat vs. channel vs. subconscious vs. cron vs. CLI│
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ SENTRY SCRUBBING (src/main.rs:50-340)                                 │
│ ────────────────────────────────────────────────────────────────────│
│  before_send filter pipeline:                                        │
│   - drop transient HTTP failures (429/408/502/503/504)               │
│   - drop all-providers-exhausted (real outages still go through)     │
│   - drop backend errorCode events (F2/F4)                            │
│   - drop transient streaming transport blips (F7)                    │
│   - drop budget-exhausted 400s, insufficient-credits 402s            │
│   - drop max-iterations cap events                                   │
│   - drop session-expired events                                      │
│   - scrub Bearer / api_key / sk-* patterns                           │
│   - strip server_name (hostname)                                     │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ PROMPT INJECTION (src/openhuman/prompt_injection/)                    │
│ ────────────────────────────────────────────────────────────────────│
│  enforce_prompt_input() called in agent/harness/session/runtime.rs:17│
│  Per-turn gate; uses PromptEnforcementContext + Action enums          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 13. Module dependency graph (key edges)

```
                    ┌────────────────────┐
                    │  src/main.rs       │   Sentry + CLI
                    └────────┬───────────┘
                             ▼
                    ┌────────────────────┐
                    │  src/lib.rs        │   pub mod api; pub mod core;
                    └────────┬───────────┘   pub mod openhuman; pub mod rpc;
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   ┌────────┐         ┌────────────┐         ┌────────────┐
   │  api/  │ ◄─────► │   core/    │ ◄─────► │ openhuman/ │
   │ rest   │         │ runtime    │         │            │
   │ socket │         │ event_bus  │         │  133 mods  │
   │ jwt    │         │ jsonrpc    │         │            │
   └────────┘         │ observ.    │         └────────────┘
        ▲             │ shutdown   │              │
        │             └────────────┘              │
        │                                         │
        └─────────────────────────────────────────┘
                  (one-way: api/ → openhuman/)
```

The `api/` layer (HTTP/Socket.IO) is **above** `core/` (runtime) and
`openhuman/` (domain). The domain does not depend on api/. The runtime
composes the domain.

```
openhuman/agent/           ── depends on ──►  openhuman/tinyagents/
openhuman/agent_registry/  ── depends on ──►  openhuman/agent/
openhuman/inference/       ── depends on ──►  (vendored tinyagents for ChatModel trait)
openhuman/memory/          ── depends on ──►  openhuman/memory_tree/ ─► openhuman/memory_store/ ─► vendored tinycortex
openhuman/memory_tree/     ── depends on ──►  openhuman/memory_store/
openhuman/memory_sync/     ── depends on ──►  openhuman/memory_sources/, openhuman/composio/
openhuman/sandbox/         ── depends on ──►  openhuman/cwd_jail/, openhuman/sandbox/docker.rs
openhuman/channels/        ── depends on ──►  openhuman/composio/, openhuman/integrations/
openhuman/subconscious/    ── depends on ──►  openhuman/memory/, openhuman/inference/
openhuman/agent/host_runtime.rs  ── depends on ──► openhuman/config/
openhuman/voice/           ── depends on ──►  openhuman/config/, vendored whisper-rs
```

No cycles; clean dependency direction.

---

## 14. Where to read more

| Topic | File |
|---|---|
| Embeddable core API | `src/lib.rs:25-27` |
| Agent turn lifecycle | `src/openhuman/agent/harness/session/turn/core.rs:141-150` |
| LLM provider factory | `src/openhuman/inference/provider/factory.rs` |
| 8-tier model router | `src/openhuman/inference/provider/factory.rs:101-117` |
| Reliable provider layer | `src/openhuman/inference/provider/reliable.rs` |
| 3-layer memory | `src/openhuman/memory_store/`, `src/openhuman/memory_tree/`, `src/openhuman/memory_sources/`, `src/openhuman/memory_sync/` |
| 20-min sync tick | `src/openhuman/memory_sync/composio/periodic.rs:81` |
| Summary tree engine | `src/openhuman/memory_tree/summarise.rs` |
| Obsidian vault | `src/openhuman/memory_store/content/obsidian.rs` |
| 17 channels | `src/openhuman/channels/providers/mod.rs:1-23` |
| Composito managed proxy | `src/openhuman/composio/client.rs:1-9` |
| Sandbox backends | `src/openhuman/sandbox/types.rs:12-22` |
| Subconscious | `src/openhuman/subconscious/mod.rs:25-32` |
| 33 sub-agents | `src/openhuman/agent_registry/agents/` |
| Sentry scrubbing | `src/main.rs:50-340` |
| Encryption | `src/openhuman/encryption/` + `Cargo.toml:127-163` |
| Tauri config | `app/src-tauri/tauri.conf.json` |
| Tauri windows | `app/src-tauri/src/mascot_native_window.rs`, `notch_window.rs` |
| Mascot Rive | `tiny_mascot.riv` + `app/src/components/mascot/` |
| CI/CD | `.github/workflows/` (20 files) |
| Docker self-host | `docker-compose.yml` + `Dockerfile` |
| License | `LICENSE:1-3` (GPL-3.0) |

---

*Architecture doc completed 2026-07-13.*
*Source commit: 407fd8edd75f155f345291ffa1e5c9e8af31fd75.*
*Companion: `openhuman-code-audit.md` (5,000+ words, 80+ verified citations).*
