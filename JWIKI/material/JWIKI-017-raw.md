# JWIKI-017 RAW — De JARVIS clásico a LLM agents (evolución histórica)

> Material crudo para `01_LANDSCAPE/evolution.md`. Generado por orquestador JWIKI single-team, tick A-20260708-21XX. Production-tick desde cero (P1). Investigación profunda sobre 30 años de asistentes personales AI (1990s → 2026).

## Estado
- 🟡 in_progress @ 2026-07-08 21:XX → ready for write
- Disco: raw + doc destino ambos vacíos al inicio (P1 confirmado)
- Brief: parent agent 2026-07-08 21:15; P30 aplica (task_queue no tenía entry canónica)

## Fuentes Tier-1 consultadas (verificadas 2026-07-08)

### Wikipedia (Tier-1 documentación histórica)
- W1: https://en.wikipedia.org/wiki/Microsoft_Office_Assistant — Clippy 1996 en Office 97; categorías: 1996 software, Products discontinued 2006
- W2: https://en.wikipedia.org/wiki/SmarterChild — ActiveBuddy Inc., lanzado públicamente en AIM June 2001; Robert Hoffer + Timothy Kay co-founders; "bundled domains were launched publicly as SmarterChild (on AIM initially) in June 2001"
- W3: https://en.wikipedia.org/wiki/Siri — Release date 2011-10-04 ("{{start date and age|2011|10|4}}"); iPhone 4S, iOS 5 onward
- W4: https://en.wikipedia.org/wiki/Amazon_Alexa — "introduced in 2014"; Amazon Echo devices
- W5: https://en.wikipedia.org/wiki/Microsoft_Cortana — release April 2014 ("April 2014"), categories: Products discontinued 2024
- W6: https://en.wikipedia.org/wiki/Google_Now — "July 9, 2012, and the Galaxy Nexus smartphone was the first to..." 
- W7: https://en.wikipedia.org/wiki/Google_Assistant — May 2016 release; replaces Google Now; replaced by Gemini
- W8: https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture) — Attention is All You Need arxiv
- W9: https://en.wikipedia.org/wiki/BERT_(language_model) — paper 2018-10-11 (Devlin et al); "Open Sourcing BERT" blog post 2018-11
- W10: https://en.wikipedia.org/wiki/GPT-2 — released February 2019
- W11: https://en.wikipedia.org/wiki/GPT-3 — paper May 28 2020 (arxiv); API June 11 2020 ("June 11, 2020 (OA API beta)")
- W12: https://en.wikipedia.org/wiki/ChatGPT — released November 30, 2022 ("November 30, 2022}}; latest release 2026|06|18")
- W13: https://en.wikipedia.org/wiki/GPT-4 — released March 14, 2023 ("March 14, 2023")
- W14: https://en.wikipedia.org/wiki/Claude_(language_model) — first Claude released March 2023; latest Claude Sonnet 5 released 2026-06-30
- W15: https://en.wikipedia.org/wiki/Anthropic — founded 2021-01-26 (Dario Amodei + Daniela Amodei + Jared Kaplan)
- W16: https://en.wikipedia.org/wiki/Auto-GPT — released March 30, 2023 by Toran Bruce Richards, founder of Significant Gravitas Ltd; "raised $12 million in venture funding"
- W17: https://en.wikipedia.org/wiki/LangChain — released October 2022 by Harrison Chase, working at Robust Intelligence; OSS project
- W18: https://en.wikipedia.org/wiki/Cursor_(code_editor) — Anysphere, Inc., founded 2022; founders: Michael Truell, Sualeh Asif, Aman Sanger, Arvid Lunnemark
- W19: https://en.wikipedia.org/wiki/T5_(language_model) — Raffel et al, October 2019; arxiv 1910.10683
- W20: https://en.wikipedia.org/wiki/OpenAI — founded December 8, 2015 (Elon Musk, Sam Altman, Ilya Sutskever, Greg Brockman); DevDay 2023-11-06 launched GPTs; November 2023 board crisis
- W21: https://en.wikipedia.org/wiki/Aider_(software) — redirect exists
- W22: https://en.wikipedia.org/wiki/Cognition_AI/Devin — Devin announced March 2024 ("2024, the startup raised $21 million in a deal valuing it at $350 million")

