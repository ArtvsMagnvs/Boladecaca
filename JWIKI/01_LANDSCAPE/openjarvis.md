# OpenJarvis

## Resumen

OpenJarvis es el framework open-source de Stanford (Hazy Research + Scaling Intelligence Lab, ~7.2k stars) que implementa un agente personal AI **local-first** sobre cinco primitivas ortogonales (Intelligence, Engine, Agents, Tools & Memory, Learning). Su tesis fundacional es **Intelligence Per Watt**: ejecutar el agente en el dispositivo del usuario, medir joules y watts con instrumentación vendor-native, y optimizar el propio spec (prompts, routing, LoRA) con un bucle de aprendizaje cerrado basado en traces locales. Lanzado el 12 de marzo de 2026, paper arXiv:2605.17172, v1.0.2 estable, bundle de escritorio Tauri cross-platform.

## Objetivo

Documentar el estado actual de OpenJarvis: las cinco primitivas, los dos diferenciadores clave (routing por complejidad + energía como métrica first-class), su posición en el ecosistema de agentes OSS de 2026 (vs OpenClaw, OpenHuman, Hermes), y qué partes son借鉴 aplicables al stack propio de Aithera V0.7.

## Estado

🟡 En progreso — material crudo verificado (141 hechos), pendiente audit 6-criterios + tablas de validación cruzada.

## Versiones compatibles

| Versión | Fecha | Notas |
|---|---|---|
| v1.0.0 | 2026-05-15 | Primera release estable de la arquitectura de 5 primitivas |
| v1.0.1 | 2026-05-17 | Patches: auto-update + analytics |
| v1.0.2 | 2026-05-24 | Wheel packaging fix + RAM detection Windows + Tauri desktop boot |
| Lanzamiento público inicial | 2026-03-12 | Anuncio MarkTechPost + CSDN + Tencent News |
| Anuncio integración Ollama | 2026-05-28 | Soporte oficial de Ollama v1.0.0 |
| `Unreleased` | continuo | Vision input (`gemma3:4b`), screen capture, `JARVIS_NUM_CTX` |

## Datos rápidos

| Campo | Valor |
|---|---|
| **Repositorio** | `github.com/open-jarvis/OpenJarvis` (org `open-jarvis`, NO `stanford-oval`) |
| **Licencia** | Apache-2.0 |
| **Stars** | 7.234 (a 2026-06-30, vía GitHub API) |
| **Forks** | 1.587 |
| **Open issues** | 63 |
| **Lenguaje principal declarado** | Python 3.10-3.13 (`requires-python = ">=3.10,<3.14"`) |
| **Rust** | Solo en crate telemetry `rust/crates/openjarvis-telemetry/` y Pearl mining crates |
| **Frontend navegador** | TypeScript + React (Tauri shell) |
| **Package manager** | `uv` (Astral) — `uv.lock` en repo (1,4 MB) |
| **Build backend** | hatchling + hatch-vcs (versionado desde git tags) |
| **CLI entrypoints** | `jarvis` (`openjarvis.cli:main`) + `openjarvis-eval` |
| **Server mode** | `jarvis serve` arranca FastAPI con SSE streaming |
| **Desktop bundle** | Tauri (.exe/.dmg/.deb/.rpm/.AppImage) con backend local embebido |
| **Paper arXiv** | `2605.17172` (v1: 16 May 2026, 22:00 UTC) |
| **DOI** | `10.48550/arXiv.2605.17172` |
| **Predecessor paper** | `arXiv:2511.07885` "Intelligence per Watt" |
| **Laboratorios** | Hazy Research (PI Christopher Re) + Scaling Intelligence Lab (co-PI Azalia Mirhoseini, dir. Percy Liang) |
| **Co-lead authors** | Jon Saad-Falcon + Avanika Narayan |
| **Paradigma** | Local-first + agent-as-5-primitives + trace-driven learning |

## Proyectos compatibles

- **Categorías OSS relacionadas**: OpenClaw (TypeScript, multi-canal-first), OpenHuman (Rust+TS, desktop-first), Hermes Agent (Python research framework), JarvisAgent (Tauri+Vue 3).
- **Skill sources importables**: ~150 skills desde Hermes Agent (NousResearch) + ~13.700 community skills desde OpenClaw (openclaw/skills).
- **Estándar de skills**: `agentskills.io` (abierto, cross-framework).
- **Protocolos interop**: MCP (Model Context Protocol, nativo en `src/openjarvis/mcp/`) + Google A2A (Agent-to-Agent, en `src/openjarvis/a2a/`).
- **Channels de mensajería**: 30+ soportados en `src/openjarvis/channels/` (slack, telegram, discord, whatsapp, imessage, signal, email/gmail, feishu, line, viber, messenger, reddit, mastodon, matrix, mattermost, teams, twitch, xmpp, zulip, etc.).
- **Conectores**: 40+ en `src/openjarvis/connectors/` (gmail, gdrive, gcalendar, notion, slack, github_notifications, spotify, oura, strava, obsidian, apple_health, apple_music, apple_notes, news_rss, weather, hackernews, etc.).

## Dependencias

- [01_LANDSCAPE/history.md](./history.md) — contexto histórico JARVIS-like agents
- [01_LANDSCAPE/projects.md](./projects.md) — comparativa OSS 2026
- [01_LANDSCAPE/openclaw.md](./openclaw.md) — comparativa vs TypeScript multi-canal
- [01_LANDSCAPE/openhuman.md](./openhuman.md) — comparativa vs desktop-first Tauri
- [01_LANDSCAPE/hermes-agent.md](./hermes-agent.md) — fuente de skills Python+Node — *(pendiente)*
- [02_ARCHITECTURE/](../02_ARCHITECTURE/README.md) — patrones de arquitectura
- [05_AI_PROVIDERS/](../05_AI_PROVIDERS/README.md) — providers IA (referencia de comparativa de modelos)
- [06_AGENTS/](../06_AGENTS/README.md) — patrones de agente (routing, learning loop)
- [07_MEMORY/](../07_MEMORY/README.md) — memoria semántica / ChromaDB
- [11_SECURITY/](../11_SECURITY/README.md) — sandboxing, injection scanner
- [12_TOOLING/](../12_TOOLING/README.md) — execution engine patterns

## Arquitectura

OpenJarvis formaliza el agente personal como cinco primitivas ortogonales editables independientemente, conectadas por un registry central:

