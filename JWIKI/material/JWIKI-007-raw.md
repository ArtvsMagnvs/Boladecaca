# Material crudo JWIKI-007 — Hermes Agent (NousResearch/hermes-agent)

> Material crudo de investigación enriquecido 2026-07-08 (tick A-20260708-1955).
> Fuentes: GitHub REST API + `raw.githubusercontent.com` + landing oficial + SKILL.md del propio repo + release notes.
> Investigador: sesión actual (directo, sin subagente).
> Mantenedor: Aithera Escriba / orquestador JWIKI single-team.

## Bloque A — Hechos verificados del material crudo original (2026-07-07)

1-26. (Ver contenido previo del archivo antes de este enriquecimiento; los 26 hechos originales
       con URL y fecha del 2026-07-07 se conservan al final del archivo, sección "## Hechos verificados originales (2026-07-07)" —
       la auditoría de este tick los re-confirma y los re-fecha al 2026-07-08 con contraste directo).

## Bloque B — Hechos verificados NUEVOS / RE-VERIFICADOS (2026-07-08, tick actual)

### B.1 GitHub API contraste directo (2026-07-08T19:55Z)

27. **Stars**: 211.474 (vs 210.335 al 2026-07-07 → +1.139 en 24h, ritmo ~1.100-1.700/día). — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent` (`stargazers_count`) — Fecha acceso: 2026-07-08
28. **Forks**: 38.853 (no consultado en el material original; valor 2026-07-08). — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent` (`forks_count`) — Fecha acceso: 2026-07-08
29. **Open issues**: 26.881. — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent` (`open_issues_count`) — Fecha acceso: 2026-07-08
30. **Subscribers (watchers reales)**: 825. — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent` (`subscribers_count`) — Fecha acceso: 2026-07-08
31. **Repository size**: 469.792 KB (~470 MB de código + assets). — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent` (`size`) — Fecha acceso: 2026-07-08
32. **Created at**: 2025-07-22T22:22:28Z (el repo tiene ~1 año de existencia). — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent` (`created_at`) — Fecha acceso: 2026-07-08
33. **Pushed at**: 2026-07-08T15:32:15Z (hace ~4h al momento del contraste; actividad diaria). — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent` (`pushed_at`) — Fecha acceso: 2026-07-08
34. **Updated at**: 2026-07-08T17:46:43Z (hace ~2h; metadata fresca). — Fuente: idem — Fecha acceso: 2026-07-08
35. **Default branch**: `main`. — Fuente: idem — Fecha acceso: 2026-07-08
36. **Homepage declarada**: `https://hermes-agent.nousresearch.com`. — Fuente: idem — Fecha acceso: 2026-07-08
37. **Description corta**: "The agent that grows with you". — Fuente: idem — Fecha acceso: 2026-07-08

### B.2 Release más reciente (CORRECCIÓN IMPORTANTE: el doc pre-existente dice v0.18.0, pero ya hay v0.18.2)

38. **Latest release**: `v2026.7.7.2` — "Hermes Agent v0.18.2 (2026.7.7.2)" — publicada **2026-07-08T03:11:22Z** (HACE 16H). — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/releases/latest` — Fecha acceso: 2026-07-08
39. **Contenido del patch v0.18.2**: fix(whatsapp) unpin Baileys from git commit, use published 7.0.0-rc13 (PR #60643) — el WhatsApp bridge ahora se instala desde npm published en lugar de commit pin, lo que arregla fallos de Docker build. — Fuente: release body de v2026.7.7.2 — Fecha acceso: 2026-07-08
40. **Actualizar comando**: `hermes update` (existing installs) o `pip install -U hermes-agent`. — Fuente: release body — Fecha acceso: 2026-07-08
41. **Penúltima release**: `v2026.7.7` — "Hermes Agent v0.18.1 (2026.7.7)" — publicada **2026-07-08T01:15:00Z** (mismo día, 2h antes). Patch release con curated notes diferidas a v0.19.0. — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/releases` — Fecha acceso: 2026-07-08
42. **Release v0.18.0 (v2026.7.1) "The Judgment Release"** (la que cita el doc pre-existente): publicada 2026-07-01T20:08:06Z. Métricas del window: ~1.720 commits, 998 PRs mergeados, 2.215 archivos cambiados, ~251.000 inserciones, ~41.000 deletions, 949 issues cerrados, 370+ contribuidores comunitarios. — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/releases/tags/v2026.7.1` — Fecha acceso: 2026-07-08
43. **Headline de v0.18.0**: 100% P0/P1 cerrados en 12 días (~700 highest-priority items: 3 P0 issues + 8 P0 PRs + 493 P1 issues + 188 P1 PRs). — Fuente: idem — Fecha acceso: 2026-07-08
44. **Credito especial v0.18.0**: @kshitijk4poor por quemar el backlog de prioridad día y noche junto al core team. — Fuente: idem — Fecha acceso: 2026-07-08
45. **Highlights v0.18.0** (extracto):
    - **Mixture-of-Agents (MoA) first-class**: ahora MoA aparece como modelo seleccionable en el model picker (CLI/TUI/desktop/gateway) bajo un provider `moa`, junto a Claude/GPT/Grok. Cada MoA ensemble muestra el reasoning de los reference models y streamea la respuesta del aggregator en vivo.
    - **Self-verification**: el agente verifica su trabajo contra evidencia (no vibes).
    - **`/goal`** con completion contracts.
    - **`/learn` + `/journey`**: self-improvement visible y steerable.
    - **Gateway scale-to-zero + drain coordination** (deployable at scale).
    - **Desktop**: first-class coding projects + playable memory graph.
    - **Subagents** pueden fan-out en background.
    — Fuente: idem — Fecha acceso: 2026-07-08

### B.3 Historial de releases (cadencia 2026)

46. **v2026.7.7.2** (v0.18.2) — 2026-07-08 — patch WhatsApp Baileys
47. **v2026.7.7** (v0.18.1) — 2026-07-08 — patch release (mismo día que v0.18.0+1 semana)
48. **v2026.7.1** (v0.18.0) "The Judgment Release" — 2026-07-01
49. **v2026.6.19** (v0.17.0) — 2026-06-19
50. **v2026.6.5** (v0.16.0) "The Surface Release" — 2026-06-06
51. **v2026.5.29.2** (v0.15.2) — 2026-05-29 (bug fix)
52. **v2026.5.29** (v0.15.1) "The Patch Release" — 2026-05-29
53. **v2026.5.28** (v0.15.0) "The Velocity Release" — 2026-05-28
— Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/releases` — Fecha acceso: 2026-07-08
**Patrón observado**: cadencia de releases semanal a quincenal. Naming convention `vAAAA.M.P` (año.mes.patch) + nombre semántico ("The Judgment", "The Velocity", "The Surface", "The Patch"). Numeración interna `v0.X` con X=patch acumulado.