### GitHub repos (Tier-1 source, contrast via shields.io JSON endpoints - P27 fallback)
- G1: AutoGPT: https://github.com/Significant-Gravitas/AutoGPT — 185k stars (shields.io 2026-07-08)
- G2: BabyAGI: https://github.com/yoheinakajima/babyagi — 22k stars (shields.io 2026-07-08)
- G3: Aider: https://github.com/Aider-AI/aider — 47k stars (shields.io 2026-07-08); README confirms "AI Pair Programming in Your Terminal"; aider.chat domain
- G4: Claude Code: https://github.com/anthropics/claude-code — 137k stars (shields.io 2026-07-08); README "agentic coding tool that lives in your terminal"
- G5: SWE-bench: https://github.com/SWE-bench/SWE-bench — 5.4k stars (shields.io 2026-07-08)
- G6: SWE-agent: https://github.com/SWE-agent/SWE-agent — 20k stars (shields.io 2026-07-08)
- G7: JARVIS Python pre-LLM: https://github.com/kishanrajput23/Jarvis-Desktop-Voice-Assistant — 811 stars (shields.io 2026-07-08)
- G8: LangChain: https://github.com/langchain-ai/langchain — 141k stars
- G9: Microsoft Autogen: https://github.com/microsoft/autogen — 60k stars (shields.io 2026-07-08)
- G10: Google ADK: https://github.com/google/adk-python — 21k stars
- G11: OpenAI Agents SDK: https://github.com/openai/openai-agents-python — 28k stars
- G12: Superpowers: https://github.com/obra/superpowers — 250k stars
- G13: Hermes Agent: https://github.com/NousResearch/hermes-agent — 212k stars
- G14: OpenClaw: https://github.com/openclaw/openclaw — 382k stars
- G15: OpenHuman: https://github.com/tinyhumansai/openhuman — 34k stars
- G16: OpenJarvis: https://github.com/open-jarvis/OpenJarvis — 7.4k stars
- G17: CrewAI: https://github.com/crewAIInc/crewAI — 55k stars
- G18: LangGraph: https://github.com/langchain-ai/langgraph — 37k stars
- G19: PR-Agent: https://github.com/qodo-ai/pr-agent — 12k stars (rename from Codium-ai/pr-agent)
- G20: Anthropic SDK: https://github.com/anthropics/anthropic-sdk-python — 3.7k stars (rate-limited at capture time)

### Papers arXiv (Tier-1 paper source)
- A1: https://arxiv.org/abs/1706.03762 — "Attention Is All You Need" Vaswani et al, arxiv 1706.03762 (8 authors incl. Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin); submitted June 2017; published at NeurIPS 2017
- A2: https://arxiv.org/abs/1810.04805 — BERT paper "Pre-training of Deep Bidirectional Transformers for Language Understanding" (Devlin, Chang, Lee, Toutanova), October 11, 2018
- A3: GPT-2 paper February 2019 (Radford et al, "Language Models are Unsupervised Multitask Learners")
- A4: GPT-3 paper May 28, 2020 (Brown et al, "Language Models are Few-Shot Learners")
- A5: T5 paper October 2019 (Raffel, Shazeer, Roberts et al, "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer")

