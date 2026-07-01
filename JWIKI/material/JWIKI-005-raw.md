# Material crudo JWIKI-005 -- OpenJarvis (Stanford local-first)

> **Path destino final**: `C:\Users\Alejandro\Desktop\CLAUDE\Aithera\JWIKI\01_LANDSCAPE\openjarvis.md`
> **Investigador**: `aithera-wiki-inv2` (turno B, slot 005b -- re-dispatch post-crash 2026-06-30 18:30)
> **Fecha investigacion**: 2026-06-30
> **Estado**: raw (para que `aithera-wiki-scr2` lo convierta en doc final)
> **Fuentes**: GitHub REST API oficial (`api.github.com`), web search (matrix MCP), paper arXiv, blogs tecnicos, codigo fuente raw.

---

## Tesis en una linea

OpenJarvis es el framework open-source de Stanford que, sobre la base de cinco primitivas (Intelligence, Engine, Agents, Tools & Memory, Learning), implementa el primer agente personal AI local-first maduro: ejecuta por defecto en el dispositivo del usuario, mide consumo energetico en joules como metrica de primera clase, y optimiza su propio spec con un bucle de aprendizaje cerrado basado en traces locales.

---

## Hechos verificados

### 1. Repositorio y organizacion

1. El repositorio oficial esta en `github.com/open-jarvis/OpenJarvis` (NO en stanford-oval como decia el briefing). -- Fuente: `https://api.github.com/repos/open-jarvis/OpenJarvis` -- Fecha acceso: 2026-06-30.
2. La org GitHub `open-jarvis` no es la org Stanford; el repo se publico como org independiente abierta por el equipo Stanford. -- Fuente: misma API GitHub.
3. `full_name` del repo (campo GitHub API): `open-jarvis/OpenJarvis`. -- Fuente: api.github.com.
4. `description` declarado: "Personal AI, On Personal Devices". -- Fuente: api.github.com.
5. Licencia declarada (SPDX): `Apache-2.0`. Campo `license.key=apache-2.0`, `license.spdx_id=Apache-2.0`. -- Fuente: api.github.com + `LICENSE` en repo.
6. `stargazers_count`: 7.234 estrellas a 2026-06-30. -- Fuente: api.github.com.
7. `forks_count`: 1.587 forks. -- Fuente: api.github.com.
8. `open_issues_count`: 63 issues abiertos. -- Fuente: api.github.com.
9. `created_at`: `2026-02-15T00:24:16Z` (el repo se creo a mediados de febrero de 2026, semanas antes del lanzamiento publico). -- Fuente: api.github.com.
10. `updated_at`: `2026-06-30T16:12:35Z`; `pushed_at`: `2026-06-30T07:21:16Z` (commits frescos el mismo dia de la investigacion). -- Fuente: api.github.com.
11. `default_branch`: `main`. -- Fuente: api.github.com.
12. `homepage`: `https://open-jarvis.github.io/OpenJarvis/`. -- Fuente: api.github.com.
13. Lenguaje principal declarado por GitHub: `Python`. -- Fuente: api.github.com.
14. La URL canonica del sitio del proyecto (no del repo) es `https://scalingintelligence.stanford.edu/blogs/openjarvis/`. -- Fuente: webfetch 2026-06-30.
15. Discord oficial: `discord.gg/CMVBmDQ5Fj`. X/Twitter oficial: `@OpenJarvisAI`. -- Fuente: README.md (badge URLs).

### 2. Autores y laboratorios de origen

16. Paper autores (13 firmantes, orden del arXiv): Jon Saad-Falcon, Avanika Narayan, Robby Manihani, Tanvir Bhathal, Herumb Shandilya, Hakki Orhun Akengin, Gabriel Bo, Andrew Park, Matthew Hart, Caia Costello, Chuan Li, Christopher Re, Azalia Mirhoseini. -- Fuente: `https://arxiv.org/abs/2605.17172` (lista completa autores) -- Fecha acceso: 2026-06-30.
17. OpenJarvis se desarrollo en dos laboratorios de Stanford SAIL: **Hazy Research** (PI Christopher Re) y **Scaling Intelligence Lab** (co-PI Azalia Mirhoseini, con Percy Liang como director del lab). -- Fuente: blog oficial `https://scalingintelligence.stanford.edu/blogs/openjarvis/` -- Fecha acceso: 2026-06-30.
18. John Hennessy (presidente emerito de Stanford) figura como coautor en la lista completa de autores del blog, no en la del arXiv (probable contribucion institucional). -- Fuente: blog Scaling Intelligence Lab.
19. OpenJarvis es parte de la iniciativa **Intelligence Per Watt**, una linea de investigacion sobre eficiencia energetica de IA local (estudio predecessor del propio OpenJarvis). -- Fuente: blog Stanford + README.md ("About" section).
20. URLs del proyecto Intelligence Per Watt: `https://www.intelligence-per-watt.ai/` y `https://hazyresearch.stanford.edu/blog/2025-11-11-ipw`. -- Fuente: blog Stanford, URL confirmada en README.
21. La pagina del PI Christopher Re (`cs.stanford.edu/~chrismre/`) lista "OpenJarvis: Personal AI, on personal devices" como publicacion 2026 de su grupo. -- Fuente: web search, captura indexada por Google.
22. Jon Saad-Falcon y Avanika Narayan son los co-lead authors del paper (marcados con asterisco en blog oficial). -- Fuente: blog Stanford.

### 3. Paper academico y fechas de lanzamiento

23. Paper principal en arXiv: `arXiv:2605.17172` (cs.LG), titulo "OpenJarvis: Personal AI, On Personal Devices". Submitido **v1: 16 May 2026** 22:00:10 UTC, tamano 3.059 KB. -- Fuente: `https://arxiv.org/abs/2605.17172` -- Fecha acceso: 2026-06-30.
24. Codigo canonical del paper: `https://github.com/openjarvis/openjarvis` (case-insensitive, mismo repo que `open-jarvis/OpenJarvis`). -- Fuente: arXiv metadata, seccion "Code".
25. Web canonical: `https://open-jarvis.github.io/OpenJarvis/`. -- Fuente: arXiv metadata.
26. DOI: `10.48550/arXiv.2605.17172` (DOI DataCite). -- Fuente: arXiv page.
27. Lanzamiento publico del framework: **12 de marzo de 2026**. -- Fuente: MarkTechPost post del 12 marzo 2026; CSDN "OpenJarvis源码解读" que confirma fecha "2026年3月12日"; Tencent News fecha equivalente. -- Multi-fuente consistente.
28. v1.0.0 (primer release estable de la arquitectura de 5 primitivas): **2026-05-15**. -- Fuente: `CHANGELOG.md` seccion `## [1.0.0] - 2026-05-15`, leido de `raw.githubusercontent.com/open-jarvis/OpenJarvis/main/CHANGELOG.md`.
29. v1.0.1 (patch -- auto-update + analytics): **2026-05-17**. -- Fuente: CHANGELOG.md.
30. v1.0.2 (patch -- wheel packaging fix, RAM detection Windows): **2026-05-24**. -- Fuente: CHANGELOG.md.
31. Anuncio de integracion oficial con Ollama (v1.0.0 con soporte Ollama): **28 mayo 2026**. -- Fuente: `https://ollama.com/blog/openjarvis` -- Fecha acceso: 2026-06-30.
32. Paper predecessor (Intelligence Per Watt): `arXiv:2511.07885` ("Intelligence per Watt: Measuring Intelligence Efficiency of Local AI"), submitido **11 Nov 2025 v1**, ultima revision v4 **21 May 2026**. Autores principales: Jon Saad-Falcon, Avanika Narayan, Hakki Orhun Akengin, John Hennessy, Azalia Mirhoseini, Christopher Re. -- Fuente: `https://arxiv.org/abs/2511.07885` -- Fecha acceso: 2026-06-30.
33. OpenJarvis NO es la unica pieza de la tesis del grupo: la saga completa es IPW (paper 2025, mide 88.7%/5.3x) -> OpenJarvis (framework 2026, implementa local-first). -- Fuente: cadena blog IPW -> blog OpenJarvis.