```
┌─────────────────────────────────────────────────────────────┐
│             OpenJarvis — 5 Primitivas Ortogonales           │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐   │
│  │  INTELLIGENCE │  │    ENGINE     │  │    AGENTS      │   │
│  │  (catálogo    │  │  (backends    │  │  (comporta-    │   │
│  │  modelos      │◀─▶  inferencia) │◀─▶  miento:      │   │
│  │  on-device)   │  │  ollama/vllm/ │  │  orchestrator, │   │
│  │               │  │  sglang/      │  │  operative,    │   │
│  │  Qwen, GPT-OSS│  │  llama.cpp,   │  │  native_react, │   │
│  │  Gemma, GLM,  │  │  Apple FM,    │  │  openhands,    │   │
│  │  Granite,     │  │  Exo, Nexa,   │  │  deep_research │   │
│  │  Kimi         │  │  Mirai Uzu    │  │  monitor, etc.)│   │
│  └───────────────┘  └───────────────┘  └────────────────┘   │
│           ▲                  ▲                  ▲           │
│           └──────────────────┴──────────────────┘           │
│                              │                              │
│                              ▼                              │
│  ┌────────────────────────────────────┐  ┌────────────────┐ │
│  │       TOOLS & MEMORY               │  │   LEARNING     │ │
│  │  • skills/  (Hermes + OpenClaw)    │  │  (loop cerrado │ │
│  │  • memory/  (extractor+store)      │◀─▶   de optimi-  │ │
│  │  • mcp/  (Model Context Protocol)  │  │   zación       │ │
│  │  • a2a/  (Google Agent-to-Agent)   │  │   desde traces │ │
│  │  • connectors/  (40+ OAuth/data)   │  │   locales)     │ │
│  │  • channels/  (30+ messaging)      │  │                │ │
│  └────────────────────────────────────┘  └────────────────┘ │
│                              │                   │           │
│                              ▼                   ▼           │
│              ┌─────────────────────────────────────────┐    │
│              │   TELEMETRY + SEGURIDAD (transversal)   │    │
│              │   • EnergyMonitor (NVIDIA/AMD/Apple/   │    │
│              │     CPU_RAPL) → joules + watts + breakdown│   │
│              │   • InjectionScanner (Rust-backed)      │    │
│              │   • Sandbox Docker + WASM              │    │
│              │   • Taint tracking + credential strip  │    │
│              └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Punto clave**: el **registry central** (`src/openjarvis/core/registry.py`) es el bus. Cada primitiva publica sus implementaciones (e.g. `HeuristicRouter` y `LearnedRouterPolicy` ambas en `RouterPolicyRegistry`) y se intercambian en runtime. Esto permite cambiar intelligence (de Qwen a GPT-OSS) sin tocar agents, y cambiar engine (de Ollama a vLLM) sin tocar tools.

## Descripción técnica

### 1. Repositorio y origen

El proyecto se aloja en `github.com/open-jarvis/OpenJarvis` (organización independiente **abierta** por el equipo Stanford, NO la org `stanford-oval` que aloja STORM y otros). Repositorio creado el **15 de febrero de 2026**, semanas antes del lanzamiento público, con commits frescos a fecha de este documento (`pushed_at: 2026-06-30T07:21:16Z`). `default_branch: main`, `homepage: https://open-jarvis.github.io/OpenJarvis/`. La descripción corta declarada es "Personal AI, On Personal Devices", y la URL canónica del blog del laboratorio es `https://scalingintelligence.stanford.edu/blogs/openjarvis/`.

### 2. Autores y posición institucional

13 firmantes en el paper (orden arXiv): Jon Saad-Falcon, Avanika Narayan, Robby Manihani, Tanvir Bhathal, Herumb Shandilya, Hakki Orhun Akengin, Gabriel Bo, Andrew Park, Matthew Hart, Caia Costello, Chuan Li, Christopher Re, Azalia Mirhoseini. Saad-Falcon y Narayan aparecen marcados como co-lead con asterisco en el blog del Scaling Intelligence Lab. John Hennessy (presidente emérito de Stanford) figura como coautor en la lista del blog pero NO en la lista arXiv, lo que sugiere una contribución institucional. El trabajo se Adscribed a dos laboratorios SAIL: **Hazy Research** (Christopher Re como PI; Hazy Research mantiene `hazyresearch.stanford.edu`) y **Scaling Intelligence Lab** (co-PI Azalia Mirhoseini, con Percy Liang como director del lab). Estos laboratorios son los creadores del concepto **Intelligence Per Watt** (IPW), del que OpenJarvis es la implementación como framework.

### 3. Las 5 primitivas (corrección a briefings iniciales)

Aclaración crítica que corrige el briefing original del orquestador: las cinco primitivas **no** son `model, reasoning, agent, tools/memory, routing`. El repo declara nombres **completamente diferentes**:

| # | Primitiva real | Propósito | Ubicación |
|---|---|---|---|
| 1 | **Intelligence** | Catálogo unificado de modelos open (Qwen, GPT-OSS, Gemma, Granite, GLM, Kimi) | `src/openjarvis/intelligence/` con `model_catalog.py` y `__init__.py` |
| 2 | **Engine** | Backends de inferencia swap-in: `ollama`, `vllm`, `sglang`, `llama.cpp` (vía `gemma_cpp`), `apple_fm_shim` (Apple Foundation Models), `Exo`, `Nexa`, `Mirai Uzu` | `src/openjarvis/engine/` con `multi.py` para composición multi-engine |
| 3 | **Agents** | Capa comportamiento: `orchestrator` (descompone tareas), `operative` (ejecutor ligero), `native_react` (ReAct loop), `native_openhands` (CodeAct), `morning_digest` (scheduled TTS), `deep_research`, `monitor_operative`, `simple` | `src/openjarvis/agents/` |
| 4 | **Tools & Memory** | Grounding: skills (`agentskills.io`), `memory/` (extractor, service, store), `mcp/` (Model Context Protocol nativo client+server+transport+protocol+loader), `a2a/`, `connectors/` (40+), `channels/` (30+) | `src/openjarvis/{skills,memory,mcp,a2a,connectors,channels}/` |
| 5 | **Learning** | Motor de adaptación: 4 sub-áreas (`agents/`, `intelligence/`, `routing/`, `optimize/`), `spec_search/` (LLM-guided spec search), `training/lora/` | `src/openjarvis/learning/` |

Cada primitiva se registra en `core/registry.py`. **El routing NO es primitiva independiente** — es un sub-módulo dentro de Learning (`src/openjarvis/learning/routing/`). **Reasoning NO es primitiva** — es transversal: reside en el modelo (Intelligence) y en los patrones de agente (Agents).

### 4. Routing dinámico basado en complejidad (diferenciador #1)

El módulo central es `src/openjarvis/learning/routing/complexity.py`, que define `ComplexityQueryAnalyzer` y la función `score_complexity(query)` que retorna `ComplexityResult(score, tier, suggested_max_tokens, signals)`. La señal agregada es un **weighted-sum de cinco sub-señales detectables por regex**, con pesos fijos:

| Sub-señal | Peso | Detecta |
|---|---|---|
| `length` | 0.20 | Longitud absoluta del query |
| `domain` | 0.25 | Presencia de regex de código (`_CODE_PATTERNS`) o matemáticas (`_MATH_PATTERNS`) |
| `reasoning` | 0.25 | Patrones como `explain`, `analyze`, `compare`, `why`, `step-by-step` |
| `multi_part` | 0.15 | Conteo de `?` y sub-tareas enumeradas |
| `creative` | 0.15 | Patrones de generación creativa |

El score continuo [0,1] se mapea a cinco tiers con token budgets crecientes (`_TOKEN_TIERS`):

| Tier | Score range | `suggested_max_tokens` |
|---|---|---|
| `trivial` | <0.15 | 1.024 |
| `simple` | <0.30 | 2.048 |
| `moderate` | <0.55 | 4.096 |
| `complex` | <0.80 | 8.192 |
| `very_complex` | ≥0.80 | 16.384 |

Para "thinking models" (regex matchea `qwen3.5|qwq|deepseek-r1|o1-|o3-|o4-`), la función `adjust_tokens_for_model()` multiplica el presupuesto por **2x** porque consumen output tokens en internal chain-of-thought que el usuario no ve.