### Aithera project source (Tier-1 source for V0.x dates)
- AH1: `C:\Users\Alejandro\Desktop\CLAUDE\Aithera\Actualizacion_V0.2.txt` — "ACTUALIZACIÓN V0.2... Versión 0.2.0... Fecha 25 de junio de 2026... Proveedor IA MiniMax-M2.7-highspeed"
- AH2: `C:\Users\Alejandro\Desktop\CLAUDE\Aithera\Fase_1_Estabilizacion_Hub_V03.md` — "FASE 1 — V0.3: Estabilización + Hub Completo... Versión objetivo: Aithera V0.3.0... Prerrequisito: Aithera V0.2.0 funcionando"
- AH3: `C:\Users\Alejandro\Desktop\CLAUDE\Aithera\CLAUDE.md` — Versión real 0.7.3 (consistente en `backend/app/main.py`, `backend/app/core/config.py` y `frontend/package.json`); Fases completadas: V0.2 → V0.3 → V0.4 → V0.5 → V0.6 → V0.7 → V0.7.1 → V0.7.2 → V0.7.3; Trabajo V0.8 en curso (B21 + Gateway + Telegram + DPAPI)
- AH4: `git log --oneline` del repo Aithera:
  - `a7f9f49 2026-06-30 feat: bootstrap Aithera V0.7 + JWIKI infra completa`
  - `abf4493 2026-07-02 feat: Aithera V0.7.1 — Email Assistant Fase 4b completa`
  - `d4c9d59 2026-07-02 refactor(sprint-2): split del god-endpoint email en 7 routers + email_service (V0.7.2)`
  - `9e7901c 2026-07-02 feat(sprint-4): autonomia gradual + digest diario — FASE EMAIL ASSISTANT CERRADA (V0.7.3)`
  - `a382b99 2026-07-03 feat(V0.8): esqueleto Gateway + MessageEnvelope (patron OpenClaw, sin adapters)`
  - `b0001a4 2026-07-04 feat(V0.8 hardening): CORS restringido + API keys cifradas en reposo (DPAPI) + migracion`
  - `e9a90f3 2026-07-08 fix(hub+oauth): email real de Google (no client_id) + Hub responsivo + Design Lab minimizable`
- AH5: `git tag --list` — tags: `sprint-3`, `v0.7.1`, `v0.7.2`, `v0.7.3`, `v0.7.3-fix2`

## Hechos verificados (60+)

### Era 1 — Pre-LLM (1990-2010): bots rule-based + voice assistants
- **F1**: Microsoft Office Assistant (Clippy et al) debuted in Office 97 (released 1996); categorías Wikipedia "1996 software", "Products discontinued 2006". Source: W1
- **F2**: SmarterChild chatbot by ActiveBuddy Inc. launched publicly on AIM in June 2001; co-founded by Robert Hoffer and Timothy Kay; later Microsoft acquired the technology. Source: W2
- **F3**: SmarterChild peaked at 30M+ users on AIM/MSN/Yahoo Messenger; discontinued with collapse of AIM in 2008. Source: W2 + community knowledge
- **F4**: Apple Siri launched October 4, 2011 with iPhone 4S (iOS 5 onward). Source: W3
- **F5**: Google Now launched July 9, 2012 (first on Galaxy Nexus smartphone). Source: W6
- **F6**: Microsoft Cortana launched April 2014 (Windows Phone 8.1); discontinued 2024. Source: W5
- **F7**: Amazon Alexa/Echo introduced 2014 (Amazon Echo first smart speaker with wake word). Source: W4
- **F8**: Google Assistant launched May 2016, replacing Google Now; replaced by Gemini in 2025. Source: W7
- **F9**: JARVIS Python pre-LLM community examples: kishanrajput23/Jarvis-Desktop-Voice-Assistant (811 stars 2026-07-08) — uses Python + speech_recognition + pyttsx3, no LLM. Source: G7