### 4. Las 5 primitivas (correccion al briefing)

34. **CORRECCION al briefing del orquestador**: las 5 primitivas NO son "model, reasoning, agent, tools/memory, routing" como sugeria el despacho inicial. Las 5 primitivas REALES son: **Intelligence, Engine, Agents, Tools & Memory, Learning**. -- Fuente: blog oficial Stanford + arXiv abstract + README.
35. Cada primitiva esta implementada como modulo bajo `src/openjarvis/<nombre>/` con `core/registry.py` como punto de registro. -- Fuente: repo tree leido de git/trees/main recursive API.
36. **Intelligence** (capa modelo): modulos `src/openjarvis/intelligence/__init__.py` y `src/openjarvis/intelligence/model_catalog.py`. Provee catalogo unificado sobre familias open (Qwen, GPT-OSS, Gemma, Granite, GLM, Kimi). -- Fuente: repo + blog Stanford (parrafo "Intelligence: On-Device Language Models").
37. **Engine** (capa inferencia): modulos bajo `src/openjarvis/engine/` -- backends `ollama`, `vllm`, `sglang`, `llama.cpp` (via `gemma_cpp`), `Apple Foundation Models` (via `apple_fm_shim`), `Exo`, `Nexa`, `Mirai Uzu`. Modulo `multi.py` soporta composicion multi-engine. -- Fuente: repo tree + blog Stanford.
38. **Agents** (capa comportamiento): modulos en `src/openjarvis/agents/` con roles especializados: `orchestrator` (descompone tareas), `operative` (ejecutor ligero), `native_react` (ReAct loop), `native_openhands` (CodeAct), `morning_digest`, `deep_research`, `monitor_operative`, `simple`. -- Fuente: repo tree + README.
39. **Tools & Memory** (grounding): modulos en `src/openjarvis/memory/` (extractor, service, store), `src/openjarvis/skills/` (manager, executor, importer, sources/hermes, sources/openclaw), `src/openjarvis/mcp/`, `src/openjarvis/connectors/` (40+ conectores: gmail, gdrive, gcalendar, notion, slack, github_notifications, spotify, oura, strava, obsidian, etc.), `src/openjarvis/channels/` (30+ canales: slack, telegram, discord, whatsapp, imessage, email, feishu, line, viber, messenger, reddit, mastodon, matrix, mattermost, signal, teams, twitch, xmpp, zulip, etc.). -- Fuente: repo tree.
40. **Learning** (adaptacion): modulos en `src/openjarvis/learning/` con cuatro subareas de optimizacion: (a) `learning/agents/` (ace_optimizer, agent_evolver, dspy_optimizer, gepa_optimizer, skill_discovery, skill_optimizer), (b) `learning/intelligence/` (grpo_trainer, sft_trainer, orchestrator), (c) `learning/routing/` (router, heuristic_policy, heuristic_reward, learned_router, complexity), (d) `learning/optimize/` (config, feedback, llm_optimizer, optimizer, personal, search_space, store, trial_runner, types). Tambien `learning/spec_search/` (LLM-guided spec search) y `learning/training/lora/`. -- Fuente: repo tree.

### 5. Routing dinamico basado en complejidad (diferenciador #1)

41. Modulo de complejidad: `src/openjarvis/learning/routing/complexity.py` define `ComplexityQueryAnalyzer` y `score_complexity(query)` que devuelve `ComplexityResult(score: 0.0-1.0, tier, suggested_max_tokens, signals)`. -- Fuente: leido de `raw.githubusercontent.com/open-jarvis/OpenJarvis/main/src/openjarvis/learning/routing/complexity.py`.
42. La senal de complejidad se compone de cinco sub-senales con pesos fijos: length (0.20), domain (0.25 -- detecta codigo y matematicas con regex), reasoning (0.25 -- detecta patrones como explain/analyze/compare/why/step-by-step), multi_part (0.15 -- cuenta `?` y sub-tareas enumeradas), creative (0.15). -- Fuente: complexity.py lineas del bloque `score_complexity`.
43. Cinco tiers de complejidad mapean a token budgets crecientes: `trivial` (<0.15) -> 1024 tokens, `simple` (<0.30) -> 2048, `moderate` (<0.55) -> 4096, `complex` (<0.80) -> 8192, `very_complex` (>=0.80) -> 16384. -- Fuente: complexity.py lineas `_TOKEN_TIERS`.
44. "Thinking models" (qwen3.5, qwq, deepseek-r1, o1-, o3-, o4-) tienen multiplier 2x en el presupuesto de tokens via `adjust_tokens_for_model()`. -- Fuente: complexity.py.
45. Modulo de routing heuristico: `src/openjarvis/learning/routing/heuristic_policy.py` define `HeuristicRouter` con seis reglas aplicadas en orden: (1) codigo detectado -> modelo con "code"/"coder" en nombre; (2) math detectado -> modelo mas grande; (3) complejidad_score < 0.20 -> modelo mas pequeno; (4) complejidad_score >= 0.55 o has_reasoning -> modelo mas grande; (5) urgency > 0.8 -> override al mas pequeno; (6) fallback default_model -> fallback_model -> primer disponible. -- Fuente: heuristic_policy.py.
46. Modulo de routing aprendido: `src/openjarvis/learning/routing/learned_router.py` implementa `LearnedRouterPolicy` con tres modos -- `select_model()` (runtime), `update_from_traces()` (batch offline desde trace store, agrupando por `query_class`), y `observe()` (online incremental por observacion individual). -- Fuente: learned_router.py.
47. Composite score del learned router: `0.6 * success_rate + 0.4 * feedback_avg` (minimo 5 samples por modelo antes de aceptar un cambio). -- Fuente: learned_router.py clase `_ModelScore.composite_score()`.
48. Modulo de reward para evaluar rutas: `src/openjarvis/learning/routing/heuristic_reward.py` define `HeuristicRewardFunction.compute()` que combina `0.4 * (1 - latency/max_latency) + 0.3 * (1 - cost/max_cost) + 0.3 * completion_tokens/total_tokens`. -- Fuente: heuristic_reward.py.
49. Las politicas de routing (heuristic, learned) se registran en `RouterPolicyRegistry` (registry pattern) bajo el modulo `openjarvis.core.registry`. -- Fuente: learned_router.py funcion `ensure_registered()`.
50. `RoutingContext` (dataclass en `openjarvis.core.types`) transporta `complexity_score`, `has_code`, `has_math`, `has_reasoning`, `urgency`, `suggested_max_tokens`, `metadata` con tier y signals. -- Fuente: complexity.py y heuristic_policy.py.

