# Material crudo JWIKI-002 — Comparativa proyectos OSS principales

> **Path destino**: `01_LANDSCAPE/projects.md`
> **Investigador**: aithera-wiki-investigador (turno A)
> **Fecha investigación**: 2026-06-30
> **Estado**: raw (para que `aithera-wiki-escriba` lo convierta en doc final)

---

## Hechos verificados (cronológicos y por proyecto)

### OpenClaw (openclaw/openclaw)

1. **Repositorio principal**: `github.com/openclaw/openclaw` — activo, TypeScript-based. — Fuente: https://github.com/openclaw/openclaw — Fecha acceso: 2026-06-30
2. **Autor**: Peter Steinberger (PSPDFKit founder), desarrollador austríaco. — Fuente: https://ai.zhiding.cn/2026/0202/3178245.shtml — Fecha acceso: 2026-06-30
3. **Historia del nombre (triple rebrand)**: Clawdbot (2 ene 2026) → Moltbot (27 ene 2026) → OpenClaw (final, post-Anthropic legal challenge). — Fuente: https://en.wikipedia.org/wiki/OpenClaw — Fecha acceso: 2026-06-30
4. **Stars**: ~376.000 (a junio 2026, según ranking TOP GitHub AI projects). Rango histórico: pasó de 145k (feb 2026) → 248k (60 días) → 302k → 376k. — Fuente: https://juejin.cn/post/7646606448858365988 — Fecha acceso: 2026-06-30
5. **Licencia**: MIT. — Fuente: https://www.jitendrazaa.com/blog/ai/clawdbot-complete-guide-open-source-ai-assistant-2026/ — Fecha acceso: 2026-06-30
6. **Lenguaje principal**: TypeScript. — Fuente: https://github.com/openclaw/openclaw (snippet observado: "Plain npm install at the repo root…") — Fecha acceso: 2026-06-30
7. **Plataformas de chat integradas**: WhatsApp, Telegram, Discord, Slack, iMessage, Signal, Matrix, WeChat/Lark, etc. (12+). — Fuente: https://github.com/SamurAIGPT/awesome-openclaw — Fecha acceso: 2026-06-30
8. **Modelo agnóstico**: soporta Claude, GPT-4o, Gemini, Ollama (local). — Fuente: https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30
9. **Skills**: 13.729 skills en ClawHub (clawhub.ai) al 2026-02-28, 1.5M+ descargas acumuladas, 3.286 activos tras auditoría Snyk (ToxicSkills report). — Fuente: https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30
10. **Última versión estable conocida**: v2026.6.5 (publicada ~10 jun 2026, "yyyy.m.patch" naming). — Fuente: https://news.qq.com/rain/a/20260610A05MIA00 — Fecha acceso: 2026-06-30
11. **Frecuencia de release**: marzo 2026 tuvo 13 releases (~cada 2 días). 1.200+ contribuidores, 58.000+ forks. — Fuente: https://openclawvps.io/blog/openclaw-statistics — Fecha acceso: 2026-06-30
12. **Status del fundador**: Peter Steinberger fue contratado por OpenAI; el proyecto pasó a mantenimiento de open source foundation. — Fuente: https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30
13. **Posicionamiento crítico**: Andrej Karpathy (ex-Tesla AI director) lo llamó "literal dumpster fire" en febrero 2026 — 512 vulnerabilidades reportadas en auditoría, 8 críticas. 20K+ instancias expuestas en internet. — Fuente: https://news.qq.com/rain/a/20260315A00GCR00 — Fecha acceso: 2026-06-30

### OpenHuman (tinyhumansai/openhuman)