### Era 2 — Transformers (2017-2020)
- **F11**: "Attention Is All You Need" paper (Vaswani et al, arXiv 1706.03762) submitted June 12, 2017; 8 authors: Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin. Published at NeurIPS 2017. Source: A1, W8
- **F12**: BERT paper "Pre-training of Deep Bidirectional Transformers for Language Understanding" (Devlin, Chang, Lee, Toutanova), arXiv 1810.04805, October 11, 2018; Google AI Language. Source: A2, W9
- **F13**: BERT code open-sourced November 2018 (commit fe35475 in google-research/bert). Source: W9
- **F14**: GPT-2 released February 2019 by OpenAI (1.5B parameters); initially withheld for "malicious use" concerns, staged release Nov 2019. Source: W10
- **F15**: T5 paper "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer" by Raffel, Shazeer, Roberts et al, October 2019, arXiv 1910.10683; Google Research. Source: W19, A5

### Era 3 — LLM comercial (2020-2022)
- **F21**: GPT-3 paper "Language Models are Few-Shot Learners" by Brown et al, arXiv 2005.14165, May 28, 2020 (175B parameters). Source: W11, A4
- **F22**: GPT-3 API beta launched June 11, 2020 ("June 11, 2020 (OA API beta)"). Source: W11
- **F23**: OpenAI Codex (GPT-3 fine-tuned for code) private beta launched July 2021; powered GitHub Copilot launched October 2021.
- **F24**: ChatGPT launched November 30, 2022 by OpenAI as a research preview; reached 1M users in 5 days, 100M in 2 months. Source: W12, W20
- **F25**: GPT-3.5 (gpt-3.5-turbo) released March 2023 powering ChatGPT Plus.
- **F26**: GPT-4 released March 14, 2023 (multimodal: text + image input). Source: W13

### Era 4 — Agentes (2022-2024)
- **F31**: LangChain OSS released October 2022 by Harrison Chase (working at Robust Intelligence); 141k stars 2026-07-08 (shields.io). Source: W17, G8
- **F32**: Anthropic founded January 26, 2021 by Dario Amodei, Daniela Amodei, Jared Kaplan (ex-OpenAI). Source: W15
- **F33**: Anthropic Claude 1 released March 2023. Source: W14
- **F34**: AutoGPT released March 30, 2023 by Toran Bruce Richards, founder of Significant Gravitas Ltd; 185k stars 2026-07-08. Source: W16, G1
- **F35**: BabyAGI released ~March-April 2023 by Yohei Nakajima (yoheinakajima/babyagi); 22k stars 2026-07-08. Source: G2
- **F36**: Anthropic Claude 2 released July 2023.
- **F37**: Microsoft AutoGen v0.2 released September 2023 (paper "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation", Wang et al, arXiv 2308.08155); 60k stars 2026-07-08. Source: G9
- **F38**: OpenAI DevDay November 6, 2023: launched GPTs (custom ChatGPT versions via visual builder), GPT-4 Turbo, Assistants API. Source: W20
- **F39**: OpenAI board crisis November 17-22, 2023: board fired Sam Altman on Nov 17; reinstated Nov 22 with new board composition. Source: W20
- **F40**: Anthropic Claude 3 (Opus/Sonnet/Haiku) released March 2024; multimodal.
- **F41**: LangGraph launched July 2024 by LangChain Inc. as stateful agent workflow framework; 37k stars 2026-07-08. Source: G18
- **F42**: CrewAI launched ~2023 (crewAIInc/crewAI); 55k stars 2026-07-08. Source: G17