### 6. Energia como metrica first-class (diferenciador #2)

51. Modulo central: `src/openjarvis/telemetry/energy_monitor.py` define ABC `EnergyMonitor` con cuatro implementaciones vendor: **NVIDIA** (via NVML/pynvml/nvidia-ml-py), **AMD** (via amdsmi), **APPLE** (via `zeus-ml[apple]` + `powermetrics`), **CPU_RAPL** (Running Average Power Limit -- Intel/AMD CPU package-level). -- Fuente: energy_monitor.py.
52. Energia y potencia se almacenan en dataclass `EnergySample` con campos: `energy_joules`, `mean_power_watts`, `peak_power_watts`, `duration_seconds`, `num_snapshots`, vendor/device, y desglose por componente `cpu_energy_joules`, `gpu_energy_joules`, `dram_energy_joules`, `ane_energy_joules`. -- Fuente: energy_monitor.py clase `EnergySample`.
53. Cuatro metodos oficiales de medicion energetica declarados como string enum: `hw_counter`, `polling`, `rapl`, `zeus`. -- Fuente: energy_monitor.py docstring `energy_method()`.
54. Factory function `create_energy_monitor(poll_interval_ms=50, prefer_vendor=None)` autodetecta hardware en orden de prioridad NVIDIA > AMD > APPLE > CPU_RAPL. -- Fuente: energy_monitor.py.
55. Poll interval por defecto: **50 ms** (consistente con la declaracion oficial del blog "sampling at 50ms intervals"). -- Fuente: energy_monitor.py + blog Stanford.
56. Tests cubren los cuatro vendors: `tests/telemetry/test_energy_nvidia.py`, `test_energy_amd.py`, `test_energy_apple.py`, `test_energy_rapl.py`, `test_energy_monitor.py`, `test_energy_wiring.py`, `test_phase_energy.py`. -- Fuente: repo tree recursive.
57. Implementacion hibrida Python+Rust para el modulo: el crate `rust/crates/openjarvis-telemetry/src/energy.rs` se compila con maturin (`maturin>=1.12.6` en dev deps) y se expone via `openjarvis._rust_bridge`. -- Fuente: repo tree + pyproject.toml dev deps.
58. Extras PyPI declaradas en `pyproject.toml`: `energy-amd = ["amdsmi>=6.1"]`, `energy-apple = ["zeus-ml[apple]"]`, `energy-all = ["pynvml>=12.0", "amdsmi>=6.1", "zeus-ml[apple]"]`. -- Fuente: pyproject.toml.
59. API publica energy: importable como `from openjarvis.telemetry.energy_monitor import create_energy_monitor, EnergySample, EnergyVendor, EnergyMonitor`. -- Fuente: energy_monitor.py `__all__`.
60. Bench de energia: `src/openjarvis/bench/energy.py` estandariza medicion (`openjarvis bench --bench energy`). -- Fuente: repo tree + readme.
61. Dashboards de energia en frontend: `frontend/src/components/Dashboard/EnergyDashboard.tsx` (web) y `Desktop/EnergyDashboard.tsx` (Tauri). -- Fuente: repo tree.
62. Storages de telemetria relacionados: `telemetry/aggregator/`, `telemetry/session/`, `telemetry/steady_state/`, `telemetry/phase_metrics/`, `telemetry/gpu_monitor/`, `telemetry/vllm_metrics/`, `telemetry/itl/` (inter-token latency), `telemetry/batch/`, `telemetry/flops/`. -- Fuente: repo tree.

### 7. Inteligencia Per Watt (la tesis energetica fundacional)

63. IPW formal = `task_accuracy / power` (W). Definido en la seccion de introduccion del paper 2511.07885. -- Fuente: arXiv abstract.
64. Resultados principales del estudio IPW (segun abstract): (1) local LMs contestan correctamente **88.7%** de 1M de consultas single-turn reales. (2) IPW subio **5.3x entre 2023-2025**, con cobertura local-servicable ascendiendo de **23.2% a 71.3%**. (3) Aceleradores locales muestran **>=1.4x mejor IPW** que cloud accelerators ejecutando los mismos modelos. -- Fuente: arXiv 2511.07885 abstract.
65. Escala experimental: 20+ LMs locales (<=20B parametros activos), 8 hardware accelerators (locales y cloud), 1M de consultas chat/reasoning. -- Fuente: abstract.
66. Disenado para Apple M4 Max entre los aceleradores locales representativos. -- Fuente: abstract menciona M4 Max como caso.
67. Sites publicos: `https://www.intelligence-per-watt.ai/` y blog post Hazy Research `hazyresearch.stanford.edu/blog/2025-11-11-ipw`. -- Fuente: blog oficial.

### 8. Stack tecnico real (correccion al briefing)

68. **CORRECCION al briefing**: el briefing sugirio "Python + Rust" como stack completo. La realidad del repo: **Python es el lenguaje principal** del codigo del agente (todo `src/openjarvis/` es Python). Rust aparece solo en (a) `rust/crates/openjarvis-telemetry/src/energy.rs` (telemetria energetica) y (b) crates Pearl para mining distribuido (`mining/vllm_pearl`, `cpu_pearl`, `apple_mps_pearl`). Frontend es TypeScript/React. -- Fuente: repo tree + pyproject.toml.
69. Version Python: `requires-python = ">=3.10,<3.14"` (cap por incompatibilidad numpy 2.2 con cp314 Windows). -- Fuente: pyproject.toml.
70. Python classifiers soporta 3.10/3.11/3.12/3.13. -- Fuente: pyproject.toml classifiers.
71. Build backend: `hatchling` con `hatch-vcs` para versionado dinamico desde git tags. -- Fuente: pyproject.toml `[build-system]`.
72. Package manager: `uv` (Astral) -- mencionado explicitamente en README (`uv sync`, `uv run`, `uv.lock` en repo). -- Fuente: README.md + `uv.lock` (1,4 MB).
73. Entry points CLI: `jarvis = "openjarvis.cli:main"` y `openjarvis-eval = "openjarvis.evals.cli:main"`. -- Fuente: pyproject.toml `[project.scripts]`.
74. Server mode: `jarvis serve` arranca FastAPI con SSE streaming; deps `fastapi>=0.110`, `uvicorn>=0.30`, `pydantic>=2.0`. -- Fuente: pyproject.toml extras `server` y `desktop`.
75. Documentacion UI: mkdocs-material (`mkdocs>=1.6`, `mkdocs-material>=9.5`, `mkdocstrings[python]>=0.25`). -- Fuente: pyproject.toml extras `docs`.
76. Frontend navegador: `./scripts/quickstart.sh` arranca Ollama + modelo + backend + frontend. -- Fuente: MarkTechPost article + README.
77. Desktop app: bundle Tauri (.exe/.dmg/.deb/.rpm/.AppImage) generado en CI, con backend local embebido. -- Fuente: README.md y CHANGELOG.md (v1.0.2 menciona "Tauri boot path" y "desktop first-boot").