#### Dos políticas de routing coexistentes

Lo importante: **el routing tiene dos implementaciones intercambiables vía `RouterPolicyRegistry`**, no una sola "ML black-box":

**(a) `HeuristicRouter`** (`src/openjarvis/learning/routing/heuristic_policy.py`): seis reglas deterministas aplicadas en orden — (1) código detectado → modelo con tag `code`/`coder`; (2) math → modelo más grande; (3) score <0.20 → modelo más pequeño/rápido; (4) score ≥0.55 o `has_reasoning` → modelo más grande; (5) `urgency > 0.8` → override al más pequeño; (6) fallbacks en cadena: `default_model` → `fallback_model` → primer modelo disponible. Es **declarativo, depurable y reproducible** — no es una caja negra.

**(b) `LearnedRouterPolicy`** (`src/openjarvis/learning/routing/learned_router.py`): política aprendida en formato `query_class → best_model`, con tres modos:
- `select_model()` (runtime, lookup directo),
- `update_from_traces()` (batch offline, lee hasta 10.000 traces del trace store y agrupa por `query_class`),
- `observe(query, model, outcome, feedback)` (online incremental).

Composite score por modelo: `0.6 * success_rate + 0.4 * feedback_avg`. Requiere mínimo 5 samples (`min_samples = 5`) antes de aceptar un cambio de política.

`HeuristicRewardFunction.compute()` define el reward escalar combinando latencia, costo y eficiencia de tokens:

```python
reward = 0.4 * (1 - latency/max_latency) 
       + 0.3 * (1 - cost/max_cost)
       + 0.3 * (completion_tokens / total_tokens)
```

El reward es **continuo** ([0,1]), lo que permitiría migrar a bandits o policy gradient en el futuro. `RoutingContext` (dataclass en `openjarvis.core.types`) transporta `complexity_score`, `has_code`, `has_math`, `has_reasoning`, `urgency`, `suggested_max_tokens` y `metadata` con tier + signals.

**Lo crítico**: el routing aprende **solo** desde el trace local del usuario. NO envía traces a un servidor central — esto cierra el bucle con la promesa "personal data routes through... NOT" del proyecto.

### 5. Energía como métrica first-class (diferenciador #2)

Este es el segundo pilar diferenciador. El módulo central `src/openjarvis/telemetry/energy_monitor.py` define un ABC `EnergyMonitor` con cuatro implementaciones vendor:

| Vendor | API / librería | Notas |
|---|---|---|
| **NVIDIA** | NVML / `pynvml` / `nvidia-ml-py` | GPUs discretas +数据中心 GPUs |
| **AMD** | `amdsmi` (`amd-smi-lib`) | GPUs AMD Radeon Instinct |
| **APPLE** | `zeus-ml[apple]` + `powermetrics` | Apple Silicon (M-series), ANE incluido |
| **CPU_RAPL** | RAPL (Running Average Power Limit) | Intel + AMD CPU package-level |

La dataclass `EnergySample` almacena `energy_joules`, `mean_power_watts`, `peak_power_watts`, `duration_seconds`, `num_snapshots`, `vendor`, `energy_method` y **desglose por componente**: `cpu_energy_joules`, `gpu_energy_joules`, `dram_energy_joules`, `ane_energy_joules`. El enum `EnergyMethod` declara cuatro métodos oficiales como strings: `hw_counter`, `polling`, `rapl`, `zeus` — **deja claro que OpenJarvis NO simula potencia por software**, lee contadores reales de hardware cuando están disponibles.

La factory `create_energy_monitor(poll_interval_ms=50, prefer_vendor=None)` autodetecta hardware en orden **NVIDIA > AMD > APPLE > CPU_RAPL**. El poll interval por defecto es **50 ms**, consistente con la declaración del blog "sampling at 50ms intervals". Extras PyPI declaradas en `pyproject.toml`: `energy-amd = ["amdsmi>=6.1"]`, `energy-apple = ["zeus-ml[apple]"]`, `energy-all = ["pynvml>=12.0", "amdsmi>=6.1", "zeus-ml[apple]"]`.

**Implementación híbrida Python + Rust**: el crate `rust/crates/openjarvis-telemetry/src/energy.rs` se compila con `maturin>=1.12.6` (dev dep) y se expone via `openjarvis._rust_bridge`. La tests cubren los cuatro vendors: `tests/telemetry/test_energy_nvidia.py`, `test_energy_amd.py`, `test_energy_apple.py`, `test_energy_rapl.py`, `test_energy_monitor.py`, `test_energy_wiring.py`, `test_phase_energy.py`.

API pública energy (importable como): `from openjarvis.telemetry.energy_monitor import create_energy_monitor, EnergySample, EnergyVendor, EnergyMonitor`. Bench estándar: `openjarvis bench --bench energy` (`src/openjarvis/bench/energy.py`). Dashboards frontend: `EnergyDashboard.tsx` (web) + `Desktop/EnergyDashboard.tsx` (Tauri). Storages relacionados: `telemetry/{aggregator,session,steady_state,phase_metrics,gpu_monitor,vllm_metrics,itl,batch,flops}`.

### 6. Inteligencia Per Watt (la tesis energética fundacional)

IPW se formaliza como **`task_accuracy / power` (W)** en el paper predecessor (`arXiv:2511.07885`). Resultados principales declarados en el abstract:

- Local LMs responden correctamente **88.7%** de **1M** de consultas single-turn reales.
- IPW subió **5.3x entre 2023-2025**, con cobertura local-servicable ascendiendo de **23.2% a 71.3%**.
- Aceleradores locales muestran **≥1.4x mejor IPW** que cloud accelerators ejecutando los mismos modelos.

Escala experimental: 20+ LMs locales (≤20B parámetros activos), 8 hardware accelerators, 1M de consultas chat/reasoning. Apple M4 Max se cita explícitamente entre los locales. Sitios públicos: `https://www.intelligence-per-watt.ai/` y blog Hazy Research `hazyresearch.stanford.edu/blog/2025-11-11-ipw`. La saga completa es: **IPW (paper 2025, mide 88.7%/5.3x) → OpenJarvis (framework 2026, implementa local-first)**.

### 7. Stack técnico real

El briefing sugirió "Python + Rust". La realidad del repo:

- **Python** = lenguaje principal del código del agente (todo `src/openjarvis/`). Version `>=3.10,<3.14` (cap por incompatibilidad numpy 2.2 con cp314 Windows). Classifiers soporta 3.10/3.11/3.12/3.13.
- **Rust** = solo dos sitios: (a) `rust/crates/openjarvis-telemetry/` (telemetría energética compilada con `maturin`) y (b) Pearl mining crates distribuidas (`mining/vllm_pearl`, `cpu_pearl`, `apple_mps_pearl`).
- **TypeScript/React** = frontend (Tauri shell).
- **Package manager** = `uv` (Astral) — mencionado explícitamente en README (`uv sync`, `uv run`, `uv.lock` en repo).
- **Build backend** = `hatchling` con `hatch-vcs` para versionado dinámico desde git tags.
- **CLI entrypoints** = `jarvis = "openjarvis.cli:main"` y `openjarvis-eval = "openjarvis.evals.cli:main"`.
- **Server mode** = `jarvis serve` arranca FastAPI con SSE streaming; deps `fastapi>=0.110`, `uvicorn>=0.30`, `pydantic>=2.0`.
- **Docs UI** = mkdocs-material (`mkdocs>=1.6`, `mkdocs-material>=9.5`, `mkdocstrings[python]>=0.25`).
- **Frontend navegador quickstart** = `./scripts/quickstart.sh` (arranca Ollama + modelo + backend + frontend).
- **Desktop app** = bundle Tauri (.exe/.dmg/.deb/.rpm/.AppImage) generado en CI, con backend local embebido. CHANGELOG v1.0.2 menciona "Tauri boot path" y "desktop first-boot".