14. **Repositorio**: `github.com/tinyhumansai/openhuman` — Fuente: https://github.com/tinyhumansai/openhuman — Fecha acceso: 2026-06-30
15. **Autor/organización**: tinyhumansai (equipo open source, GNU license). — Fuente: https://blog.csdn.net/luolaihua2018/article/details/161323420 — Fecha acceso: 2026-06-30
16. **Licencia**: GNU (no MIT). — Fuente: https://blog.csdn.net/luolaihua2018/article/details/161323420 — Fecha acceso: 2026-06-30
17. **Stack**: Rust (backend core) + Tauri (desktop shell) + React/TypeScript (frontend). — Fuente: https://blog.csdn.net/luolaihua2018/article/details/161323420 — Fecha acceso: 2026-06-30
18. **Stars**: ~7.8k (junio 2026, según ranking). — Fuente: https://juejin.cn/post/7646606448858365988 — Fecha acceso: 2026-06-30
19. **Versión actual**: v0.54.7 (versión CSDN), aunque las notas de la wiki mencionan v0.53.43 (mayo 2026) — **CONFLICTO A VERIFICAR**. — Fuentes: https://blog.csdn.net/luolaihua2018/article/details/161323420 (v0.54.7) vs task_queue.md notas (v0.53.43) — Fecha acceso: 2026-06-30
20. **Diferenciador**: Mascot (avatar) que habla/gesticula, integra Google Meet como asistente, sincroniza cada 20 min datos de 118+ servicios. — Fuente: https://ai-bot.cn/openhuman/ — Fecha acceso: 2026-06-30
21. **Memoria**: Memory Tree jerárquico, chunks ≤3k tokens, SQLite local, jerarquía de summaries. — Fuente: https://ai-bot.cn/openhuman/ — Fecha acceso: 2026-06-30
22. **Compresión**: TokenJuice engine para comprimir contexto antes de mandar a LLM. — Fuente: https://blog.csdn.net/luolaihua2018/article/details/161323420 — Fecha acceso: 2026-06-30
23. **Plataformas soportadas**: macOS, Linux, Windows. — Fuente: https://ai-bot.cn/openhuman/ — Fecha acceso: 2026-06-30
24. **Salida voz**: ElevenLabs TTS con lip-sync del mascot. STT para input. — Fuente: https://ai-bot.cn/openhuman/ — Fecha acceso: 2026-06-30
25. **Integraciones OAuth**: Gmail, Notion, GitHub, Slack, Linear, Jira, Stripe, Calendar, Drive. — Fuente: https://ai-bot.cn/openhuman/ — Fecha acceso: 2026-06-30
26. **Obsidian-compatible**: sincroniza datos como .md nativos para Obsidian Vault. — Fuente: https://ai-bot.cn/openhuman/ — Fecha acceso: 2026-06-30

### OpenJarvis (open-jarvis/OpenJarvis)