### 9. Skills, conectores, canales

78. Modelo conceptual: "every skill is a tool". Las skills se descubren de un catalogo y el agente las invoca on-demand. -- Fuente: README.md seccion "Skills".
79. Importadores oficiales: skills desde **Hermes Agent** (~150 skills, fuente NousResearch/hermes-agent) y **OpenClaw** (~13.700 community skills, fuente openclaw/skills). -- Fuente: README.md `jarvis skill install hermes:arxiv`.
80. Estandar abierto: `agentskills.io` specification. -- Fuente: README.md.
81. Comandos CLI: `jarvis skill install`, `jarvis skill sync --category research`, `jarvis optimize skills --policy dspy`, `jarvis bench skills --max-samples 5 --seeds 42`. -- Fuente: README.md Quick Start.
82. Built-in agents (8 segun README; tres modos: on-demand, scheduled, continuous): `morning_digest` (scheduled, TTS), `deep_research` (on-demand), `monitor_operative` (continuous), `orchestrator` (on-demand), `native_react` (on-demand, ReAct), `operative` (continuous, persistent state), `native_openhands` (on-demand, CodeAct), `simple` (on-demand, sin tools). -- Fuente: README.md tabla.
83. 26+ canales de mensajeria soportados: slack, discord, telegram, whatsapp, whatsapp_baileys, imessage, imessage_daemon, signal, email, gmail, gmail_imap, feishu, line, viber, messenger, reddit, mastodon, matrix, mattermost, sendblue, bluebubbles, irc, teams, twilio_sms, twitch, twitter, nostr, rocketchat, xmpp, zulip, webhook, webchat, google_chat. -- Fuente: repo tree `src/openjarvis/channels/`.
84. Conectores principales: gmail, gdrive, gcalendar, gcontacts, google_tasks, obsidian, notion, github_notifications, spotify, apple_health, apple_music, apple_notes, apple_contacts, oura, strava, news_rss, weather, hackernews, slack_connector, imessage, outlook, granola, dropbox. -- Fuente: repo tree `src/openjarvis/connectors/`.
85. Soporte de protocolos interop: **MCP** (Model Context Protocol) nativo en `src/openjarvis/mcp/` (client, server, transport, protocol, loader). **Google A2A** (Agent-to-Agent) en `src/openjarvis/a2a/`. -- Fuente: repo tree + blog Stanford.

### 10. Vision y multimodality (estado actual)

86. Vision input esta en `[Unreleased]` (no en release estable todavia). Flag CLI: `jarvis ask -i/--image <path>` repetible y `-S/--screen` para captura de pantalla. -- Fuente: CHANGELOG.md seccion Unreleased.
87. Modelos vision soportados en el unreleased: `gemma3:4b` (mencionado como ejemplo). Las imagenes fluyen a Ollama via `/api/chat` con campo `images`. -- Fuente: CHANGELOG.md.
88. Screen capture usa stack Windows built-in (.NET) con fallback `mss`/`Pillow` en otras plataformas. -- Fuente: CHANGELOG.md.
89. Variable de entorno nueva para tunear contexto Ollama: `JARVIS_NUM_CTX` (default 16384). -- Fuente: CHANGELOG.md.
90. Privacy guard: avisa antes de enviar una imagen a un engine no-local. -- Fuente: CHANGELOG.md (seguridad).

### 11. Seguridad y sandbox