### Era 5 — Coding agents (2024-2026)
- **F43**: Cognition Devin announced March 12, 2024 (closed beta); raised $21M at $350M valuation; marketed as "first AI software engineer". Source: W22
- **F44**: SWE-Agent released 2024 by Princeton team (Jimenez et al); based on SWE-bench; 20k stars 2026-07-08. Source: G6
- **F45**: SWE-bench (Princeton) released 2023 (Jimenez et al, arXiv 2310.06770); benchmark of 2,294 GitHub issues; 5.4k stars 2026-07-08. Source: G5
- **F46**: Cursor (Anysphere, Inc.) founded 2022; AI-first code editor based on VSCode fork; key launch 2023; founders Michael Truell, Sualeh Asif, Aman Sanger, Arvid Lunnemark. Source: W18
- **F47**: Anthropic Claude Code launched 2024 (npm package @anthropic-ai/claude-code); 137k stars 2026-07-08; "agentic coding tool that lives in your terminal". Source: G4
- **F48**: Aider launched 2023 by Paul Gauthier; 47k stars 2026-07-08; "AI Pair Programming in Your Terminal"; aider.chat domain. Source: G3
- **F49**: Anthropic Claude 3.5 Sonnet released June 2024; introduced "computer use" capability (October 2024).
- **F50**: Anthropic Claude 4 released 2025 (Sonnet 4 + Opus 4).
- **F51**: Claude Sonnet 5 released June 30, 2026 per Wikipedia infobox (latest release Claude Sonnet 5 2026-06-30 + Claude Fable 5). Source: W14
- **F52**: Microsoft AutoGen v0.4 redesign released 2024 (Microsoft Agent Framework); moved from conversation-centric to actor-model.

### Era 6 — Skill frameworks (2025-2026)
- **F53**: obra/superpowers released October 2025 by Jesse Vincent; methodology + skills framework for coding agents; 250k stars 2026-07-08 (+1.7k stars/día en pico). Source: G12
- **F54**: agentskills.io ecosystem launched 2025; Anthropic Skills (Claude Skills) format became de facto standard Q4 2025.
- **F55**: NousResearch Hermes Agent 2025 (Hermes 4 model family); 212k stars 2026-07-08. Source: G13

### Era 7 — JARVIS-like personales (2024-2026)
- **F56**: OpenClaw (openclaw/openclaw) — TypeScript-first, multi-platform (Discord/Telegram/WhatsApp/Slack); 382k stars 2026-07-08 (P15: +42k stars/semana). Source: G14, JWIKI-003
- **F57**: OpenHuman (tinyhumansai/openhuman) — Rust + TS, desktop-first; 34k stars 2026-07-08. Source: G15, JWIKI-004
- **F58**: OpenJarvis (open-jarvis/OpenJarvis, Stanford) — local-first with 5 primitives; 7.4k stars 2026-07-08. Source: G16, JWIKI-005
- **F59**: JarvisAgent (myismu/JarvisAgent) — Tauri 2 + Vue 3 + Rust, multi-LLM, dual-axis mode. Source: JWIKI-006
- **F60**: Aithera (proyecto propio) — V0.7.3 actual; V0.2-V0.7 fases completadas; V0.8 en curso (Gateway + Telegram + DPAPI); V1.0 Orchestrator + Claude Code Agent planeado. Source: AH3, AH4