27. **Repositorio**: `github.com/open-jarvis/OpenJarvis` — Fuente: https://github.com/open-jarvis/OpenJarvis — Fecha acceso: 2026-06-30
28. **Autores**: Stanford Scaling Intelligence Lab + Hazy Research (Christopher Ré's group). Azalia Mirhoseini en author list. — Fuente: https://blog.csdn.net/xianghongtao0116/article/details/161570161 — Fecha acceso: 2026-06-30
29. **Release inicial**: 2026-03-12 bajo Apache 2.0. — Fuente: https://blog.csdn.net/xianghongtao0116/article/details/161570161 — Fecha acceso: 2026-06-30
30. **Licencia**: Apache 2.0. — Fuente: https://blog.csdn.net/xianghongtao0116/article/details/161570161 — Fecha acceso: 2026-06-30
31. **Lenguajes**: Python (82.7%) + Rust (8.7%) + TypeScript (7.3%). — Fuente: https://blog.csdn.net/xianghongtao0116/article/details/161570161 — Fecha acceso: 2026-06-30
32. **Tagline**: "Personal AI, On Personal Devices". — Fuente: https://scalingintelligence.stanford.edu/blogs/openjarvis/ — Fecha acceso: 2026-06-30
33. **Arquitectura (5 primitivos + registry)**: Intelligence (modelo), Engine (inferencia hardware-adaptive), Agents (orquestación), Tools/Memory, Routing (con energía como métrica). — Fuente: https://www.php.cn/faq/2210459.html — Fecha acceso: 2026-06-30
34. **Backends de inferencia soportados**: Ollama, llama.cpp, vLLM, SGLang. — Fuente: https://www.php.cn/faq/2210459.html — Fecha acceso: 2026-06-30
35. **Dato clave (Intelligence Per Watt)**: 88.7% de consultas single-turn resolubles localmente; "inteligencia por vatio" mejoró 5.3x entre 2023-2025. — Fuente: https://news.qq.com/rain/a/20260315A00GCR00 — Fecha acceso: 2026-06-30
36. **Formas de uso**: browser interface, desktop client (macOS/Windows/Linux), Python SDK, CLI. — Fuente: https://www.php.cn/faq/2210459.html — Fecha acceso: 2026-06-30
37. **Distribución**: `pip install openjarvis`. — Fuente: https://www.php.cn/faq/2210459.html — Fecha acceso: 2026-06-30

### JarvisAgent (myismu/JarvisAgent)

38. **Repositorio**: `github.com/myismu/JarvisAgent` — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
39. **Stack**: Tauri 2.0 + Vue 3 + Rust. — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
40. **Stars / licencia**: **NO VERIFICADO** — búsqueda devolvió resultados no específicos. Pendiente de validación por `aithera-frontend` (leer directamente `github.com/myismu/JarvisAgent` para LICENSE + stars).
41. **Propósito declarado**: "AI 驱动的桌面端编程助手" (desktop coding assistant). — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
42. **Soporte LLM**: DeepSeek, Claude, GPT, Gemini, Qwen, Doubao, MIMO (20+ modelos). — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
43. **Sistema de modos doble**: Audience (User/Developer) × WorkMode (Chat/Edit/Plan) ortogonal. — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
44. **Loop agent completo**: intent classification → tool loading → dynamic context injection → SSE streaming → autonomous execution. — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
45. **Snapshot engine**: versionado file-level tree, rollback atómico, branch management, multi-agent sandbox merge. — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
46. **Sub-agent delegation**: main agent orquesta task graph, sub-agents ejecutan en contextos aislados. — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
47. **Plan approval**: tareas complejas → structured proposal → user preview/edit → approve → dependency-graph execution. — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
48. **Persistencia**: SQLite, vista de referencia para evitar doble full-storage, multi-session. — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30
49. **Inspiración**: basado en Claude Code + Codex capabilities. — Fuente: https://blog.csdn.net/muyvf/article/details/161483417 — Fecha acceso: 2026-06-30

### Hermes Agent (NousResearch/hermes-agent)

50. **Repositorio**: `github.com/nousresearch/hermes-agent` — Fuente: https://github.com/nousresearch/hermes-agent — Fecha acceso: 2026-06-30
51. **Autor**: Nous Research (lab fundado 2023 desde Discord, $50M Series A Paradigm + North Island Ventures). — Fuente: https://blog.csdn.net/qq_23625847/article/details/160146769 — Fecha acceso: 2026-06-30
52. **Stars**: ~140.000 (cruzó 140k en <3 meses, citado por NVIDIA). Ranking #47 GitHub global. — Fuente: https://blogs.nvidia.com/blog/rtx-ai-garage-hermes-agent-dgx-spark/ — Fecha acceso: 2026-06-30
53. **Licencia**: MIT. — Fuente: https://blog.csdn.net/yanceyxin/article/details/161090316 — Fecha acceso: 2026-06-30
54. **Lenguaje**: Python (principal), stack secondary Node.js. — Fuente: https://blog.csdn.net/yanceyxin/article/details/161090316 — Fecha acceso: 2026-06-30
55. **Tagline**: "The agent that grows with you". — Fuente: https://github.com/nousresearch/hermes-agent — Fecha acceso: 2026-06-30
56. **Versión inicial**: 2026-02-25 open-source release. — Fuente: https://blog.csdn.net/qq_23625847/article/details/160146769 — Fecha acceso: 2026-06-30
57. **Versión actual**: v0.13.0 (rango v0.2.0 → v0.13.0 en 13 versiones formales). — Fuente: https://blog.csdn.net/yanceyxin/article/details/161090316 — Fecha acceso: 2026-06-30
58. **Diferenciador clave**: Learning loop — auto-crea SKILL.md después de tareas con >5 tool calls o tras retries exitosos. — Fuente: https://news.qq.com/rain/a/20260622A07SB600 — Fecha acceso: 2026-06-30
59. **Self-Evolution**: usa DSPy + GEPA para auto-evolucionar skills, descripciones, prompts y código. — Fuente: https://github.com/NousResearch/hermes-agent-self-evolution — Fecha acceso: 2026-06-30
60. **Plataformas de chat**: Telegram, Discord, Slack, WhatsApp, Feishu, DingTalk (20+). — Fuente: https://blog.csdn.net/yanceyxin/article/details/161090316 — Fecha acceso: 2026-06-30
61. **Soporte modelos**: OpenAI, Anthropic, OpenRouter (200+ modelos). — Fuente: https://blog.csdn.net/yanceyxin/article/details/161090316 — Fecha acceso: 2026-06-30
62. **Storage**: SQLite + FTS5 para sesiones. — Fuente: https://blog.csdn.net/yanceyxin/article/details/161090316 — Fecha acceso: 2026-06-30
63. **Deployment**: $5 VPS, GPU cluster, serverless. — Fuente: https://blog.csdn.net/yanceyxin/article/details/161090316 — Fecha acceso: 2026-06-30
64. **Comparativa OpenClaw vs Hermes**: según ClawCharts, Hermes superó a OpenClaw en nuevos contribuidores/30 días (jun 2026). — Fuente: https://news.qq.com/rain/a/20260622A07SB600 — Fecha acceso: 2026-06-30

### Clawdbot (= OpenClaw precursor)

65. **Estado**: nombre original de OpenClaw del 2 enero 2026 al 27 enero 2026 (~25 días). — Fuente: https://en.wikipedia.org/wiki/OpenClaw — Fecha acceso: 2026-06-30
66. **Repositorio histórico**: mismo que OpenClaw (`openclaw/openclaw`) después del rename. — Fuente: https://en.wikipedia.org/wiki/OpenClaw — Fecha acceso: 2026-06-30
67. **Causa del rename**: Anthropic legal challenge sobre la marca. — Fuente: https://www.cnbc.com/2026/02/02/openclaw-open-source-ai-agent-rise-controversy-clawdbot-moltbot-moltbook.html — Fecha acceso: 2026-06-30
68. **Estado actual**: abandonado como nombre — todo el código y comunidad migrados a OpenClaw. **RECOMENDACIÓN**: fusionar este punto JWIKI-008 con JWIKI-003 (OpenClaw detallado) en una sección histórica "Origen y renombrado". — Fuente: https://en.wikipedia.org/wiki/OpenClaw — Fecha acceso: 2026-06-30

### Superpowers (obra/superpowers)

69. **Repositorio**: `github.com/obra/superpowers` — Fuente: https://github.com/obra/superpowers — Fecha acceso: 2026-06-30
70. **Autor**: Jesse Vincent (obra). — Fuente: https://blog.csdn.net/wangdq_1989/article/details/157127299 — Fecha acceso: 2026-06-30
71. **Fecha de creación**: 2025-07-15. — Fuente: https://medium.com/@tentenco/the-8-claude-code-skills-worth-installing-first-898735fec4b8 — Fecha acceso: 2026-06-30
72. **Stars**: ~215.946 (jun 2026, según ranking TOP 10); otras fuentes mencionan 149k (junio 2026) o 18.5k (enero 2026 — early data). — Fuentes: https://juejin.cn/post/7646606448858365988 (215k), https://www.pulumi.com/blog/claude-code-orchestration-frameworks/ (149k) — **CONFLICTO A VERIFICAR**
73. **Lenguaje**: Shell (herramienta core). — Fuente: https://github.com/obra/superpowers — Fecha acceso: 2026-06-30
74. **Licencia**: MIT (asumida por open-source convention; **PENDIENTE**: leer LICENSE file directamente). — Fuente: https://github.com/obra/superpowers (README visible) — Fecha acceso: 2026-06-30
75. **Propósito**: Framework de skills para coding agents. NO es un agente en sí — es una metodología/collection de skills (TDD, planning, debugging, verification) como Markdown. — Fuente: https://github.com/obra/superpowers — Fecha acceso: 2026-06-30
76. **Plataformas compatibles**: Claude Code (principal), Codex, OpenCode, Cursor. — Fuente: https://juejin.cn/post/7621026569314598938 — Fecha acceso: 2026-06-30
77. **Skills preinstaladas**: 50+ (GitHub operations, code review, project planning, etc.). — Fuente: https://juejin.cn/post/7646606448858365988 — Fecha acceso: 2026-06-30
78. **Diferenciador**: NO es un agente ejecutor — es un complemento que se monta sobre Claude Code / Codex para forzar buenas prácticas (TDD RED-GREEN-REFACTOR, YAGNI, DRY, system debugging). — Fuente: https://blog.csdn.net/wangdq_1989/article/details/157127299 — Fecha acceso: 2026-06-30
79. **Comparativa con OTKB**: similar concept (knowledge base + skills), pero OTKB es Tibia-focused y Superpowers es general coding. — Fuente: inferencia desde la JWIKI architecture — Fecha acceso: 2026-06-30

---

## Snippets de código / arquitectura

### OpenClaw (openclaw/openclaw)
- **Lenguaje principal**: TypeScript (npm-based install, requiere `git clone` + npm install, README explícito: "Plain npm install at the repo root is not a supported source setup"). — Fuente: https://github.com/openclaw/openclaw — Fecha acceso: 2026-06-30
- **Channel adapters**: WhatsApp, Telegram, Discord, Slack, iMessage, Signal, Matrix, WeChat, Lark, QQBot. — Fuente: https://news.qq.com/rain/a/20260610A05MIA00 — Fecha acceso: 2026-06-30
- **Runtime**: contenedor principal con sandbox layer (Docker-based isolation según diagramas técnicos). — Fuente: https://juejin.cn/post/7650133122809774089 — Fecha acceso: 2026-06-30
- **Skill engine**: cada skill = folder con `SKILL.md` (Markdown), cargado por el agent al detectar task matching. — Fuente: https://www.cn486.com/news/4137919/ — Fecha acceso: 2026-06-30

### OpenHuman (tinyhumansai/openhuman)
- **Estructura de proyecto (CSDN analiza v0.54.7)**:
  ```
  openhuman-main/
  ├── src/
  │   ├── main.rs          # openhuman-core binary entry
  │   ├── rpc/             # JSON-RPC dispatch layer
  │   └── openhuman/       # core business (~80 sub-modules)
  │       ├── agent/       # Agent orchestration, sessions, tool calls
  │       └── memory/      # Memory Tree + SQLite
  └── app/                 # React + TypeScript frontend
  ```
  — Fuente: https://blog.csdn.net/luolaihua2018/article/details/161323420 — Fecha acceso: 2026-06-30
- **Memory Tree**: jerarquía de summaries, chunks ≤3k tokens, scoring + folding. — Fuente: https://ai-bot.cn/openhuman/ — Fecha acceso: 2026-06-30
- **CDP Client puerto 19222**: WebView scanning para el mascot. — Fuente: https://blog.csdn.net/luolaihua2018/article/details/161323420 — Fecha acceso: 2026-06-30

### OpenJarvis (open-jarvis/OpenJarvis)
- **Composición de lenguajes**: Python 82.7% / Rust 8.7% / TypeScript 7.3%. Core logic en `src/openjarvis/`. — Fuente: https://blog.csdn.net/xianghongtao0116/article/details/161570161 — Fecha acceso: 2026-06-30
- **5 primitivos**: Intelligence (catálogo de modelos), Engine (router de inference backend), Agents (orquestador Operative/Orchestrator), Tools/Memory, Routing (con telemetría de energía). — Fuente: https://www.php.cn/faq/2210459.html — Fecha acceso: 2026-06-30

### Hermes Agent
- **Estructura de directorios**:
  ```
  hermes-agent/
  ├── run_agent.py
  ├── model_tools.py
  ├── toolsets.py
  ├── cli.py
  └── (SQLite/FTS5 para storage)
  ```
  — Fuente: https://blog.csdn.net/yanceyxin/article/details/161090316 — Fecha acceso: 2026-06-30
- **Mecanismo de auto-skill-creation**: cuando una tarea requiere >5 tool calls O cuando hay retries exitosos después de fallos, se genera automáticamente `SKILL.md`. — Fuente: https://news.qq.com/rain/a/20260622A07SB600 — Fecha acceso: 2026-06-30
- **Self-Evolution** (hermes-agent-self-evolution repo): DSPy + GEPA optimization loop sobre skills, prompts y código. — Fuente: https://github.com/NousResearch/hermes-agent-self-evolution — Fecha acceso: 2026-06-30

### Superpowers (obra/superpowers)
- **Estructura basada en skills**: colección de `SKILL.md` (Markdown con frontmatter) + scripts Shell ejecutables. — Fuente: https://blog.csdn.net/wangdq_1989/article/details/157127299 — Fecha acceso: 2026-06-30
- **Instalación en Claude Code**: `/plugin marketplace add obra/superpowers-marketplace` + `/plugin install superpowers@superpowers-marketplace`. — Fuente: https://juejin.cn/post/7621026569314598938 — Fecha acceso: 2026-06-30

---

## Diferencias entre proyectos

### Modelo de ejecución
- **OpenClaw**: autonomous agent, 24/7 background, local-first pero no exclusively local (cloud APIs opcionales). Skills via SKILL.md plugins.
- **OpenHuman**: desktop-first, mascot paradigm, heavy auto-sync (cada 20 min), persistente memory tree.
- **OpenJarvis**: framework, NO agente standalone — provee primitives para construir agentes. Local-first by design (cloud opcional).
- **JarvisAgent**: desktop coding agent, Tauri+Vue+Rust, modos duales (User/Developer × Chat/Edit/Plan), sub-agent sandboxing.
- **Hermes Agent**: self-improving agent (DSPy+GEPA learning loop), escribe sus propios skills, deployable en VPS barato.
- **Superpowers**: NO es agente — es metodología/skills collection para Claude Code/Codex/Cursor. Complemento, no ejecutor.

### Lenguaje principal
- **OpenClaw**: TypeScript
- **OpenHuman**: Rust (core) + TS (frontend) + Tauri (shell)
- **OpenJarvis**: Python 82% + Rust 8.7% + TS 7.3%
- **JarvisAgent**: Rust + TypeScript + Vue 3 (Tauri 2.0)
- **Hermes Agent**: Python (primary), Node.js secundario
- **Superpowers**: Shell + Markdown skills

### Licencia
- **OpenClaw**: MIT
- **OpenHuman**: GNU (GPL)
- **OpenJarvis**: Apache 2.0
- **JarvisAgent**: NO VERIFICADO
- **Hermes Agent**: MIT
- **Superpowers**: MIT (asumida — PENDIENTE confirmar LICENSE file)

### Stars (junio 2026)
- **OpenClaw**: 376k (líder absoluto)
- **Superpowers**: 215k (segundo)
- **Hermes Agent**: 140k
- **OpenHuman**: 7.8k
- **OpenJarvis**: NO verificado — fuente no reporta
- **JarvisAgent**: NO verificado
- **Clawdbot**: N/A (renombrado)

### Despliegue / Target
- **OpenClaw**: terminal-first, multi-platform chat
- **OpenHuman**: desktop mascot, meeting assistant, heavy personal context
- **OpenJarvis**: framework, dependency-light (pip install), research-oriented
- **JarvisAgent**: desktop coding IDE-style
- **Hermes Agent**: VPS/cluster/serverless, low-resource (5 USD VPS viable)
- **Superpowers**: complemento de Claude Code/Codex (no standalone)

---

## Pendientes de validación

1. **JarvisAgent stars + license**: no se encontró fuente oficial. El agente `aithera-backend` debería leer directamente `github.com/myismu/JarvisAgent` para extraer `LICENSE` file y el contador de stars.
2. **OpenJarvis stars**: Stanford project, no aparece en rankings TOP — verificar si tiene stars bajas por ser reciente (release marzo 2026) o si la fuente china simplemente no lo reportó.
3. **OpenHuman versión**: v0.53.43 (task_queue) vs v0.54.7 (CSDN) — el agente de backend debería clonar el repo y leer `Cargo.toml` o `package.json` para confirmar versión exacta al 2026-06-30.
4. **Superpowers stars conflict**: 215k vs 149k — leer directamente desde GitHub API antes del doc final.
5. **Superpowers license file**: leer directamente LICENSE en repo.
6. **OpenClaw stars exactos a 2026-06-30**: las fuentes van de 302k a 376k — fluctuación rápida por hype; verificar via GitHub API antes del doc final.
7. **Comparativa con Aithera**: el doc final debe incluir una columna/sección donde Aithera se compare con estos proyectos OSS. Aithera ya está documentada en OTKB — enlazar cross-refs.
8. **Riesgos de seguridad OpenClaw**: el doc debe mencionar la auditoría de 512 vulnerabilidades + posición de Karpathy. Esto es información crítica que no debe obviarse.
9. **Pendiente de fusionar JWIKI-008 (Clawdbot)**: como Clawdbot = precursor de OpenClaw, el doc final debe fusionar este punto o anotarlo como "Ver JWIKI-003 sección historia".
10. **Linking con JWIKI-010 (Comparativa frameworks de agentes)**: este doc es de "proyectos OSS personales", JWIKI-010 es de "frameworks de agentes" (LangGraph, CrewAI, AutoGen). Ambos se complementan pero NO se solapan — verificar boundary clara.

---

*Material crudo recopilado por `aithera-wiki-investigador` (turno A, tick 1 — 2026-06-30 13:15). Listo para que `aithera-wiki-escriba` lo convierta en `JWIKI/01_LANDSCAPE/projects.md`.*