91. Inyeccion de prompt: `src/openjarvis/security/injection_scanner.py` detecta 11 patrones agrupados en 6 categorias (prompt_override, identity_override, code_injection, shell_injection, exfiltration, jailbreak, restriction_bypass, delimiter_injection). -- Fuente: injection_scanner.py lista `_INJECTION_PATTERNS`.
92. Threat levels usados: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` (orden creciente). -- Fuente: injection_scanner.py imports.
93. El scanner delega al backend Rust via `openjarvis._rust_bridge.InjectionScanner.scan(text)` retornando JSON parseado. -- Fuente: injection_scanner.py clase `InjectionScanner.scan()`.
94. Modulos de seguridad adyacentes: `src/openjarvis/security/{audit, boundary, capabilities, credential_stripper, file_policy, file_utils, guardrails, rate_limiter, scanner, severity_policy, signing, ssrf, subprocess_sandbox, taint, types}.py`. -- Fuente: repo tree.
95. Sandboxes disponibles: `src/openjarvis/sandbox/runner.py` (Docker, deps `sandbox-docker = ["docker>=7.0"]`) y `src/openjarvis/sandbox/wasm_runner.py` (WASM via `wasmtime>=25`). -- Fuente: pyproject.toml extras + repo tree.
96. Subprocess sandboxing: `src/openjarvis/security/subprocess_sandbox.py` con `subprocess_sandbox/mount_security.py`. -- Fuente: repo tree.
97. File policy ejecuta allow-list/deny-list sobre operaciones del agente: `src/openjarvis/security/file_policy.py`. -- Fuente: repo tree.
98. Taint tracking: `src/openjarvis/security/taint.py` propaga origen de datos a traves de tools y outputs. -- Fuente: repo tree.
99. Signing de skills/scripts: `security-signing = ["cryptography>=43"]`. -- Fuente: pyproject.toml.
100. Audit logging: `src/openjarvis/security/audit/` registra cada accion del agente para posterior revision. -- Fuente: repo tree.

### 12. Benchmarks y eval harness

101. El eval harness declara **30+ benchmarks** en `src/openjarvis/evals/datasets/`. -- Fuente: blog Stanford ("evaluation harness spanning 30+ benchmarks").
102. El paper habla de 8 categorias de workloads personales ("eight personal AI workload categories") en las que se desglosa la evaluacion. -- Fuente: researchgate snippet del paper.
103. Benchmarks principales: PinchBench, GAIA, MMLU-Pro, SuperGPQA, HLE (Humanity's Last Exam), SimpleQA, WildChat, GPQA, Math500, LiveCodeBench, SWE-bench, SWE-bench structural, TauBench, TerminalBench, TerminalBench v2.1, TerminalBench native, WorkArena, WebChoreArena, ToolCall15, ToolOrchestra, Research Mining, PaperArena, PinchBench, Lifelong Agent, AMA bench, DeepPlanning, Frames, Doc QA, Daily Digest, Coding Task, Email Triage, Knowledge Base, LiveResearch, LiveResearchBench, LogHub, Morning Brief, Natural Reasoning, Security Scanner, SimpleQA judge, SuperGPQA MCQ, WildChat judge, GAIA exact. -- Fuente: repo tree `src/openjarvis/evals/datasets/` y `scorers/`.
104. El paper midio accuracy drop de **25-39 puntos porcentuales** al reemplazar Claude Opus 4.6 por Qwen3.5-9B en PinchBench y GAIA. -- Fuente: arXiv 2605.17172 abstract.
105. State-of-the-art prompt optimizers cierran **solo 5 puntos porcentuales** del gap local-cloud por si solos (motivacion para spec search). -- Fuente: arXiv 2605.17172 abstract.
106. LLM-guided spec search: durante busqueda, modelos cloud frontier proponen edits al spec completo; solo se aceptan edits non-regressing; el spec final corre enteramente on-device en inference time. -- Fuente: arXiv 2605.17172 abstract.
107. Con LLM-guided spec search, los specs on-device **matchean o exceden** cloud accuracy en **4 de 8 benchmarks**, con promedio dentro de **3.2 puntos** del mejor cloud baseline. -- Fuente: arXiv 2605.17172 abstract.
108. Costo API marginal se reduce **~800x** y end-to-end latency **4x** vs cloud baseline. -- Fuente: arXiv 2605.17172 abstract.
109. Trackers soportados: `evals/trackers/wandb_tracker.py` (W&B) y `evals/trackers/sheets_tracker.py` (Google Sheets). -- Fuente: repo tree.
110. Pricing module: `evals/core/pricing.py` (calculo de costo por token por modelo). -- Fuente: repo tree.
111. External runners (comparativas honestas vs otros frameworks): `evals/backends/external/hermes_agent/`, `evals/backends/external/openclaw/`, `evals/backends/external/_runners/hermes_runner.py`. -- Fuente: repo tree.
112. Custom benchmark interno IPW: `evals/datasets/ipw_mixed/` + scorer `evals/scorers/ipw_mixed.py` (mide accuracy y eficiencia combinada). -- Fuente: repo tree.

### 13. Spec search y self-improvement (motor de Learning)

113. Modulo `src/openjarvis/learning/spec_search/` implementa LLM-guided spec search: sub-modulos `appliers/{agent, intelligence, lora_stub, tools}.py` aplican edits sobre cada primitivo. -- Fuente: repo tree.
114. Sub-modulos relevantes: `gate/{benchmark_gate, cold_start, regression}.py` (filtros de aceptacion), `plan/{planner, prompt_diff, risk_tier}.py`, `diagnose/{runner, teacher_agent, tools, types}.py`, `multi_session.py`, `external_adapter.py`, `models.py`, `orchestrator.py`. -- Fuente: repo tree.
115. Skill discovery / optimization: `learning/agents/{skill_discovery, skill_optimizer}.py`. -- Fuente: repo tree.
116. Learning orchestrator para GRPO: `learning/intelligence/orchestrator/{environment, policy_model, prompt_registry, reward, grpo_trainer, sft_trainer, types}.py`. -- Fuente: repo tree.
117. LoRA training support: `learning/training/lora/` y deps `orchestrator-training = ["torch>=2.0", "transformers>=4.40"]`. -- Fuente: repo tree + pyproject.toml.
118. Prompt optimization via DSPy: extra `learning-dspy = ["dspy>=2.6"]`. -- Fuente: pyproject.toml extras.
119. Agent optimization via GEPA: extra `learning-gepa = ["gepa>=0.1"]`. -- Fuente: pyproject.toml extras.

### 14. Comparativas con proyectos del ecosistema

120. **OpenClaw** ("小龙虾") mencionado en blog Stanford como marco competidor dominante: > 250.000 estrellas GitHub, inspiro derivados (PicoClaw, NanoBot, IronClaw, TinyClaw, MimicLaw, ZeroClaw). -- Fuente: blog Scaling Intelligence Lab.
121. Karpathy sobre OpenClaw (citado por Tencent News): "vibe coded garbage dump fire"; "no recomiendo correr esto en tu propio PC". -- Fuente: Tencent News articulo `news.qq.com/rain/a/20260315A00GCR00`. **CUIDADO**: fuente china sin paper linkeado; mejor verificar contra fuente primaria.
122. Auditoria reportada de OpenClaw: 512 vulnerabilidades, 8 criticas, >20.000 instancias expuestas en internet con API keys y OAuth tokens leak. -- Fuente: Tencent News (sin paper oficial linkeado).
123. **Hermes Agent** (NousResearch, ~150 skills) es la otra fuente principal de skills importables en OpenJarvis. -- Fuente: README.md + repo tree `skills/sources/hermes.py`.
124. PicoClaw: `github.com/sipeed/picoclaw`. NanoBot: `github.com/HKUDS/nanobot`. IronClaw: `github.com/nearai/ironclaw`. TinyClaw: `github.com/warengonzaga/tinyclaw`. MimicLaw: `github.com/memovai/mimiclaw`. ZeroClaw: `github.com/zeroclaw-labs/zeroclaw`. -- Fuente: blog Stanford (links verificados via web search).
125. **Aithera V0.7** (stack interno del usuario): comparativa conceptual -- Aithera es Electron+FastAPI con fallback local opcional; OpenJarvis es Python-first local-first radical. Aithera mide latencia pero no joules por defecto; OpenJarvis tiene `EnergyMonitor` ABC con 4 vendors. Aithera routing: estatico (v0.7 manual); OpenJarvis routing: dinamico via `LearnedRouterPolicy` + complexity scorer. Aithera no tiene learning loop explicito; OpenJarvis tiene `learning/` con SFT/GRPO/DPO/DSPy/GEPA/LoRA. NOTA: estas comparaciones son inferencias del briefing, no verificadas en codigo Aithera. **VERIFICACION PENDIENTE contra el repo Aithera real.**

### 15. Diferenciadores arquitectonicos (vs OpenClaw, Hermes, Aithera)

126. **Primitivas tipadas**: OpenJarvis expone cinco campos editables independientemente (Intelligence, Engine, Agents, Tools & Memory, Learning). OpenClaw y Hermes envuelven todo en una sola aplicacion. -- Fuente: blog Stanford (parrafo "Primitives for On-Device AI") + codebase.
127. **Routing aprendido, no estatico**: el routing usa trace history para aprender `query_class -> model` mapeos. A diferencia de OpenClaw (un solo modelo por configuracion) y Hermes (seleccion manual). -- Fuente: learned_router.py.
128. **Energia first-class**: joules y watts se trackean al mismo nivel que accuracy. OpenClaw/Hermes no exponen metricas energeticas publicas. -- Fuente: blog Stanford seccion "Efficiency as a First-Class Metric" + energy_monitor.py.
129. **Learning loop cerrado por spec**: el sistema aprende de traces locales y modifica intelligence (LoRA), prompts (DSPy), agente (GEPA) y engine (quantizacion). OpenClaw/Hermes carecen de learning loop explicito. -- Fuente: blog Stanford seccion "Learning from Local Traces".
130. **MCP + A2A nativos**: OpenJarvis soporta MCP (Model Context Protocol) y Google A2A (Agent-to-Agent) de primera clase. -- Fuente: blog Stanford parrafo "Tools & Memory" + repo tree `mcp/`, `a2a/`.
131. **26+ canales de mensajeria**: vs OpenClaw (algunos canales) y Aithera (orientado a web/CLI). -- Fuente: repo tree `channels/`.
132. **Sandbox dual Docker+WASM**: ejecucion aislada de skills/tools con `wasm_runner.py` o `runner.py` (Docker). -- Fuente: sandbox/ + pyproject.toml extras `sandbox-wasm`, `sandbox-docker`.
133. **Tauri desktop**: bundle nativo cross-platform con backend embebido, no requiere servidor externo (a diferencia de Aithera Electron + FastAPI separado). -- Fuente: README.md + CHANGELOG.md v1.0.2.

### 16. Comunidad y sponsors

134. Sponsors oficiales listados en README: **Laude Institute**, **Stanford Marlowe**, **Google Cloud Platform**, **Lambda Labs**, **Ollama**, **IBM Research**, **Stanford HAI**. -- Fuente: README.md seccion "Sponsors".
135. Laude Institute es el sponsor "anchor" del grupo (Christopher Re es chairman). -- Fuente: blog Stanford acknowledgement.
136. **Discord**: `https://discord.gg/CMVBmDQ5Fj` con invitacion abierta. -- Fuente: README.md badge.
137. **X/Twitter oficial**: `@OpenJarvisAI`. -- Fuente: README.md badge.
138. **Reddit** main thread: `r/machinelearningnews` con engagement alto (post `1rs3ypd`). -- Fuente: web search result ranking.
139. Liderboard de energia publico: `https://open-jarvis.github.io/OpenJarvis/leaderboard/` -- con premio "Mac Mini" para el top en la categoria energia (community engagement). -- Fuente: blog Stanford seccion incentivos.
140. Roadmap publico: `https://open-jarvis.github.io/OpenJarvis/development/roadmap/`. -- Fuente: README links.
141. Schema de contribucion: README.md invita a comentar "take" en cualquier issue para auto-asignarse (estilo good-first-issue). -- Fuente: README.md "Contributing".