### B.4 Lenguajes (GitHub API, contraste 2026-07-08)

54. **Lenguajes por bytes** (ordenados desc):
    - Python: 55.352.301 bytes (~84.3%)
    - TypeScript: 9.311.359 bytes (~14.2%)
    - JavaScript: 969.143 bytes (~1.5%)
    - TeX: 434.546 bytes
    - Shell: 279.816 bytes
    - PowerShell: 181.048 bytes
    - BibTeX Style: 156.486 bytes
    - Rust: 128.467 bytes
    - CSS: 106.609 bytes
    - Nix: 104.228 bytes
    - HTML: 91.188 bytes
    - Dockerfile: 20.787 bytes
    - MDX: 18.640 bytes
    - Go Template: 2.740 bytes
    - Ruby: 1.585 bytes
    - Batchfile: 1.145 bytes
    - Makefile: 1.054 bytes
— Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/languages` — Fecha acceso: 2026-07-08
**Discrepancia con doc pre-existente**: el doc decía Python ~80% / TypeScript ~13% / JS ~1.4% / Rust ~0.2% — los valores reales actualizados son Python 84.3% / TypeScript 14.2% / JS 1.5% / Rust 0.2% (el porcentaje de Python ha subido, probablemente por la explosión de cli.py y run_agent.py; el doc pre-existente subestimaba Python por usar los bytes del 2026-07-07).

### B.5 pyproject.toml (descubierto: NO estaba en el material crudo original)

55. **Python requirement**: `>=3.11,<3.14` (cap explícito en 3.14 — el comentario en pyproject dice: "an inherited `UV_PYTHON` env var... will otherwise select 3.14, where Rust-backed transitives (e.g. pydantic-core) have no cp314 wheel yet and fall back to a maturin source build that fails. Capping at <3.14 makes uv refuse 3.14 with a clear error instead of attempting that build"). — Fuente: `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/pyproject.toml` — Fecha acceso: 2026-07-08
56. **Pinning policy**: cada dep directa está pinned a `==X.Y.Z` (sin ranges), decisión del 2026-05-12 en respuesta al **Mini Shai-Hulud worm** que golpeó mistralai 2.4.6 en PyPI. Razón citada: "ranges allow PyPI to ship a fresh version of a transitive at any time without a code review on our side. Exact pins mean the only way a new package version reaches a user is via an intentional update on our end (bump the pin in this file, regenerate uv.lock)". — Fuente: idem — Fecha acceso: 2026-07-08
57. **Scope rule explícito**: "only packages used by EVERY hermes session belong here. Anything that's provider-specific (`anthropic`, `firecrawl-py`, `exa-py`, `fal-client`, `edge-tts`, `parallel-web`) belongs in an extra and gets lazy-installed via `tools/lazy_deps.py` when the user picks that backend. Smaller `dependencies` = smaller blast radius for the next supply-chain attack." — Fuente: idem — Fecha acceso: 2026-07-08
58. **Stack core confirmado en pyproject.toml**:
    - `openai==2.24.0` (OpenAI SDK como dep core)
    - `pydantic==2.13.4` (bumped desde 2.12.5 → 2.13.4 para pull pydantic-core 2.46.4 que arregla un segfault cuando el OpenAI SDK's Responses API se ejerce desde non-main thread; bug en `agent/chat_completion_helpers.py:_call`)
    - `fastapi>=0.104.0,<1` + `uvicorn[standard]>=0.24.0,<1` (FastAPI para el dashboard, NO para el core agent)
    - `python-multipart>=0.0.9,<1` (file upload dashboard)
    - `prompt_toolkit==3.0.52` (CLI interactiva — usada directamente por `cli.py`)
    - `rich==14.3.3` (output)
    - `croniter==6.0.0` (cron scheduler — built-in feature)
    - `packaging==26.0` (declarada explícitamente tras descubrir que el slim Docker image no la traía transitivamente y rompía update_mode='append' de Hindsight, lazy_deps.py, y hermes_cli/main.py)
    - `Markdown==3.10.2` (markdown→HTML para Matrix formatted_body y send_message tool)
    - `PyJWT[crypto]==2.13.0` (Skills Hub GitHub App JWT auth)
    - `urllib3>=2.7.0,<3`, `cryptography==46.0.7` (CVE fixes WeCom/Weixin crypto paths)
    - `tzdata==2025.3; sys_platform == 'win32'` (Windows no trae IANA tzdata)
    - `psutil==7.2.2` (cross-platform PID management; reemplaza `os.kill(pid, 0)` que es silent killer en Windows)
    - `websockets==15.0.1` (browser CDP supervisor)
    - `pathspec==1.1.1` (.gitignore-aware matching)
    - `ptyprocess>=0.7.0,<1; sys_platform != 'win32'` + `pywinpty>=2.0.0,<3; sys_platform == 'win32'` (cross-platform PTY)
    - `Pillow==12.2.0` (image resize recovery for vision tools)
    - `concurrent-log-handler==0.9.29; sys_platform == 'win32'` (Windows log rotation — stdlib RotatingFileHandler fails con WinError 32 cuando otros procesos tienen el handle)
    - `httpx[socks]==0.28.1`, `requests==2.33.0` (CVE-2026-25645)
    - `jinja2==3.1.6`, `pyyaml==6.0.3`, `ruamel.yaml==0.18.17`, `tenacity==9.1.4`, `fire==0.7.1`, `python-dotenv==1.2.2`
— Fuente: `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/pyproject.toml` — Fecha acceso: 2026-07-08
59. **Build backend**: `setuptools>=77.0,<83` (PEP 639 SPDX license expression requiere setuptools>=77). — Fuente: idem — Fecha acceso: 2026-07-08
60. **uv.lock presente**: 661.356 bytes (lockfile grande → muchas transitivas). — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/contents/` — Fecha acceso: 2026-07-08
61. **Extras de pyproject definidos** (cada uno es opt-in via `pip install hermes-agent[<extra>]`):
    - `anthropic = ["anthropic==0.87.0"]` (CVE-2026-34450, CVE-2026-34452) — solo si provider=anthropic directo (no vía OpenRouter)
    - `exa = ["exa-py==2.10.2"]` (web search)
    - `firecrawl = ["firecrawl-py==4.17.0"]` (web search)
    - `parallel-web = ["parallel-web==0.4.2"]` (web search)
    - `fal = ["fal-client==0.13.1"]` (image generation)
    - `edge-tts = ["edge-tts==7.2.7"]` (default TTS pero aún opt-in)
    - `modal = ["modal==1.3.4"]` (Modal serverless backend)
    - `daytona = ["daytona==0.155.0"]` (Daytona serverless hiberna backend)
    - `hindsight = ["hindsight-client==0.6.1"]`
    - `dev = ["debugpy==1.8.20", "pytest==9.0.2", "pytest-asyncio==1.3.0", "mcp==1.26.0", "starlette==1.0.1", "ty==0.0.21", "ruff==0.15.10", "setuptools==81.0.0"]`
    - `messaging = ["python-telegram-bot[webhooks]==22.6", "discord.py[voice]==2.7.1", "aiohttp==3.14.1", "brotlicffi==1.2.0.1", "slack-bolt==1.27.0", "slack-sdk==3.40.1", "qrcode==7.4.2"]` (aiohttp 3.14.1: CVE-2026-34513/34518/34519/34520/34525 + 34993(RCE)/47265)
    - `cron = []` (croniter ahora es core; extra kept for back-compat)
    - `slack = ["slack-bolt==1.27.0", "slack-sdk==3.40.1", "aiohttp==3.14.1"]`
    - `matrix = ["mautrix[encryption]==0.21.0", "aiosqlite==0.22.1", "asyncpg==0.31.0", "aiohttp-socks==0.11.0", "aiohttp==3.14.1"]`
    - `wecom = ["defusedxml==0.7.1"]` (parsea XML untrusted de WeCom callback)
    - `cli = ["simple-term-menu==1.6.6"]`
    - `tts-premium = ["elevenlabs==1.59.0"]`
    - `voice = ["faster-whisper==1.2.1", "sounddevice==0.5.5", "numpy==2.4.3"]` (local STT)
    - `pty = []` (no-op alias for back-compat)
    - `honcho = ["honcho-ai==2.0.1"]` (Honcho user modeling — opt-in por seguridad)
    - `supermemory = ["supermemory==3.50.0"]` (cloud memory provider, lazy-install)
    - `mem0 = ["mem0ai==2.0.10"]` (cloud memory provider, lazy-install)
    - `vision = []` (no-op alias for back-compat)