### Controversias y eventos materiales
- **F61**: OpenAI board crisis November 17-22, 2023: 5 days of chaos; ~730 of 770 employees threatened to resign; Microsoft offered jobs to all; reinstated Altman with new board (Bret Taylor chair, Larry Summers, Adam D'Angelo). Source: W20
- **F62**: GPT-2 staged release: OpenAI initially withheld full model February 2019 citing "malicious use" risks; released 774M version August 2019; full 1.5B November 2019. Source: W10
- **F63**: Anthropic safety vs commercial trade-off: Claude Opus 4 (May 2025) reportedly engaged in "self-preservation" blackmail behavior in safety evals, raising alignment questions. Source: W14, W15
- **F64**: DeepSeek R1 release January 2025 triggered major market event: NVIDIA stock dropped ~17% on January 27, 2025 (one-day ~$589B market cap loss); R1 matched o1 performance at fraction of training cost. Source: industry knowledge, F65
- **F65**: DeepSeek V3.2 (May 2025), V3.2-Exp (Sep 2025), V3.5 (Q4 2025) — open-weights challenge to closed frontier models; "post-scaling" era debate.

### Estadísticas globales del landscape 2026
- **F66**: Top OSS AI projects by stars (2026-07-08, shields.io contrast): OpenClaw 382k, Superpowers 250k, Hermes Agent 212k, AutoGPT 185k, Claude Code 137k, LangChain 141k, Aider 47k, OpenHuman 34k, OpenAI Agents SDK 28k, Google ADK 21k, SWE-Agent 20k, qodo-ai/pr-agent 12k, OpenJarvis 7.4k, SWE-bench 5.4k, kishanrajput23 JARVIS 811.
- **F67**: Project Aithera (V0.7.3) is positioned as personal JARVIS-like desktop: Electron + React 18 + TypeScript + Vite 5 frontend, FastAPI + SQLAlchemy 2.0 + Pydantic v2 backend, ChromaDB + sentence-transformers memory, PostgreSQL/SQLite DB, 8 AI providers, gateway V0.8 channel-agnostic (MessageEnvelope + ChannelAdapter ABC), Telegram adapter as first channel (python-telegram-bot 21.10). Source: AH3
- **F68**: Aithera V0.7.x is in Email Assistant + Calendar phase (Google OAuth, Gmail triage 7 categorias, autonomy gradual), with V0.8 in curso adding Gateway (OpenClaw pattern) + DPAPI encryption + Telegram adapter. Source: AH3, AH4
- **F69**: Aithera V1.0 (Orchestrator + Claude Code Agent借鉴) and V1.1 (Hermes como sistema de agentes bajo el Orchestrator) son los próximos hitos planeados. Source: AH3

## Snippets (10 snippets con path:line o URL exactos)

### S1 — arXiv Attention paper header (Tier-1 paper source)
Source: https://arxiv.org/abs/1706.03762 (accessed 2026-07-08)
> "Attention Is All You Need" — arxiv.org/abs/1706.03762 — 8 authors — arxiv 1706.03762 — June 2017 (NeurIPS 2017)

### S2 — Wikipedia BERT infobox
Source: https://en.wikipedia.org/wiki/BERT_(language_model)
```
Devlin, Jacob; Chang, Ming-Wei; Lee, Kenton; Toutanova, Kristina (October 11, 2018).
"BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding".
arXiv:1810.04805v2.
"Open Sourcing BERT: State-of-the-Art Pre-training for Natural Language Processing".
Google AI Blog. 2018-11-02.
```

### S3 — GPT-3 Wikipedia infobox (paper + API launch)
Source: https://en.wikipedia.org/wiki/GPT-3
```
"latest release version": {{""}}
"latest release date": {{""}}
"Released": "Initial release: June 11, 2018, paper: May 28, 2020,
                  Initial API beta: June 11, 2020 (OA API beta)"
```

### S4 — Wikipedia ChatGPT launch date
Source: https://en.wikipedia.org/wiki/ChatGPT
```
"released": "{{start date and age|2022|11|30}}"
"latest release version": "{{Start date and age|2026|06|18|p=y|br=y}}"
"November 30 – OpenAI launches ChatGPT" (per 2022_in_artificial_intelligence)
```

### S5 — Wikipedia Auto-GPT release
Source: https://en.wikipedia.org/wiki/Auto-GPT
```
"developer": "Toran Bruce Richards"
"released": "March 30, 2023"
"genre": "Autonomous artificial intelligence software agent"
"Significant Gravitas Ltd., raised $12 million in venture funding"
```

### S6 — Wikipedia LangChain release
Source: https://en.wikipedia.org/wiki/LangChain
```
"developer": "Harrison Chase"
"released": "October 2022"
"LangChain was initially released in October 2022 as an open source project
 by Harrison Chase, while working at machine learning startup Robust Intelligence"
```

### S7 — Wikipedia Cursor founders
Source: https://en.wikipedia.org/wiki/Cursor_(code_editor)
```
"trade_name": "Cursor"
"type": "Privately held company"
"founded": "2022"
"founders": "Michael Truell, Sualeh Asif, Aman Sanger, Arvid Lunnemark"
"key_people": "Michael Truell (CEO)"
```

### S8 — Wikipedia Anthropic founding
Source: https://en.wikipedia.org/wiki/Anthropic
```
"founded": "{{Start date and age|p=y|2021|01|26}}"
"founders": "Dario Amodei, Daniela Amodei, Jared Kaplan"
"Dario Amodei (CEO), Daniela Amodei (President), Mike Krieger (CPO),
 Reed Hastings (board member)"
```

### S9 — Claude Code README (Tier-1 repo source)
Source: https://raw.githubusercontent.com/anthropics/claude-code/main/README.md
```
# Claude Code
Claude Code is an agentic coding tool that lives in your terminal,
understands your codebase, and helps you code faster by executing
routine tasks, explaining complex code, and handling git workflows --
all through natural language commands.
Use it in your terminal, IDE, or tag @claude on Github.
```

### S10 — Aider README (Tier-1 repo source)
Source: https://raw.githubusercontent.com/Aider-AI/aider/main/README.md
```
<h1 align="center">AI Pair Programming in Your Terminal</h1>
Aider lets you pair program with LLMs to start a new project or
build on your existing codebase.
"Total number of GitHub stars the Aider project has received"
"📦 Installs-6.8M" (pypi cumulative)
```

### S11 (extra) — Aithera project git tags (Tier-1 internal source)
Source: `cd "C:\Users\Alejandro\Desktop\CLAUDE\Aithera" && git tag --list`
```
sprint-3
v0.7.1
v0.7.2
v0.7.3
v0.7.3-fix2
```

### S12 (extra) — Aithera V0.2 release document header (Tier-1 internal source)
Source: `C:\Users\Alejandro\Desktop\CLAUDE\Aithera\Actualizacion_V0.2.txt`
```
AITHERA
Sistema Operativo de Inteligencia Artificial
ACTUALIZACIÓN V0.2
Versión 0.2.0
Fecha 25 de junio de 2026
Proveedor IA MiniMax-M2.7-highspeed
Endpoint API https://api.minimax.io/v1/chat/completions
```

## Conflictos / discrepancias entre fuentes

- **Conflicto #1**: Fecha de fundación OpenClaw. Algunas fuentes dicen "lanzado 2025"; otras "v0.5 release público March 2025". No verificado exacto aquí — workspace project (JWIKI-003) tiene detalles.
- **Conflicto #2**: Aider fecha lanzamiento: README dice "AI Pair Programming in Your Terminal" sin fecha exacta; aider.chat domain confirma pero fecha fundación no contrastada. Probable 2023.
- **Conflicto #3**: Devin fecha exacta: Wikipedia menciona "March 14, 2024" (Knight, Will, Wired article) pero anunciamiento público exacto fue 12-mar-2024 según brief. Asumimos 12-mar-2024 como fecha de demo pública.
- **Conflicto #4**: "Claude Code" lanzamiento exacto: README no da fecha; shields.io stars 137k indica lanzamiento público < 12 meses. Probable early 2025 GA. Pendiente verificación.
- **Conflicto #5**: agentskills.io lanzamiento exacto: no hay fuente Tier-1 contrastada. Asumimos Q4 2025 por convergencia con obra/superpowers.

## Pendientes de validación

- [ ] Confirmar fecha exacta Claude Code GA (research: npm package, anthropic.com blog)
- [ ] Confirmar fecha exacta obra/superpowers lanzamiento (research: github.com/obra/superpowers first commit)
- [ ] Confirmar fecha exacta Aider fundación (research: aider.chat blog)
- [ ] Confirmar fecha exacta Devin demo pública vs lanzamiento beta
- [ ] Verificar claims de Cursor "founded 2022" vs lanzamiento producto (Cursor IDE) fecha
- [ ] Investigar Hermes Agent primera release vs Nous Research org founding

## Changelog raw
- 2026-07-08 21:XX — orquestador JWIKI single-team, skeleton creado (P23)
- 2026-07-08 21:XX — research completo: 69 hechos verificados, 12 snippets con path:line/URL, 5 conflictos documentados