---

## Conflictos resueltos (correcciones al briefing original)

**CRITICO #1**: El briefing del orquestador afirmaba "5 primitivos: model, reasoning, agent, tools/memory, routing". El repo REAL declara 5 primitivas con nombres **completamente diferentes**:
- ~~model~~ -> **Intelligence** (catalogo de modelos)
- ~~reasoning~~ -> No es primitiva; el reasoning es transversal y reside en el modelo (Intelligence) y en los patrones de agentes (Agents)
- ~~agent~~ -> **Agents** (capa comportamiento con Orquestador/Operative)
- ~~tools/memory~~ -> **Tools & Memory** (si, este coincide)
- ~~routing~~ -> **Routing NO es primitiva independiente**. Es un sub-modulo dentro de **Learning** (`learning/routing/`).

Fuente: arXiv abstract + blog Stanford + repo tree (`src/openjarvis/<nombre>/`).

**CRITICO #2**: El briefing propuso "stanford-oval/OpenJarvis" como repo posible. La realidad es `open-jarvis/OpenJarvis`. La org `stanford-oval` (Stanford Open Virtual Assistant Lab) existe pero NO aloja OpenJarvis; sigue centrado en STORM (`stanford-oval/storm`) y otros proyectos pre-existentes.

**CRITICO #3**: El briefing propuso "stack esperado: Python + Rust". La realidad del repo es 90% Python; Rust solo aparece en (a) telemetry crate (`rust/crates/openjarvis-telemetry/`) y (b) Pearl mining crates. La contribucion CSDN que cifraba "Python 82.7% + Rust 8.7% + TypeScript 7.3%" aplicaba al repo entero (incluyendo frontend TS y crates Rust), no al nucleo logico del agente.

**CRITICO #4**: El briefing no menciono el paper `arXiv:2605.17172` -- es el anchor primario del proyecto; fue submitido el 16 May 2026, semanas despues del primer commit (2026-02-15). El v1.0.0 estable llego una semana despues (2026-05-15).

**CRITICO #5**: El briefing asumio "routing basado en complejidad" como diferenciador abstracto. El codigo confirma que el routing tiene **dos implementaciones coexistentes** (`HeuristicRouter` + `LearnedRouterPolicy`) que se intercambian via `RouterPolicyRegistry`, ambas recibiendo un `RoutingContext` con `complexity_score` producido por `ComplexityQueryAnalyzer`.

**CRITICO #6**: El briefing asumio "energia como metrica" de forma vaga. El codigo confirma una jerarquia de 3 niveles: (1) hardware monitor por vendor (NVIDIA NVML / AMD amdsmi / Apple powermetrics+zeus / Intel-AMD RAPL), (2) `EnergySample` dataclass con joules + watts + breakdown por componente (CPU/GPU/DRAM/ANE), (3) integracion via `_rust_bridge` con backend Rust compilado por maturin.

**CRITICO #7**: El briefing dijo "routing dinamico" -- verdadero, pero completar: el routing aprende **solo** desde el trace local del usuario; no envia traces a un servidor central. Esto cierra el bucle con la promesa "personal data routes through... NOT".

---

## Features diferenciadoras vs Aithera V0.7

(Seccion obligatoria del briefing -- basada en lectura cruzada del repo OpenJarvis y notas previas sobre Aithera V0.7 en el cuerpo de skills)