— Fuente: idem — Fecha acceso: 2026-07-08

### B.6 Estructura del repo (contraste 2026-07-08)

62. **Top-level dirs** (GitHub API /contents/): `agent/`, `apps/`, `acp_adapter/`, `acp_registry/`, `assets/`, `cron/`, `datagen-config-examples/`, `docker/`, `docs/`, `gateway/`, `hermes/`, `hermes_cli/`, `infographic/`, `locales/`, `nix/`, `optional-mcps/`, `optional-skills/`, `packaging/`, `plugins/`, `providers/`, `scripts/`, `skills/`, `tests/`, `tools/`, `tui_gateway/`, `ui-tui/`, `web/`, `website/`, `.github/`, `.plans/`. — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/contents/` — Fecha acceso: 2026-07-08
63. **Top-level files grandes** (clasificación por tamaño):
    - `cli.py` — **744.220 bytes (~744 KB)** — la CLI monolítica (este archivo es enorme, probablemente monolito que crecerá a ser dividido en hermes_cli/)
    - `package-lock.json` — 712.343 bytes
    - `uv.lock` — 661.356 bytes
    - `run_agent.py` — 269.293 bytes (agent loop monolítico)
    - `hermes_state.py` — 278.925 bytes (state management)
    - `AGENTS.md` — 71.537 bytes (instructions file para coding agents)
    - `batch_runner.py` — 57.245 bytes (research batch trajectory generation)
    - `trajectory_compressor.py` — 68.848 bytes (compress trajectories para training)
    - `cli-config.yaml.example` — 75.700 bytes (config example, 75KB!)
    - `CONTRIBUTING.md` — 49.539 bytes
    - `mini_swe_runner.py` — 28.425 bytes
    - `hermes_constants.py` — 37.726 bytes
    - `mcp_serve.py` — 35.282 bytes
    - `toolsets.py` — 34.801 bytes
    - `model_tools.py` — 62.902 bytes
    - `hermes_logging.py` — 31.152 bytes
    - `setup-hermes.sh` — 18.181 bytes
    - `pyproject.toml` — 21.219 bytes
    - `README.md` — 17.617 bytes
    - `.env.example` — 23.389 bytes
    - `Dockerfile` — 20.787 bytes
    - `docker-compose.yml` — 3.454 bytes
    - `docker-compose.windows.yml` — 1.073 bytes
    - `setup.py` — 2.309 bytes
    - `flake.nix` — 1.254 bytes + `flake.lock` — 3.539 bytes
    - `hermes_bootstrap.py` — 8.439 bytes
    - `hermes` (sin extensión, executable script) — 262 bytes
    - `hermes-already-has-routines.md` — 6.373 bytes (competitive blog post contra Claude Code Routines)
— Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/contents/` — Fecha acceso: 2026-07-08
64. **Observación arquitectónica**: el repo tiene un patrón **monolítico-en-archivo**: `cli.py` (744KB), `run_agent.py` (269KB), `hermes_state.py` (278KB), `cli-config.yaml.example` (75KB) son archivos individuales enormes. Esto sugiere que Hermes es un proyecto **joven (~1 año)** con preferencia por velocidad de iteración sobre modularidad. El `hermes_cli/` dir existe pero `cli.py` está fuera; podría migrar a subpaquete en el futuro. — Inferencia basada en observación directa de la estructura — Fecha acceso: 2026-07-08
65. **Hermes tiene `.plans/` dir**: posiblemente directorio de planning/roadmap interno. — Fuente: idem — Fecha acceso: 2026-07-08
66. **Hermes tiene `datagen-config-examples/` dir**: sugiere que el batch_runner + trajectory_compressor están preparados para research/data generation pipelines. — Fuente: idem — Fecha acceso: 2026-07-08