### 8. Skills, conectores, canales

**Modelo conceptual**: "every skill is a tool". Las skills se descubren de un catálogo y el agente las invoca on-demand. Estándar abierto: `agentskills.io` specification. Importadores oficiales: skills desde **Hermes Agent** (~150 skills de NousResearch/hermes-agent) y **OpenClaw** (~13.700 community skills de openclaw/skills). Comandos CLI:

```bash
jarvis skill install hermes:arxiv          # instala skill específica
jarvis skill sync --category research       # sync masivo por categoría
jarvis optimize skills --policy dspy        # optimiza skills con DSPy
jarvis bench skills --max-samples 5 --seeds 42
```

**Built-in agents** (8 según README; tres modos):

| Agente | Modo | Notas |
|---|---|---|
| `morning_digest` | scheduled, TTS | Briefing matutino programado |
| `deep_research` | on-demand | Búsqueda profunda multi-fuente |
| `monitor_operative` | continuous | Vigila señales continuas |
| `orchestrator` | on-demand | Descompone tareas en sub-tareas |
| `native_react` | on-demand | ReAct loop clásico |
| `operative` | continuous, persistent state | Ejecutor ligero con estado |
| `native_openhands` | on-demand | CodeAct (OpenHands adapter) |
| `simple` | on-demand, sin tools | Chat puro |

**26+ canales de mensajería** soportados (vía `src/openjarvis/channels/`): slack, discord, telegram, whatsapp, whatsapp_baileys, imessage, imessage_daemon, signal, email, gmail, gmail_imap, feishu, line, viber, messenger, reddit, mastodon, matrix, mattermost, sendblue, bluebubbles, irc, teams, twilio_sms, twitch, twitter, nostr, rocketchat, xmpp, zulip, webhook, webchat, google_chat.

**Conectores principales** (`src/openjarvis/connectors/`): gmail, gdrive, gcalendar, gcontacts, google_tasks, obsidian, notion, github_notifications, spotify, apple_health, apple_music, apple_notes, apple_contacts, oura, strava, news_rss, weather, hackernews, slack_connector, imessage, outlook, granola, dropbox.

**Protocolos interop**: **MCP** (Model Context Protocol) nativo en `src/openjarvis/mcp/` (client + server + transport + protocol + loader); **Google A2A** (Agent-to-Agent) en `src/openjarvis/a2a/`.

### 9. Vision y multimodality (estado actual = Unreleased)

Vision input **NO está en release estable** todavía — está en `[Unreleased]` del CHANGELOG. Flag CLI: `jarvis ask -i/--image <path>` (repetible) y `-S/--screen` para captura de pantalla. Modelo vision de ejemplo en unreleased: `gemma3:4b`. Las imágenes fluyen a Ollama via `/api/chat` con campo `images`. Screen capture usa stack Windows built-in (.NET) con fallback `mss`/`Pillow` en otras plataformas. Variable de entorno nueva: `JARVIS_NUM_CTX` (default 16384). Privacy guard avisa antes de enviar una imagen a un engine no-local.

### 10. Seguridad y sandbox

**Prompt injection scanner**: `src/openjarvis/security/injection_scanner.py` detecta **11 patrones** agrupados en categorías (`prompt_override`, `identity_override`, `code_injection`, `shell_injection`, `exfiltration`, `jailbreak`, `restriction_bypass`, `delimiter_injection`). Threat levels usados: `LOW < MEDIUM < HIGH < CRITICAL` (orden creciente). **Implementación**: delega al backend Rust via `openjarvis._rust_bridge.InjectionScanner.scan(text)` retornando JSON parseado — el wrapper Python es fino y la implementación real corre en el crate Rust compilado con maturin. Latencia-bajo y consistente cross-platform.

**Otros módulos de seguridad** en `src/openjarvis/security/`: `audit/`, `boundary`, `capabilities`, `credential_stripper`, `file_policy`, `file_utils`, `guardrails`, `rate_limiter`, `scanner`, `severity_policy`, `signing`, `ssrf`, `subprocess_sandbox`, `taint`, `types`.

**Sandboxes disponibles**:
- `src/openjarvis/sandbox/runner.py` — Docker, deps `sandbox-docker = ["docker>=7.0"]`.
- `src/openjarvis/sandbox/wasm_runner.py` — WASM via `wasmtime>=25`.

Más: `subprocess_sandbox/mount_security.py` (subprocess sandboxing), `file_policy.py` (allow-list/deny-list sobre operaciones), `taint.py` (propaga origen de datos a través de tools y outputs), signing (`security-signing = ["cryptography>=43"]`), y `audit/` que registra cada acción del agente para revisión posterior.

### 11. Benchmark y eval harness