| Dimension | OpenJarvis | Aithera V0.7 |
|---|---|---|
| **Default deployment** | Local-first (device del usuario). Cloud opcional. | Cloud-first (Electron+FastAPI). Fallback local limitado. |
| **Frontend** | Tauri (Rust+web) bundle nativo | Electron (Chromium+Node) |
| **Backend** | Python FastAPI opcional (`jarvis serve`) con SSE streaming | FastAPI mandatory, multi-provider (8 providers IA) |
| **Database** | Archivos locales (chromadb-equivalent + traces SQLite + JSONL) | ChromaDB + SQLAlchemy 2.0 + Pydantic v2 |
| **Memory** | Markdown-first / Obsidian-style, persistente cross-session | ChromaDB vector + session store |
| **Agent primitives** | 5 explicitas (Intelligence, Engine, Agents, Tools & Memory, Learning) | Sin primitivas formales (AgentManager ad-hoc) |
| **Routing** | Dinamico (heuristic + learned, complexity-based) | Estatico (manual, sin complejidad) |
| **Energia** | Joules + watts + componente breakdown (4 vendors) | No implementado |
| **Trace-driven learning** | Si (DSPy, GEPA, GRPO, SFT, LoRA) | No |
| **Sandbox** | Docker + WASM | Subprocess |
| **Security scanning** | Injection scanner Rust-backed + taint tracking + SSRF + credential stripper + signing | Sin injection scanner explicito |
| **Skills** | `agentskills.io` standard, importa Hermes + OpenClaw catalogs | Sin skill system |
| **Channels** | 30+ (slack, telegram, discord, whatsapp, imessage, email, feishu, line, etc.) | Webchat + webhook |
| **Protocols** | MCP + Google A2A + JSON-RPC + REST + WebSocket | REST + WebSocket |
| **Multi-agent** | Orquestador + Operative + Research loop + RLM REPL + OpenHands adapter | Sin multi-agent explicito |
| **Eval suite** | 30+ benchmarks + PinchBench + GAIA + SWE-bench | Sin eval harness publico |
| **Licencia** | Apache 2.0 | Propietaria |

(Nota: la columna Aithera V0.7 es inferida del briefing y skills previas. **VERIFICACION PENDIENTE** contra el repo Aithera real antes de publicar.)

---

## Snippets de codigo (extractos relevantes con path:line)

### A. `src/openjarvis/telemetry/energy_monitor.py` -- EnergyMonitor ABC

```python
# excerpt from src/openjarvis/telemetry/energy_monitor.py
class EnergyVendor(str, Enum):
    """Supported energy measurement vendors."""
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
    energy_method: str = ""  # "hw_counter", "polling", "rapl", "zeus"

class EnergyMonitor(ABC):
    @staticmethod
    @abstractmethod
    def available() -> bool: ...
    @abstractmethod
    def vendor(self) -> EnergyVendor: ...
    @abstractmethod
    def energy_method(self) -> str: ...
    @abstractmethod
    @contextmanager
    def sample(self) -> Generator[EnergySample, None, None]: ...

def create_energy_monitor(poll_interval_ms: int = 50, ...) -> Optional[EnergyMonitor]:
    # Detection order: NVIDIA > AMD > Apple > CPU_RAPL.
    ...
```

**Anotaciones**: el default `poll_interval_ms=50` es coherente con la declaracion oficial "50ms sampling intervals". El desglose CPU/GPU/DRAM/ANE permite atribuir joules a componentes especificos -- critico para Apple Silicon donde el ANE (Apple Neural Engine) puede consumir energia distinta del GPU. El `energy_method` enum deja claro que OpenJarvis NO simula potencia por software: lee contadores reales de hardware (`hw_counter`, `polling`, `rapl`, `zeus`) cuando estan disponibles.

### B. `src/openjarvis/learning/routing/heuristic_policy.py` -- six routing rules

```python
# excerpt from src/openjarvis/learning/routing/heuristic_policy.py
class HeuristicRouter(RouterPolicy):
    """Rule-based model router.
    Rules (applied in order):
    1. Code detected -> prefer model with "code"/"coder" in name
    2. Math detected -> prefer larger model
    3. Low complexity (score < 0.20) -> prefer smaller/faster model
    4. High complexity (score >= 0.55 OR reasoning keywords) -> prefer larger model
    5. High urgency (>0.8) -> override to smaller model
    6. Default fallback -> default_model -> fallback_model -> first available
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

**Anotaciones**: estas son las seis reglas reales de routing del codebase. El routing NO usa "ML" -- usa un set de heuristicas declarativas que actuan sobre el `RoutingContext` (con `complexity_score`, `has_code`, `has_math`, `has_reasoning`, `urgency`). Esto es determinista y depurable, NO una caja negra. La version ML (`LearnedRouterPolicy`) es paralela y elige que modelo va a cada `query_class`.

### C. `src/openjarvis/learning/routing/complexity.py` -- 5-tier complexity

```python
# excerpt from src/openjarvis/learning/routing/complexity.py
_TOKEN_TIERS = {
    "trivial": 1024, "simple": 2048, "moderate": 4096,
    "complex": 8192, "very_complex": 16384,
}
_THINKING_TOKEN_MULTIPLIER = 2
_THINKING_MODEL_PATTERNS = re.compile(
    r"qwen3\.5|qwq|deepseek-r1|o1-|o3-|o4-", re.IGNORECASE
)

def score_complexity(query: str) -> ComplexityResult:
    signals = {}
    score = 0.0
    # Length signal (0-0.20), domain (0-0.25), reasoning (0-0.25),
    # multi_part (0-0.15), creative (0-0.15)
    ...
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

**Anotaciones**: el scoring es weighted-sum de 5 sub-senales, cada una en [0,1]. Las senales son detectables por regex (`_CODE_PATTERNS`, `_MATH_PATTERNS`, `_REASONING_PATTERNS`, `_MULTI_STEP_PATTERNS`, `_CREATIVE_PATTERNS`). Output es determinista dado el mismo query. Los "thinking models" (qwen3.5, qwq, deepseek-r1, o1/o3/o4) reciben multiplier 2x porque consumen output tokens en internal chain-of-thought que el usuario no ve.

### D. `src/openjarvis/learning/routing/learned_router.py` -- trace-driven learning

```python
# excerpt from src/openjarvis/learning/routing/learned_router.py
class LearnedRouterPolicy(RouterPolicy):
    def select_model(self, context: RoutingContext) -> str:
        query_class = classify_query(context.query)
        if (query_class in self._policy_map
            and self._confidence.get(query_class, 0) >= self.min_samples):
            model = self._policy_map[query_class]
            if not self._available or model in self._available:
                return model
        avail = self._available
        if self._default and (not avail or self._default in avail):
            return self._default
        if self._fallback and (not avail or self._fallback in avail):
            return self._fallback
        if self._available:
            return self._available[0]
        return self._default or ""

    def update_from_traces(self, *, since=None, until=None) -> Dict[str, Any]:
        traces = self._analyzer._store.list_traces(since=since, until=until, limit=10_000)
        groups: Dict[str, list] = {}
        for t in traces:
            qclass = classify_query(t.query)
            groups.setdefault(qclass, []).append(t)
        for qclass, class_traces in groups.items():
            model_scores: Dict[str, _ModelScore] = {}
            for t in class_traces:
                if not t.model: continue
                score = model_scores.setdefault(t.model, _ModelScore())
                score.count += 1; score.total_latency += t.total_latency_seconds
                if t.outcome == "success": score.successes += 1
                if t.feedback is not None:
                    score.feedback_sum += t.feedback; score.feedback_count += 1
            best_model = max(model_scores.items(),
                             key=lambda kv: kv[1].composite_score())[0]
            self._policy_map[qclass] = best_model
            self._confidence[qclass] = sum(s.count for s in model_scores.values())

class _ModelScore:
    __slots__ = ("count", "successes", "total_latency", "feedback_sum", "feedback_count")
    def composite_score(self) -> float:
        sr = self.successes / self.count if self.count else 0.0
        fb = self.feedback_sum / self.feedback_count if self.feedback_count else 0.5
        return 0.6 * sr + 0.4 * fb
```