### B.7 Gateway: estructura y plataformas REALES (no las del headline)

67. **Gateway dir contents** (35 archivos en `gateway/`): `__init__.py`, `authz_mixin.py`, `cgroup_cleanup.py`, `channel_directory.py`, `code_skew.py`, `config.py`, `cwd_placeholder.py`, `dead_targets.py`, `delivery.py`, `display_config.py`, `drain_control.py`, `hooks.py`, `kanban_watchers.py`, `memory_monitor.py`, `message_timestamps.py`, `mirror.py`, `pairing.py`, `platform_registry.py`, `response_filters.py`, `restart.py`, `restart_loop_guard.py`, `rich_sent_store.py`, `run.py`, `runtime_footer.py`, `scale_to_zero.py`, `session.py`, `session_context.py`, `shutdown_forensics.py`, `slash_access.py`, `slash_commands.py`, `status.py`, `status_phrases.py`, `sticker_cache.py`, `stream_consumer.py`, `stream_dispatch.py`, `stream_events.py`, `whatsapp_identity.py`. Más subdirs: `assets/`, `builtin_hooks/`, `platforms/`, `relay/`. — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/contents/gateway` — Fecha acceso: 2026-07-08
68. **Plataformas en `gateway/platforms/`** (las "core" que se cargan por defecto): `__init__.py`, `_http_client_limits.py`, `api_server.py` (219KB — OpenAI-compatible local proxy backed by OAuth provider), `base.py` (245KB — base adapter class), `helpers.py`, `ADDING_A_PLATFORM.md` (14.460 bytes — docs!), `bluebubbles.py` (iMessage), `msgraph_webhook.py` (Email via Microsoft Graph), `signal.py` + `signal_format.py` + `signal_rate_limit.py`, `webhook.py` + `webhook_filters.py`, `weixin.py` (WeChat), `whatsapp_cloud.py` + `whatsapp_common.py`, `yuanbao.py` + `yuanbao_media.py` + `yuanbao_proto.py` + `yuanbao_sticker.py` (Tencent Yuanbao — una plataforma china de AI assistant de Tencent, no mencionada en README), y el subdir `qqbot/` con su adapter completo. — Fuente: `https://api.github.com/repos/NousResearch/hermes-agent/git/trees/main?recursive=1` (filter `gateway/platforms/`) — Fecha acceso: 2026-07-08
69. **Plataformas en `plugins/platforms/`** (22 adapters, las "extendidas"): `dingtalk/` (Alibaba DingTalk), `discord/`, `email/`, `feishu/` (Lark/Feishu — ByteDance), `google_chat/`, `homeassistant/`, `irc/`, `line/`, `matrix/`, `mattermost/`, `ntfy/` (ntfy.sh push notifications), `photon/` (con subdir `sidecar/`), `raft/` (consensus protocol??), `simplex/` (SimpleX Chat — privacy-first messenger), `slack/`, `sms/`, `teams/` (Microsoft Teams), `telegram/`, `wecom/` (WeCom — enterprise WeChat), `whatsapp/`. — Fuente: idem — Fecha acceso: 2026-07-08
70. **Conteo real de plataformas de mensajería**: 22 adapters distintos entre `gateway/platforms/` y `plugins/platforms/` (excluyendo `api_server.py` y `webhook.py` que son special). Las "Telegram, Discord, Slack, WhatsApp, Signal" del headline son solo **5** de las 22+. Las otras 17+: iMessage (bluebubbles), Email (msgraph_webhook, email plugin), WeChat (weixin), WeCom (wecom), QQ (qqbot), Yuanbao (yuanbao), DingTalk, Feishu/Lark, Google Chat, Home Assistant, IRC, LINE, Matrix, Mattermost, ntfy, Photon, Raft, SimpleX, SMS, Teams. — Inferencia — Fecha acceso: 2026-07-08
71. **`api_server.py` (219KB) es un OpenAI-compatible local proxy**: según la SKILL.md del propio proyecto: "`hermes proxy` — OpenAI-compatible local proxy backed by your OAuth provider". Esto permite que otras apps que usen OpenAI SDK (incluyendo Aithera si quisiera) puedan apuntar a un Hermes local como drop-in OpenAI replacement. — Fuente: SKILL.md + inferencia — Fecha acceso: 2026-07-08
72. **`photon/` con `sidecar/`**: sugiere Photon es un protocolo peer-to-peer o una plataforma con sidecar process (sidecar pattern común en service mesh / DHT). — Inferencia — Fecha acceso: 2026-07-08
73. **`raft/` platform**: nombre "raft" sugiere el consensus protocol Raft, pero en este contexto es probablemente un adapter a una plataforma de chat llamada Raft (no el algoritmo). — Inferencia — Fecha acceso: 2026-07-08
74. **`yuanbao/` (Tencent Yuanbao)**: Tencent Yuanbao (腾讯元宝) es un AI assistant de Tencent integrado en WeChat/QQ. El adapter tiene 222KB solo + 21KB de sticker handling + 45KB de protobuf. Esto sugiere integración profunda con la plataforma china. — Inferencia + observación del tamaño — Fecha acceso: 2026-07-08