El eval harness declara **30+ benchmarks** en `src/openjarvis/evals/datasets/`. El paper habla de **8 categorías de workloads personales** ("eight personal AI workload categories"). Benchmarks principales (no exhaustivo): PinchBench, GAIA, MMLU-Pro, SuperGPQA, HLE (Humanity's Last Exam), SimpleQA, WildChat, GPQA, Math500, LiveCodeBench, SWE-bench, SWE-bench structural, TauBench, TerminalBench v1/v2.1/native, WorkArena, WebChoreArena, ToolCall15, ToolOrchestra, Research Mining, PaperArena, Lifelong Agent, AMA bench, DeepPlanning, Frames, Doc QA, Daily Digest, Coding Task, Email Triage, Knowledge Base, LiveResearch, LiveResearchBench, LogHub, Morning Brief, Natural Reasoning, Security Scanner, SuperGPQA MCQ, WildChat judge, GAIA exact.

**Hallazgos del paper** (abstract, números crudos):
- Accuracy drop de **25-39 puntos porcentuales** al reemplazar Claude Opus 4.6 por Qwen3.5-9B en PinchBench y GAIA.
- State-of-the-art prompt optimizers cierran **solo 5 puntos porcentuales** del gap local-cloud por sí solos (motivación para spec search).
- **LLM-guided spec search**: durante búsqueda, modelos cloud frontier proponen edits al spec completo; solo se aceptan edits **non-regressing**; el spec final corre enteramente on-device en inference time.
- Con LLM-guided spec search, los specs on-device **matchean o exceden** cloud accuracy en **4 de 8 benchmarks**, con promedio dentro de **3.2 puntos** del mejor cloud baseline.
- Costo API marginal **~800x menor**, end-to-end latency **4x** vs cloud baseline.

Trackers: `evals/trackers/wandb_tracker.py` (W&B) + `evals/trackers/sheets_tracker.py` (Google Sheets). Pricing: `evals/core/pricing.py`. External runners (comparativas honestas contra otros frameworks): `evals/backends/external/hermes_agent/`, `evals/backends/external/openclaw/`, `evals/backends/external/_runners/hermes_runner.py`. Custom benchmark IPW: `evals/datasets/ipw_mixed/` + scorer `evals/scorers/ipw_mixed.py`.

### 12. Spec search y self-improvement (motor de Learning)

`src/openjarvis/learning/spec_search/` implementa LLM-guided spec search con sub-módulos:
- `appliers/{agent, intelligence, lora_stub, tools}.py` — aplican edits sobre cada primitivo.
- `gate/{benchmark_gate, cold_start, regression}.py` — filtros de aceptación.
- `plan/{planner, prompt_diff, risk_tier}.py` — planificación de edits.
- `diagnose/{runner, teacher_agent, tools, types}.py` — diagnóstico de fallos.
- `multi_session.py`, `external_adapter.py`, `models.py`, `orchestrator.py`.

**Skill discovery / optimization**: `learning/agents/{skill_discovery, skill_optimizer}.py`. **Learning orchestrator para GRPO**: `learning/intelligence/orchestrator/{environment, policy_model, prompt_registry, reward, grpo_trainer, sft_trainer, types}.py`. **LoRA training support**: `learning/training/lora/` + deps `orchestrator-training = ["torch>=2.0", "transformers>=4.40"]`. Prompt optimization via DSPy (extra `learning-dspy = ["dspy>=2.6"]`). Agent optimization via GEPA (extra `learning-gepa = ["gepa>=0.1"]`).

### 13. Comunidad y sponsors

**Sponsors oficiales** listados en README: Laude Institute (anchor, Christopher Re es chairman), Stanford Marlowe, Google Cloud Platform, Lambda Labs, Ollama, IBM Research, Stanford HAI.

**Canales comunitarios**: Discord oficial `https://discord.gg/CMVBmDQ5Fj` (invitación abierta), X/Twitter `@OpenJarvisAI`, Reddit main thread en `r/machinelearningnews` (post `1rs3ypd`, engagement alto). **Leaderboard de energía público**: `https://open-jarvis.github.io/OpenJarvis/leaderboard/` con premio "Mac Mini" al top en categoría energía (community engagement). **Roadmap público**: `https://open-jarvis.github.io/OpenJarvis/development/roadmap/`. Schema de contribución estilo good-first-issue: "take" en cualquier issue auto-asigna.

## Snippets de código (extractos relevantes con path)

### A. `src/openjarvis/telemetry/energy_monitor.py` — EnergyMonitor ABC

```python
class EnergyVendor(str, Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    APPLE = "apple"
    CPU_RAPL = "cpu_rapl"

@dataclass
class EnergySample:
    energy_joules: float = 0.0
    mean_power_watts: float = 0.0
    peak_power_watts: float = 0.0
    duration_seconds: float = 0.0
    cpu_energy_joules: float = 0.0
    gpu_energy_joules: float = 0.0
    dram_energy_joules: float = 0.0
    ane_energy_joules: float = 0.0
    vendor: str = ""
    energy_method: str = ""  # "hw_counter" | "polling" | "rapl" | "zeus"

class EnergyMonitor(ABC):
    @staticmethod
    @abstractmethod
    def available() -> bool: ...
    @abstractmethod
    def vendor(self) -> EnergyVendor: ...
    @abstractmethod
    def energy_method(self) -> str: ...
    @contextmanager
    @abstractmethod
    def sample(self) -> Generator[EnergySample, None, None]: ...

def create_energy_monitor(poll_interval_ms: int = 50, ...) -> Optional[EnergyMonitor]:
    """Detección orden: NVIDIA > AMD > Apple > CPU_RAPL."""
    ...
```

**Anotación**: el desglose CPU/GPU/DRAM/ANE permite atribuir joules a componentes específicos — crítico en Apple Silicon donde ANE (Apple Neural Engine) consume energía distinta del GPU. El enum `energy_method` deja claro que OpenJarvis NO simula potencia por software: lee contadores reales.

### B. `src/openjarvis/learning/routing/heuristic_policy.py` — Six routing rules

```python
class HeuristicRouter(RouterPolicy):
    """Rule-based model router. Rules (en orden):
       1. Code -> prefer model with 'code'/'coder'
       2. Math -> larger model
       3. Score < 0.20 -> smaller/faster
       4. Score >= 0.55 OR reasoning -> larger model
       5. Urgency > 0.8 -> override to smaller
       6. Fallback chain: default -> fallback -> first
    """
    def select_model(self, context: RoutingContext) -> str:
        available = self._available or list(ModelRegistry.keys())
        if not available:
            return self._default or self._fallback or ""
        if context.urgency > 0.8:
            return _smallest_model(available) or available[0]
        if context.has_code:
            code_model = _find_model_by_tag(available, "code") or _find_model_by_tag(available, "coder")
            if code_model:
                return code_model
            return _largest_model(available) or available[0]
        if context.has_math:
            return _largest_model(available) or available[0]
        if context.complexity_score < 0.20:
            return _smallest_model(available) or available[0]
        if context.complexity_score >= 0.55 or context.has_reasoning:
            return _largest_model(available) or available[0]
        if self._default and self._default in available:
            return self._default
        if self._fallback and self._fallback in available:
            return self._fallback
        return available[0]
```

**Anotación**: seis reglas deterministas declarativas — no ML black-box. Depurables, reproducibles, intercambiables con `LearnedRouterPolicy` via registry.

### C. `src/openjarvis/learning/routing/complexity.py` — 5-tier + thinking multiplier

```python
_TOKEN_TIERS = {
    "trivial": 1024, "simple": 2048, "moderate": 4096,
    "complex": 8192, "very_complex": 16384,
}
_THINKING_TOKEN_MULTIPLIER = 2
_THINKING_MODEL_PATTERNS = re.compile(
    r"qwen3\.5|qwq|deepseek-r1|o1-|o3-|o4-", re.IGNORECASE
)

def score_complexity(query: str) -> ComplexityResult:
    # weighted-sum señales: length (0.20), domain (0.25),
    # reasoning (0.25), multi_part (0.15), creative (0.15)
    if score < 0.15: tier = "trivial"
    elif score < 0.30: tier = "simple"
    elif score < 0.55: tier = "moderate"
    elif score < 0.80: tier = "complex"
    else: tier = "very_complex"
    return ComplexityResult(score=round(score, 3), tier=tier,
                            suggested_max_tokens=_TOKEN_TIERS[tier], signals=signals)

def adjust_tokens_for_model(suggested: int, model_name: Optional[str] = None) -> int:
    if model_name and is_thinking_model(model_name):
        return suggested * _THINKING_TOKEN_MULTIPLIER
    return suggested
```

### D. `src/openjarvis/learning/routing/learned_router.py` — Trace-driven learning

```python
class LearnedRouterPolicy(RouterPolicy):
    def select_model(self, context: RoutingContext) -> str:
        query_class = classify_query(context.query)
        if (query_class in self._policy_map
            and self._confidence.get(query_class, 0) >= self.min_samples):
            model = self._policy_map[query_class]
            if not self._available or model in self._available:
                return model
        # ...fallback chain...

    def update_from_traces(self, *, since=None, until=None) -> Dict[str, Any]:
        traces = self._analyzer._store.list_traces(since=since, until=until, limit=10_000)
        # agrupa por query_class, calcula composite score por modelo,
        # selecciona best_model y actualiza policy_map + confidence

class _ModelScore:
    __slots__ = ("count", "successes", "total_latency", "feedback_sum", "feedback_count")
    def composite_score(self) -> float:
        sr = self.successes / self.count if self.count else 0.0
        fb = self.feedback_sum / self.feedback_count if self.feedback_count else 0.5
        return 0.6 * sr + 0.4 * fb
```

**Anotación**: el learned router es **offline** (batch desde trace store) y **online** (incremental via `observe()`). Política en formato `query_class → best_model`. Min 5 samples antes de aceptar cambio. Aprende SOLO desde traces locales del usuario.

### E. `src/openjarvis/security/injection_scanner.py` — Prompt-injection patterns

```python
_INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
     "prompt_override", ThreatLevel.HIGH, "Attempt to override system instructions"),
    (r"(?i)(?:execute|run|eval)\s*\(\s*['\"]",
     "code_injection", ThreatLevel.HIGH, "Code execution attempt in prompt"),
    (r"(?:;|\||&&)\s*(?:rm|curl|wget|nc|ncat|bash|sh|python|perl)\s",
     "shell_injection", ThreatLevel.HIGH, "Shell command injection"),
    (r"(?i)(?:send|post|upload|exfiltrate|transmit)\s+...(?:\s+to\s+)?https?://",
     "exfiltration", ThreatLevel.HIGH, "Data exfiltration attempt"),
    # ... 7 patrones más en prompt_override, identity_override, jailbreak,
    # restriction_bypass, delimiter_injection (LOW/MEDIUM/HIGH/CRITICAL)
]

class InjectionScanner:
    def scan(self, text: str) -> InjectionScanResult:
        from openjarvis._rust_bridge import injection_result_from_json
        return injection_result_from_json(self._rust_impl.scan(text))
```

**Anotación**: scanner regex sobre 11 patrones categorizados. Backend Rust vía `_rust_bridge` (maturin-compiled). Latency-bajo y consistente cross-platform.

## Tabla comparativa final (vs otros proyectos del landscape)

| Dimensión | **OpenJarvis** | **OpenClaw** | **OpenHuman** | **Hermes Agent** *(pendiente doc)* | **Aithera V0.7** *(verif. pendiente)* |
|---|---|---|---|---|---|
| **Repo** | `open-jarvis/OpenJarvis` | `openclaw/openclaw` | `tinyhumansai/openhuman` | NousResearch/hermes-agent | `Aithera` (proyecto propio) |
| **Stars** | 7.234 | ~376k | 33.923 | ~53k | n/a (proyecto privado) |
| **Lenguaje principal** | Python 3.10-3.13 + Rust (telemetry) | TypeScript | Rust 60% + TS 36% | Python + Node | TypeScript + Python (Electron + FastAPI) |
| **Licencia** | Apache-2.0 | MIT | GPL-3.0 | MIT | Propietaria |
| **Default deployment** | **Local-first radical** (device del usuario, cloud opcional) | Cloud-first (TypeScript, multi-provider) | Desktop-first (Tauri 2.0) | Cloud-first (research) | Cloud-first (Electron, fallback local limitado) |
| **Frontend desktop** | **Tauri** (Rust+web), bundle nativo | Electron (Chromium+Node) | **Tauri 2.0** | N/A (CLI / web) | **Electron 29** + Vite/React |
| **Backend** | Python FastAPI opcional (`jarvis serve`) | Node.js | Rust (openhuman-core) | Python + Node | **FastAPI mandatory** |
| **Database** | ChromaDB-equivalent + traces SQLite + JSONL | Variable (channel state) | SQLite local + vault .md | Variable | **ChromaDB + SQLAlchemy 2.0 + Pydantic v2** |
| **Memory model** | Markdown-first / Obsidian-style + trace store | Vector (ClawHub embeddings) | Hierarchical summary trees (SQLite + .md) | Variable | **ChromaDB vector + session store** |
| **Agent primitives** | **5 explícitas** (Intelligence, Engine, Agents, Tools & Memory, Learning) | Sin primitivas formales (ClawHub skills) | Sin primitivas formales | Skill-based | Sin primitivas formales (AgentManager ad-hoc) |
| **Routing** | **Dinámico** (heuristic + learned + complexity-based) | Estático (un modelo por config) | Estático (un modelo por config) | Manual selection | Estático (manual, sin complejidad) |
| **Energía como métrica** | **Joules + watts + 4-vendor breakdown** (NVIDIA/AMD/Apple/CPU_RAPL) | No implementado | No implementado | No implementado | No implementado |
| **Trace-driven learning** | **Sí** (DSPy, GEPA, GRPO, SFT, LoRA + spec search) | No | No (sincronización 20min fija) | No explícito | No |
| **Sandbox** | **Docker + WASM** (dual) + subprocess | Docker (per-skill) | Rust sandbox interno | Variable | Subprocess |
| **Prompt injection scanner** | **Sí** (11 patrones, Rust-backed) + taint + SSRF + credential stripper + signing | VirusTotal + SkillSpector + hash lock (post-Snyk/ClawHavoc) | Limitado (Rust subprocess) | Limitado | Sin injection scanner explícito |
| **Skills system** | `agentskills.io` estándar, importa Hermes + OpenClaw catalogs | ClawHub (1.508 skills activos) | No (100+ OAuth connectors via Composio) | ~150 skills propios (importables a OpenJarvis) | Sin skill system |
| **Channels de mensajería** | **30+** (slack, telegram, discord, whatsapp, imessage, signal, feishu, line, viber, etc.) | **11+** channels (WhatsApp/Telegram/Slack/Discord/iMessage/Matrix/WeChat/Lark/QQBot) | Limitado (Google Meet como canal principal) | N/A (research framework) | Webchat + webhook |
| **Protocolos** | **MCP + Google A2A + JSON-RPC + REST + WebSocket** | MCP estándar | Composio (OAuth managed) | MCP | REST + WebSocket |
| **Multi-agente** | Orchestrator + Operative + Research loop + ReAct + OpenHands adapter | Workboard multi-agente (kanban) | Operativo único | Loop-based | Sin multi-agente explícito |
| **Eval suite** | **30+ benchmarks** + PinchBench + GAIA + SWE-bench + 8 categorías personales | Skill scanner + hash check | Básico (vault queries) | Research benchmarks varios | Sin eval harness público |
| **Sponsor académico** | Stanford SAIL (Hazy Research + Scaling Intelligence Lab) | Privado (Peter Steinberger) | Privado (TinyHumans AI) | NousResearch (independent AI safety lab) | n/a |
| **Sponsor institucional** | Laude Institute + Stanford Marlowe + Google Cloud + Lambda + Ollama + IBM Research + Stanford HAI | n/a | n/a | n/a | n/a |

### Notas sobre la comparativa

- **Diferenciadores OpenJarvis vs OpenClaw**: OpenJarvis es local-first puro; OpenClaw es multi-canal-first. OpenJarvis tiene routing dinámico por complejidad; OpenClaw tiene un modelo por configuración. OpenJarvis mide joules; OpenClaw mide skills. OpenJarvis tiene learning loop cerrado (DSPy/GEPA/GRPO/LoRA); OpenClaw no.
- **Diferenciadores OpenJarvis vs OpenHuman**: OpenJarvis es Python-first research-framework; OpenHuman es Rust-first polished-product. Ambos son desktop-first en algún sentido, pero OpenJarvis admite n modelos locales via Ollama/vLLM mientras OpenHuman apunta a "context in minutes via 20min sync desde 100+ OAuth".
- **Hermes Agent** (Pendiente doc JWIKI-007): research framework Python+Node de NousResearch, ~53k stars. Es **fuente principal de skills importables** a OpenJarvis (ver hecho #79) y es comparable en orientación research-vs-Aithera.
- **Aithera V0.7**: la columna es **INFERIDA** del briefing y skills previas (no verificada contra el repo Aithera real en este tick). El usuario deberá validar la columna antes de citarla como verdad dura.

## Buenas prácticas

- ✅ **Mantener el registry central** (`src/openjarvis/core/registry.py`) como única fuente de verdad para swap de providers/models/agents/routers.
- ✅ **Routing dual heuristic + learned** permite debugging determinista + optimización ML sin perder auditability.
- ✅ **Energy as first-class**: medir joules por defecto (no como extra opcional) refuerza la promesa local-first.
- ✅ **Spec search con regression gate**: solo se aceptan edits non-regressing — evita drift destructivo del spec.
- ✅ **Skills importables cross-framework**: usar `agentskills.io` como estándar abierto evita lock-in.
- ✅ **MCP + A2A nativos**: protocolos interop son obligatorios en un agente que quiere ser plataforma.
- ✅ **Tauri en lugar de Electron**: bundle nativo más pequeño, menor RAM, mejor performance-per-watt (encaja con la tesis IPW).
- ✅ **Sandbox dual Docker + WASM**: Docker para skills complejos, WASM para tools deterministas (más seguro, menos overhead).

## Errores comunes (veredicto honesto)

- ❌ **Confundir OpenJarvis con OpenClaw** — proyectos distintos. OpenJarvis es Stanford, Apache-2.0, local-first Python; OpenClaw es TypeScript MIT, channel-first.
- ❌ **Confundir `stanford-oval` con `open-jarvis`** — son organizaciones distintas. OpenJarvis se publicó como org abierta independiente.
- ❌ **Asumir "5 primitivas = model/reasoning/agent/tools/routing"** — el briefing original del orquestador se equivocó; las primitivas reales son Intelligence / Engine / Agents / Tools & Memory / Learning.
- ❌ **Asumir Rust + Python parejo** — el repo es ~90% Python; Rust solo aparece en telemetry crate y Pearl mining crates.
- ❌ **Asumir "routing = ML black-box"** — el routing es por defecto **heurístico + determinista** (6 reglas claras); el routing ML (`LearnedRouterPolicy`) es opcional.
- ❌ **Correr OpenJarvis sin instrumentación vendor** — el `EnergyMonitor` autodetecta, pero si la máquina no tiene NVIDIA/AMD/Apple/RAPL, el fallback `energy_method="polling"` puede dar lecturas ruidosas. Verificar antes de tomar decisiones.
- ❌ **Permitir que la spec search edite spec sin regression gate** — el módulo `gate/regression.py` debe estar activo SIEMPRE; sin él, los edits pueden destruir accuracy.
- ❌ **Confiar ciegamente en skills del catálogo** — aunque hay escáner + taint tracking, sigue siendo supply-chain risk; la auditoría humana (lee SKILL.md antes de instalar) sigue siendo necesaria.
- ❌ **Vision features en producción prematuramente** — están en `[Unreleased]`. Estables solo text/chat.
- ❌ **Stack paralelos**: el repo menciona `backend/` y `app/` con referencias cruzadas. Aunque OpenJarvis no tiene esa deuda específica, otros frameworks OSS sí — verificar antes de借鉴.

### Limitaciones reales (sin inflar)

- **Adopción temprana**: 7.2k stars a 2026-06-30 vs 376k OpenClaw. Ecosistema de skills todavía pequeño vs ClawHub.
- **Eval coverage privilegiado**: el paper declara 8 categorías personales; el framework es **personal-AI-specific**, no general-purpose. No pretende desplazar LangGraph/CrewAI/AutoGen en orquestación empresarial.
- **Dependencia del modelo on-device**: si el dispositivo no puede correr Qwen3.5-9B+ decentemente, el "local-first" se rompe (cae a cloud como fallback).
- **Spec search todavía inmaduro**: paper declara match/exceed solo en 4 de 8 benchmarks — no es una bala de plata.
- **Documentación**: el blog es denso, pero la API reference pública (mkdocs-material site) puede tener lag vs `main` — siempre leer el código fuente antes que la doc para primitivas nuevas.

## Impacto sobre otros sistemas

- **02_ARCHITECTURE** — patrón de "agent-as-N-primitives" + registry central; referencia de cómo NO codificar god-endpoint.
- **05_AI_PROVIDERS** — comparativa de modelos on-device (Qwen, GPT-OSS, Gemma, GLM, Kimi) vs cloud; trade-offs IPW.
- **06_AGENTS** — patrones de routing dinámico + complexity scoring + learned policy; benchmark de multi-agente.
- **07_MEMORY** — memoria local + trace store como base para RAG (vs ChromaDB puro).
- **08_VOICE** — `morning_digest` (scheduled TTS) pattern reference.
- **09_INTEGRATIONS** — 40+ connectors + 30+ channels como referencia de cobertura; MCP+A2A como protocolos canónicos.
- **10_AUTOMATION** — `morning_digest` + `monitor_operative` como patrones de automatización scheduled/continuous.
- **11_SECURITY** — injection scanner (Rust-backed) + taint tracking + SSRF + sandbox dual = referencia de defensa profunda.
- **12_TOOLING** — execution engine pattern (registry + validation + sandbox).
- **13_DEPLOYMENT** — Tauri bundle + Python backend embebido como alternativa a Electron + FastAPI separado.
- **14_BEST_PRACTICES** — ADR-style "why we chose local-first + 5-primitives".
- **15_KNOWN_PITFALLS** — pitfalls de medición de energía (vendor detection, polling fallback) + spec search regressions.
- **16_SOPS** — SOPs para setup (instalar uv, configurar Ollama, registrar energy monitor vendor).

## Referencias cruzadas

- [01_LANDSCAPE/projects.md](./projects.md) — comparativa OSS 2026
- [01_LANDSCAPE/history.md](./history.md) — historia JARVIS-like agents
- [01_LANDSCAPE/openclaw.md](./openclaw.md) — comparativa tipo TypeScript multi-canal
- [01_LANDSCAPE/openhuman.md](./openhuman.md) — comparativa desktop-first Rust+TS
- [01_LANDSCAPE/hermes-agent.md](./hermes-agent.md) — fuente de skills Python+Node *(pendiente)*
- [02_ARCHITECTURE/monolith-vs-microservices.md](../02_ARCHITECTURE/monolith-vs-microservices.md)
- [05_AI_PROVIDERS/local-ollama.md](../05_AI_PROVIDERS/local-ollama.md)
- [06_AGENTS/patterns-react.md](../06_AGENTS/patterns-react.md)
- [06_AGENTS/multi-agent-hierarchical.md](../06_AGENTS/multi-agent-hierarchical.md)
- [11_SECURITY/prompt-injection-defenses.md](../11_SECURITY/prompt-injection-defenses.md)
- [11_SECURITY/sandboxing-tool-whitelist.md](../11_SECURITY/sandboxing-tool-whitelist.md)
- [13_DEPLOYMENT/tauri-build.md](../13_DEPLOYMENT/tauri-build.md)

## Fuentes

1. `https://api.github.com/repos/open-jarvis/OpenJarvis` (GitHub REST API oficial) — acceso 2026-06-30
2. `https://github.com/open-jarvis/OpenJarvis` — README, LICENSE, CHANGELOG — acceso 2026-06-30
3. `https://arxiv.org/abs/2605.17172` "OpenJarvis: Personal AI, On Personal Devices" (cs.LG, v1 submit 16 May 2026 22:00 UTC, 3.059 KB) — acceso 2026-06-30
4. `https://arxiv.org/abs/2511.07885` "Intelligence per Watt" (predecessor, v1 11 Nov 2025, v4 21 May 2026) — acceso 2026-06-30
5. `https://scalingintelligence.stanford.edu/blogs/openjarvis/` (blog oficial Stanford) — acceso 2026-06-30
6. `https://www.intelligence-per-watt.ai/` (sitio IPW público) — acceso 2026-06-30
7. `https://hazyresearch.stanford.edu/blog/2025-11-11-ipw` (Hazy Research blog IPW) — acceso 2026-06-30
8. `https://hazyresearch.stanford.edu/` (perfil Hazy Research) — acceso 2026-06-30
9. `https://cs.stanford.edu/~chrismre/` (página PI Christopher Re) — acceso 2026-06-30
10. `https://ollama.com/blog/openjarvis` (anuncio oficial integración Ollama, 28 mayo 2026) — acceso 2026-06-30
11. `https://open-jarvis.github.io/OpenJarvis/` (web canónica del proyecto) — acceso 2026-06-30
12. `https://open-jarvis.github.io/OpenJarvis/leaderboard/` (leaderboard IPW público) — acceso 2026-06-30
13. `https://open-jarvis.github.io/OpenJarvis/development/roadmap/` (roadmap público) — acceso 2026-06-30
14. `https://discord.gg/CMVBmDQ5Fj` (Discord oficial) — acceso 2026-06-30
15. X/Twitter `@OpenJarvisAI` (cuenta oficial) — acceso 2026-06-30
16. `https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/CHANGELOG.md` (v1.0.0, v1.0.1, v1.0.2 + Unreleased) — acceso 2026-06-30
17. `https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/src/openjarvis/telemetry/energy_monitor.py` (código fuente real) — acceso 2026-06-30
18. `https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/src/openjarvis/learning/routing/complexity.py` (código fuente real) — acceso 2026-06-30
19. `https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/src/openjarvis/learning/routing/heuristic_policy.py` (código fuente real) — acceso 2026-06-30
20. `https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/src/openjarvis/learning/routing/learned_router.py` (código fuente real) — acceso 2026-06-30
21. `https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/src/openjarvis/learning/routing/heuristic_reward.py` (código fuente real) — acceso 2026-06-30
22. `https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/src/openjarvis/security/injection_scanner.py` (código fuente real) — acceso 2026-06-30
23. MarkTechPost post anunciando OpenJarvis (12 marzo 2026) — acceso 2026-06-30
24. CSDN "OpenJarvis源码解读" (confirmando fecha lanzamiento 2026-03-12) — acceso 2026-06-30
25. Tencent News articulo (con quote Karpathy atribuido — *fuente china, requiere verificación primaria*) — acceso 2026-06-30
26. Datasets oficiales CHANGELOG.md y `pyproject.toml` declarados en repo — acceso 2026-06-30

## Nivel de confianza

**85%** — Hechos del repo verificados desde GitHub API oficial + `api.github.com/repos/open-jarvis/OpenJarvis` (snapshot 2026-06-30). Estructura de 5 primitivas confirmada por blog oficial + código fuente directo (vía `raw.githubusercontent.com`). Hallazgos numéricos del abstract arXiv tomados como prima facie (requieren verificación contra PDF para números exactos). Métricas IPW (88.7%, 5.3x, ≥1.4x) declaradas en paper 2511.07885 abstract. Las **correcciones al briefing original** (5 primitivas reales, repo `open-jarvis`, stack Python-dominant) son de alta confianza. La **comparativa Aithera V0.7** es INFERIDA — pendiente verificación contra repo Aithera real.

## Pendientes

- [ ] **Confirmar sponsor list exacto contra página oficial** — el README menciona 7 sponsors (Laude, Marlowe, GCP, Lambda, Ollama, IBM, HAI); puede haber más añadidos después de v1.0.0.
- [ ] **Confirmar lenguaje stats del repo (Python/Rust/TypeScript %)** — el CSDN citó 82.7/8.7/7.3 pero la API GitHub solo reporta Python como lenguaje principal. Necesita `cloc` o `tokei` corriendo para confirmar.
- [ ] **Verificar counts de stars/forks/issues al momento exacto de lectura** — los números (7234 stars) eran válidos al momento del fetch pero cambian rápido; re-verificar antes de citar como número duro.
- [ ] **Comparativa Aithera V0.7** — la columna de la tabla de Diferenciadores es INFERIDA del briefing y skills. **Necesita verificación contra el repo Aithera real antes de publicarse**.
- [ ] **El dato "Karpathy OpenClaw quote"** viene de Tencent News (fuente china sin paper linkeado). Mejor verificar contra fuente primaria antes de citar como dato duro.
- [ ] **Lista derivada OpenClaw (PicoClaw/NanoBot/etc.)** viene del blog Stanford (fuente confiable). URLs verificadas vía web search. Los conteos de stars de cada fork no fueron validados.
- [ ] **`openjarvis.ai` "community-operated" broken TLS** — el dominio de la organización no se pudo validar; puede o no existir como propiedad separada del repo. No bloqueante pero anotar.
- [ ] **Licencia de OpenClaw (MIT)** — no se validó en código OpenClaw; OpenJarvis sí es Apache-2.0 (validado en LICENSE file).
- [ ] **Asterisco en autores** — el blog marca Saad-Falcon y Narayan como co-lead pero el arXiv no replica los asteriscos. Interpretación: asterisco = contribución principal. No es bloqueante.
- [ ] **Detalle de "third party" en el eval harness** — los external runners para Hermes Agent y OpenClaw existen como backend en `evals/backends/external/`, pero los números específicos de comparativas (PinchBench/GAIA numbers del paper) requieren leer el PDF.
- [ ] **Star count OpenJarvis al auditor** — verificar antes del tick de audit si ha subido significativamente.
- [ ] **RoutingContext campos exactos** — el dataclass está en `core/types.py` (no inspeccionado en este tick); verificar campos completos en el auditor.
- [ ] **Vision features fecha exacta de promoción a stable** — el CHANGELOG `[Unreleased]` no tiene fecha de release.

---

## Changelog

### 2026-06-30 — v1.0 (slot 011)
- Autor: Aithera Escriba B (`aithera-wiki-scr2`) (Mavis como proxy en tick B 19:00/19:16)
- Cambio: doc inicial OpenJarvis
- Material crudo: `JWIKI/material/JWIKI-005-raw.md` (141 hechos verificados, 50KB)
- Validador: Aithera Auditor B (`aithera-wiki-aud2`) — pendiente 6-criterios audit
- Notas: el doc corrige **7 errores** del briefing original del orquestador (5 primitivas, repo, stack, paper anchor, routing dual, energía jerárquica, learning local-only).