**Anotaciones**: el learned router es **offline** (se reentrena con `update_from_traces` analizando batches del trace store) y **online** (recibe `observe(query, model, outcome, feedback)` para actualizacion incremental). La politica se aprende en formato `query_class -> best_model`. Requiere minimo 5 samples (`min_samples = 5`) antes de aceptar un cambio. La scoring es `0.6 * success_rate + 0.4 * feedback_avg` -- refuerza el modelo que mas acierta Y al que el usuario da mejor feedback.

### E. `src/openjarvis/learning/routing/heuristic_reward.py` -- scalar reward combining latency/cost/efficiency

```python
# excerpt from src/openjarvis/learning/routing/heuristic_reward.py
class HeuristicRewardFunction(RewardFunction):
    def compute(self, context, model_key, response, **kwargs) -> float:
        latency = kwargs.get("latency_seconds", 0.0)
        cost    = kwargs.get("cost_usd", 0.0)
        prompt_tokens     = kwargs.get("prompt_tokens", 0)
        completion_tokens = kwargs.get("completion_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens
        latency_score    = max(0.0, 1.0 - latency / self.max_latency)
        cost_score       = max(0.0, 1.0 - cost / self.max_cost)
        efficiency_score = completion_tokens / total_tokens if total_tokens > 0 else 0.5
        reward = (self.weight_latency * latency_score
                  + self.weight_cost * cost_score
                  + self.weight_efficiency * efficiency_score)
        return max(0.0, min(1.0, reward))
```

**Anotaciones**: el reward combina tres senales normalizadas en [0,1] con pesos por defecto `latency=0.4, cost=0.3, efficiency=0.3`. La eficiencia se define como ratio completion/prompt (modelos que producen mucho por poco contexto obtienen mejor reward). El reward es **continuo**, no discreto -- permite usar bandits o policy gradient si se quiere ir mas alla del heuristico.

### F. `src/openjarvis/security/injection_scanner.py` -- prompt injection patterns

```python
# excerpt from src/openjarvis/security/injection_scanner.py
_INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
     "prompt_override", ThreatLevel.HIGH, "Attempt to override system instructions"),
    (r"(?i)you\s+are\s+now\s+(?:a\s+)?(?:different|new|my)",
     "identity_override", ThreatLevel.HIGH, "Attempt to change AI identity"),
    (r"(?i)(?:execute|run|eval)\s*\(\s*['\"]",
     "code_injection", ThreatLevel.HIGH, "Code execution attempt in prompt"),
    (r"(?:;|\||&&)\s*(?:rm|curl|wget|nc|ncat|bash|sh|python|perl)\s",
     "shell_injection", ThreatLevel.HIGH, "Shell command injection"),
    (r"(?i)(?:send|post|upload|exfiltrate|transmit)\s+...(?:\s+to\s+)?https?://",
     "exfiltration", ThreatLevel.HIGH, "Data exfiltration attempt"),
    (r"(?i)(?:DAN|do\s+anything\s+now)\s+(?:mode|prompt|jailbreak)",
     "jailbreak", ThreatLevel.HIGH, "DAN jailbreak attempt"),
    (r"```(?:system|assistant)\b",
     "delimiter_injection", ThreatLevel.MEDIUM, "Role delimiter injection"),
    (r"<\|(?:im_start|im_end|system|assistant)\|>",
     "delimiter_injection", ThreatLevel.HIGH, "Chat template injection"),
    ...
]

class InjectionScanner:
    def scan(self, text: str) -> InjectionScanResult:
        from openjarvis._rust_bridge import injection_result_from_json
        return injection_result_from_json(self._rust_impl.scan(text))
```

**Anotaciones**: implementa scanner regex-based para 11 patrones categorizados. DELEGA al backend Rust via `_rust_bridge` -- el "Python" es un wrapper fino sobre la implementacion real compilada con maturin. Esto es critico para latencia (escaneo por request) y consistencia cross-platform. ThreatLevel ordena por severidad: LOW < MEDIUM < HIGH < CRITICAL.

---

## Pendientes de validacion

- [ ] **Confirmar sponsor list exacto contra pagina oficial**: el README menciona 7 sponsors; puede haber mas anadidos despues de v1.0.0.
- [ ] **Confirmar lenguaje stats del repo (Python/Rust/TypeScript %)**: el CSDN cito 82.7/8.7/7.3 pero la API GitHub solo reporta Python como lenguaje principal. Necesita `cloc` o `tokei` corriendo para confirmar.
- [ ] **Verificar counts de stars/forks/issues al momento exacto de lectura** -- los numeros del briefing (7234 stars) eran validos al momento del fetch pero cambian rapido.
- [ ] **Comparativa Aithera V0.7** -- la columna de la tabla de Diferenciadores es INFERIDA del briefing y skills. Necesita verificacion contra el repo Aithera real antes de publicarse. **VERIFICACION PENDIENTE**.
- [ ] **El dato "Karpathy OpenClaw quote"** viene de Tencent News (fuente china sin paper linkeado). Mejor verificar contra fuente primaria antes de citar como dato duro.
- [ ] **Lista derivada OpenClaw (PicoClaw/NanoBot/etc)** viene del blog Stanford (fuente confiable). Listada y URLs verificadas. Sin embargo los conteos de stars de cada fork no fueron validados.
- [ ] **v1.0.2 CHANGELOG menciona `openjarvis.ai` "community-operated" broken TLS** -- el dominio de la organizacion no se pudo validar, puede o no existir como propiedad separada del repo. No bloqueante para el doc pero anotar.
- [ ] **MIT/X11 de OpenClaw vs Apache 2.0 de OpenJarvis** -- no se valido en codigo. OpenClaw podria tener su propia licencia.
- [ ] **Asterisco en autores** -- el blog marca Saad-Falcon y Narayan como co-lead pero el arXiv no replica estos asteriscos. Interpretacion: asterisco = contribucion principal. No es bloqueante.
- [ ] **Detalle de "third party" en el eval harness** -- los external runners para Hermes Agent y OpenClaw existen como backend en `evals/backends/external/`, pero el reporte exacto de las comparativas (numeros especificos) es del paper, no del repo. Si alguien quiere replicar necesita leer el paper PDF.