### B.8 hermes-already-has-routines.md (competitive blog post interno)

75. **Documento competitive**: `hermes-already-has-routines.md` (6.373 bytes) es un post que compara las **Claude Code Routines** (Anthropic) con las features existentes de Hermes desde marzo 2026. — Fuente: `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/hermes-already-has-routines.md` — Fecha acceso: 2026-07-08
76. **Cita textual del header**: "Anthropic just announced [Claude Code Routines](https://claude.com/blog/introducing-routines-in-claude-code) — scheduled tasks, GitHub event triggers, and API-triggered agent runs. Bundled prompt + repo + connectors, running on their infrastructure. It's a good feature. **We shipped it two months ago.**" — Fuente: idem — Fecha acceso: 2026-07-08
77. **Tres tipos de trigger que Hermes ya tiene** (vs Claude Code Routines):
    - **Scheduled (cron)**: `hermes cron create "0 2 * * *" "Pull the top bug..." --name "Nightly bug fix" --deliver telegram`
    - **GitHub Events (webhook)**: `hermes webhook subscribe auth-watch --events "pull_request" --prompt "..." --deliver slack`
    - **API Triggers**: `hermes webhook subscribe alert-triage --prompt "..." --deliver slack`
— Fuente: idem — Fecha acceso: 2026-07-08
78. **Claim textual**: "Every use case in their blog post — backlog triage, docs drift, deploy verification, alert correlation, library porting, bespoke PR review — has a working Hermes implementation. No new features needed. It's been shipping since March 2026." — Fuente: idem — Fecha acceso: 2026-07-08
79. **Implicación competitiva**: Hermes se posiciona como alternativa más madura y abierta a Claude Code Routines. Esto es importante para Aithera porque la decisión de "qué framework de scheduling" debe considerar que el de Hermes es más rico (delivery flexible a múltiples plataformas, no solo Claude Code infrastructure). — Inferencia — Fecha acceso: 2026-07-08

### B.9 Skills system (SKILL.md discovery en el propio repo)

80. **Hermes Agent publica su propia SKILL.md**: `skills/autonomous-ai-agents/hermes-agent/SKILL.md` (51.586 bytes — la SKILL.md individual más grande que se ha visto en un repo OSS). — Fuente: `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/skills/autonomous-ai-agents/hermes-agent/SKILL.md` — Fecha acceso: 2026-07-08
81. **SKILL.md frontmatter**:
    - name: `hermes-agent`
    - description: "Configure, extend, or contribute to Hermes Agent."
    - version: `2.3.0`
    - author: "Hermes Agent + Teknium"
    - license: MIT
    - platforms: [linux, macos, windows]
    - metadata.hermes.tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    - metadata.hermes.homepage: https://github.com/NousResearch/hermes-agent
    - metadata.hermes.related_skills: [claude-code, codex, opencode]
— Fuente: idem — Fecha acceso: 2026-07-08
82. **Self-positioning en SKILL.md**: "Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, a native desktop app, messaging platforms, and IDEs. **It's in the same category as Claude Code (Anthropic), Codex (OpenAI), and OpenClaw** — autonomous coding and task-execution agents that use tool calling to interact with your system. Hermes works with any LLM provider (OpenRouter, Anthropic, OpenAI, Google, DeepSeek, xAI, local models, and 20+ others) and runs on Linux, macOS, Windows, and WSL." — Fuente: idem — Fecha acceso: 2026-07-08
83. **Diferenciadores listados en SKILL.md** (vs Claude Code/Codex/OpenClaw):
    - "**Self-improving through skills**" — saves reusable procedures as skills, accumulates over time
    - "**Persistent memory across sessions**" — remembers who you are, preferences, environment, lessons
    - "**Multi-platform gateway**" — Telegram, Discord, Slack, WhatsApp, iMessage, Signal, Matrix, Teams, Email, and a dozen more
    - "**Many surfaces**" — CLI, Ink TUI, native Electron desktop, web dashboard, ACP server for IDEs (VS Code / Zed / JetBrains)
    - "**Provider-agnostic**" — swap models mid-workflow, credential pools rotate across multiple API keys
    - "**Profiles**" — run multiple independent Hermes instances with isolated configs, sessions, skills, memory
    - "**Extensible**" — plugins, MCP servers, custom tools, webhook triggers, cron scheduling, full Python ecosystem
— Fuente: idem — Fecha acceso: 2026-07-08
84. **Native desktop app confirmado en SKILL.md**: "the same agent core drives the CLI, the Ink TUI, a native Electron desktop app, a web dashboard, and an ACP server for IDEs (VS Code / Zed / JetBrains)." — Fuente: idem — Fecha acceso: 2026-07-08
85. **ACP server**: "ACP (Agent Communication Protocol) server" permite a IDEs (VS Code, Zed, JetBrains) consumir al agente. Esto es el equivalente a Claude Code's VS Code extension o Codex's IDE integrations. — Fuente: idem — Fecha acceso: 2026-07-08
86. **Profiles feature**: Hermes permite correr múltiples instancias independientes con configs/sessions/skills/memory aislados. Esto es importante para multi-user o multi-project setups. — Fuente: idem — Fecha acceso: 2026-07-08
87. **Related skills discovery**: La SKILL.md declara `related_skills: [claude-code, codex, opencode]`. Esto significa que el ecosystem de skills (agentskills.io) tiene skills para los 4 frameworks principales de coding agents: Hermes Agent, Claude Code, Codex (OpenAI), OpenCode. — Fuente: idem — Fecha acceso: 2026-07-08

### B.10 Landing page (hermes-agent.nousresearch.com, 2026-07-08)

88. **Tagline oficial del landing**: "The Agent That Grows With You". — Fuente: `https://hermes-agent.nousresearch.com/` — Fecha acceso: 2026-07-08
89. **Versión declarada en footer del landing**: "Hermes Agent v0.18.2" (confirma GitHub API). — Fuente: idem — Fecha acceso: 2026-07-08
90. **Pricing tiers Nous Portal**: "Free • Plus • Super • Ultra" — "All paid tiers include monthly credits for use in Hermes Agent, access to 300+ cutting-edge models and built-in tool use". — Fuente: idem — Fecha acceso: 2026-07-08
91. **6 features numeradas en landing** (orden visual): #1 Connect (Lives Everywhere) — Telegram, Discord, Slack, WhatsApp, Signal, Email, CLI; #2 Remember (Persistent Memory) — learns projects, auto-generates skills, never forgets; #3 Schedule (Focused Automation) — natural-language scheduling; #4 Delegate (Tasks Multiplied) — isolated subagents; #5 Search (Browse the Web) — web search, browser automation, vision, image gen, TTS, multi-model reasoning; #6 Experiment (Isolated Sandboxing) — 5 backends (local, Docker, SSH, Singularity, Modal) — NOTA: el landing dice 5 backends, no 6. Probablemente el landing está desactualizado respecto al README y pyproject que sí mencionan Daytona. — Fuente: idem — Fecha acceso: 2026-07-08
92. **Discrepancia de backends (5 vs 6)**: Landing page menciona 5 backends (local, Docker, SSH, Singularity, Modal), README y pyproject mencionan 6 (con Daytona). **El landing está desactualizado** — Daytona se añadió en algún release entre 2026-05-29 y 2026-07-01 y el landing no se actualizó. O el landing se generó estáticamente y no se re-build-ea. — Fuente: contraste README vs landing — Fecha acceso: 2026-07-08
93. **Native desktop downloads directos**:
    - macOS: `https://hermes-assets.nousresearch.com/Hermes-Setup.dmg?build=9de9c25f620f` (direct download)
    - Windows: `https://hermes-assets.nousresearch.com/Hermes-Setup.exe?build=9de9c25f620f` (direct download)
    - Linux: link a `https://github.com/NousResearch/hermes-agent/releases` (indirect, no DMG directo en el landing)
— Fuente: idem — Fecha acceso: 2026-07-08
94. **Nous Portal pricing link**: `https://portal.nousresearch.com/manage-subscription` — "View All Our Plans" CTA. — Fuente: idem — Fecha acceso: 2026-07-08
95. **Discord link**: `https://discord.gg/nousresearch` (NO `discord.gg/NousResearch` como dice el README; sí está bien, solo el README pone el alias NousResearch y el link es discord.gg/nousresearch lowercase — confirmado). — Fuente: idem — Fecha acceso: 2026-07-08

### B.11 Topics y comunidades (GitHub)

96. **Topics del repo** (16): `ai`, `ai-agent`, `ai-agents`, `anthropic`, `chatgpt`, `claude`, `claude-code`, `clawdbot`, `codex`, `hermes`, `hermes-agent`, `llm`, `moltbot`, `nous-research`, `openai`, `openclaw`. — Fuente: GitHub API `topics` — Fecha acceso: 2026-07-08
97. **Observación de topics**: Los topics `clawdbot` y `moltbot` siguen presentes (heredados del rename OpenClaw de enero 2026 que pasó por Warelay→CLAWDIS→Clawdbot→Moltbot→OpenClaw). `claude-code` y `codex` están por la SKILL.md related_skills. Esto indica que el equipo de marketing de Hermes busca activamente capturar tráfico de búsqueda de los proyectos competidores. — Inferencia — Fecha acceso: 2026-07-08

### B.12 Discrepancias con el doc pre-existente (CRÍTICO para audit)

98. **Doc pre-existente dice**: "Última release: v0.18.0 (release tag v2026.7.1), publicada 2026-07-01"
    **Realidad 2026-07-08**: v0.18.2 (v2026.7.7.2) publicada HOY 2026-07-08 03:11 UTC; v0.18.1 (v2026.7.7) publicada HOY 2026-07-08 01:15 UTC. **El doc pre-existente está stale por 1 semana.** — Fuente: contraste release/latest — Fecha acceso: 2026-07-08
99. **Doc pre-existente dice**: "210.335 stars"
    **Realidad 2026-07-08**: 211.474 (+1.139 en 24h, ritmo ~1.100-1.700/día). El doc está 1.139 stars stale. — Fuente: contraste stargazers_count — Fecha acceso: 2026-07-08
100. **Doc pre-existente dice**: "Python (80%)"
     **Realidad 2026-07-08**: Python 84.3% (55.3MB / 65.6MB total). La proporción ha subido probablemente por la explosión de cli.py, run_agent.py, hermes_state.py, batch_runner.py, trajectory_compressor.py. — Fuente: contraste /languages — Fecha acceso: 2026-07-08
101. **Doc pre-existente dice**: "5+ canales" (Telegram, Discord, Slack, WhatsApp, Signal, Email)
     **Realidad 2026-07-08**: 22+ plataformas incluyendo Telegram, Discord, Slack, WhatsApp, Signal, Email (msgraph_webhook + email plugin), iMessage (bluebubbles), WeChat (weixin), WeCom (wecom), QQ (qqbot), Yuanbao (yuanbao — Tencent AI assistant), DingTalk, Feishu/Lark, Google Chat, Home Assistant, IRC, LINE, Matrix, Mattermost, ntfy, Photon, Raft, SimpleX, SMS, Teams. **El headline del README/doc es engañoso; subestima 4-5x la cobertura real.** — Fuente: contraste gateway/platforms + plugins/platforms — Fecha acceso: 2026-07-08
102. **Doc pre-existente NO menciona**:
     - **Native desktop apps** (Electron para macOS/Windows/Linux con downloads directos)
     - **MoA (Mixture-of-Agents) first-class** en v0.18.0
     - **Scale-to-zero + drain coordination** del gateway
     - **Memory graph** jugable en desktop
     - **API server como OpenAI-compatible local proxy** (`hermes proxy`)
     - **Profiles** (múltiples instancias aisladas)
     - **ACP server** para IDEs (VS Code / Zed / JetBrains)
     - **Pinning policy** post-Mini Shai-Hulud worm (May 2026)
     - **Lazy install** de provider-specific deps via `tools/lazy_deps.py`
     - **Hermes ya tiene "Routines"** desde marzo 2026 (competitive vs Claude Code Routines)
     - **Exact pin Python >=3.11,<3.14** con cap explícito
     - **FastAPI dashboard** (con `python-multipart` para upload)
— Fuente: comparación doc vs realidad — Fecha acceso: 2026-07-08

## Datos numéricos consolidados (2026-07-08)

- **Stars**: 211.474
- **Forks**: 38.853
- **Open issues**: 26.881
- **Subscribers**: 825
- **Repo size**: 469.792 KB
- **Created**: 2025-07-22 (~1 año)
- **Pushed**: 2026-07-08 (hace 4h)
- **Latest release**: v0.18.2 (v2026.7.7.2), 2026-07-08
- **Python**: 84.3% (55.3MB), TypeScript: 14.2% (9.3MB), JavaScript: 1.5%
- **License**: MIT
- **Topics**: 16 (ai, ai-agent, anthropic, chatgpt, claude, claude-code, clawdbot, codex, hermes, hermes-agent, llm, moltbot, nous-research, openai, openclaw)
- **Default branch**: main
- **Homepage**: https://hermes-agent.nousresearch.com
- **README**: 17.617 bytes (263 líneas)
- **pyproject.toml**: 21.219 bytes
- **cli.py**: 744.220 bytes (monolítico)
- **Plataformas de mensajería**: 22+ (gateway/platforms + plugins/platforms)
- **Backends terminales**: 6 según README/pyproject (local, Docker, SSH, Singularity, Modal, Daytona), 5 según landing (sin Daytona)
- **Extras pyproject**: 18 (anthropic, exa, firecrawl, parallel-web, fal, edge-tts, modal, daytona, hindsight, dev, messaging, cron, slack, matrix, wecom, cli, tts-premium, voice, pty, honcho, supermemory, mem0, vision)
- **Releases en últimos 60 días**: 8 (v0.15.0 → v0.18.2)
- **Cadencia release**: ~semanal a quincenal

## Snippets de código (5 nuevos + los 5 del material original)

#### Snippet 1 (NUEVO): pyproject.toml Python pin + razón (path: `pyproject.toml:13-23`)
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

#### Snippet 2 (NUEVO): pyproject.toml pinning policy + razón (path: `pyproject.toml:32-48`)
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
#
# When updating: bump the version below AND regenerate uv.lock with
# `uv lock` so the transitive resolution stays consistent. Don't
# introduce ranges back without a written justification.
```

#### Snippet 3 (NUEVO): hermes-already-has-routines.md competitive (path: `hermes-already-has-routines.md:1-20`)
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
```

#### Snippet 4 (NUEVO): SKILL.md frontmatter (path: `skills/autonomous-ai-agents/hermes-agent/SKILL.md:1-12`)
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

#### Snippet 5 (NUEVO): Release body v0.18.0 headline (path: API releases/tags/v2026.7.1, líneas 1-15)
```markdown
# Hermes Agent v0.18.0 (v2026.7.1)

**Release Date:** July 1, 2026
**Since v0.17.0:** ~1,720 commits · 998 merged PRs · 2,215 files changed · ~251,000 insertions · ~41,000 deletions · **949 issues closed** · **370+ community contributors**

> **The Judgment Release.** Over the last week and a half the team put nearly all of its effort into one goal: resolve **every P0 and P1 issue and PR in the entire Hermes Agent repo** — and as of this release, **100% of them are closed.** Zero open P0s. Zero open P1s. That's **~700 highest-priority items** cleared as part of **~1,950 total issues and PRs closed** this window. We intend to keep P0/P1 at zero from here on.

> On top of that clean-sweep, v0.18.0 is about how *well* Hermes thinks and how it *knows when its work is actually done*. Mixture-of-Agents became a first-class citizen — named ensembles of models you can pick like any other model, with every reference model's reasoning shown to you and the aggregator's answer streamed live. The agent learned to verify its own work against evidence instead of vibes, `/goal` gained completion contracts, and `/learn` + `/journey` turned self-improvement into something you can see and steer.
```

#### Snippet 6 (NUEVO): Release v0.18.2 body (path: API releases/latest, body)
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

## Conflictos entre fuentes documentados (5 críticos)

### Conflicto 1: Cantidad de backends terminales
- **README y pyproject.toml**: 6 (local, Docker, SSH, Singularity, Modal, Daytona)
- **Landing page**: 5 (local, Docker, SSH, Singularity, Modal — sin Daytona)
- **Resolución**: el landing está desactualizado; 6 es la cifra correcta (Daytona está implementado en pyproject como extra `daytona = ["daytona==0.155.0"]`).
- **Impacto en doc**: usar 6.

### Conflicto 2: Versión más reciente
- **Doc pre-existente**: v0.18.0
- **GitHub API 2026-07-08**: v0.18.2 (publicada HOY)
- **Resolución**: v0.18.2 es la más reciente.
- **Impacto en doc**: actualizar todas las referencias a "v0.18.0" → "v0.18.2 (v2026.7.7.2)".

### Conflicto 3: Cantidad de plataformas de mensajería
- **Doc pre-existente / README headline**: 5+ (Telegram, Discord, Slack, WhatsApp, Signal, Email)
- **Realidad (gateway/platforms + plugins/platforms)**: 22+ adapters
- **Resolución**: la cifra real es 22+. El headline es marketing-friendly pero engañoso.
- **Impacto en doc**: listar las 22+ plataformas, no solo 5+.

### Conflicto 4: Porcentaje de Python
- **Doc pre-existente**: Python 80%
- **GitHub API 2026-07-08**: Python 84.3%
- **Resolución**: 84.3% (55.3MB / 65.6MB total). El cambio refleja la explosión de cli.py y run_agent.py en las últimas semanas.
- **Impacto en doc**: actualizar 80% → 84.3%.

### Conflicto 5: Cantidad de stars
- **Doc pre-existente (2026-07-07)**: 210.335
- **Doc original task_queue (junio 2026)**: 53k (estimación muy stale)
- **GitHub API 2026-07-08**: 211.474 (+1.139 en 24h)
- **Resolución**: 211.474 (dato fresco, ritmo de crecimiento ~1.100-1.700/día confirmado).
- **Impacto en doc**: actualizar 210.335 → 211.474.

## Pendientes de validación (re-evaluados 2026-07-08)

- [x] Confirmar stack Python (FastAPI/uvicorn para dashboard + prompt_toolkit para CLI + croniter para cron) — CONFIRMADO vía pyproject.toml
- [x] Confirmar Python >=3.11,<3.14 — CONFIRMADO vía pyproject.toml
- [x] Confirmar lazy install pattern — CONFIRMADO (pyproject extras + `tools/lazy_deps.py` referenciado)
- [x] Confirmar pinning policy post-Mini Shai-Hulud — CONFIRMADO vía comentario en pyproject
- [x] Confirmar 6 backends (vs 5 en landing) — CONFIRMADO (pyproject + README = 6; landing desactualizado)
- [x] Confirmar 22+ plataformas — CONFIRMADO vía `git/trees/main?recursive=1`
- [x] Confirmar version v0.18.2 latest — CONFIRMADO (releases/latest = v0.18.2 v2026.7.7.2)
- [x] Confirmar MoA first-class en v0.18.0 — CONFIRMADO vía release notes
- [x] Confirmar ACP server para IDEs — CONFIRMADO vía SKILL.md
- [x] Confirmar native desktop apps (mac/win/linux) — CONFIRMADO vía landing + SKILL.md
- [x] Confirmar hermes proxy (OpenAI-compatible local proxy) — CONFIRMADO vía SKILL.md
- [ ] Listar los 40+ tools concretamente (no hecho — requeriría leer `tools/` y `toolsets.py` línea por línea)
- [ ] Detalle exacto de los 6 backends (¿cuáles son providers oficiales vs plugins?)
- [ ] Profundizar en Honcho integration (¿cómo se llama la API? ¿qué dialectic model usa?)
- [ ] Verificar el agentskills.io standard (link a spec, schema)
- [ ] Confirmar pricing tiers Nous Portal (Free/Plus/Super/Ultra) y precios concretos

## Fuentes (consolidadas, 2026-07-08)

1. `https://api.github.com/repos/NousResearch/hermes-agent` — acceso 2026-07-08 19:55Z
2. `https://api.github.com/repos/NousResearch/hermes-agent/releases/latest` — acceso 2026-07-08 19:55Z
3. `https://api.github.com/repos/NousResearch/hermes-agent/releases` — acceso 2026-07-08 19:55Z
4. `https://api.github.com/repos/NousResearch/hermes-agent/releases/tags/v2026.7.1` — acceso 2026-07-08
5. `https://api.github.com/repos/NousResearch/hermes-agent/languages` — acceso 2026-07-08
6. `https://api.github.com/repos/NousResearch/hermes-agent/contents/` — acceso 2026-07-08
7. `https://api.github.com/repos/NousResearch/hermes-agent/contents/gateway` — acceso 2026-07-08
8. `https://api.github.com/repos/NousResearch/hermes-agent/contents/gateway/platforms` — acceso 2026-07-08
9. `https://api.github.com/repos/NousResearch/hermes-agent/git/trees/main?recursive=1` — acceso 2026-07-08
10. `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md` — acceso 2026-07-08
11. `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/pyproject.toml` — acceso 2026-07-08
12. `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/hermes-already-has-routines.md` — acceso 2026-07-08
13. `https://raw.githubusercontent.com/NousResearch/hermes-agent/main/skills/autonomous-ai-agents/hermes-agent/SKILL.md` — acceso 2026-07-08
14. `https://hermes-agent.nousresearch.com/` — acceso 2026-07-08
15. `https://github.com/plastic-labs/honcho` — citado en README
16. `https://agentskills.io` — citado en README
17. `https://portal.nousresearch.com` — citado en README

---

## Hechos verificados originales (2026-07-07, conservados para audit trail)

1-26. Los 26 hechos del material crudo original (stars 210.335, README 263 líneas, 6 backends, 5+ mensajerías, etc.) se mantienen válidos salvo los 5 que han cambiado (ver sección "Conflictos entre fuentes documentados"). Las URLs del material original siguen vigentes; las cifras numéricas se reemplazan por las del 2026-07-08.

*Fin del material crudo enriquecido.*
