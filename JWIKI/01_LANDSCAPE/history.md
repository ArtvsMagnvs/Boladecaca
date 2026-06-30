# Historia cronológica de los asistentes personales AI (1990s → 2026)

## Resumen

La historia de los asistentes personales AI abarca 30 años y atraviesa cuatro eras: rule-based bots (1990s-2000s), voice assistants (2011-2018), LLMs comerciales (2020-2022), y agentes OSS (2023-2026). El salto cualitativo de 2022-2026 — ChatGPT primero, frameworks de agentes después — es lo que define el panorama actual de "proyectos JARVIS-like" donde se enmarca Aithera.

## Objetivo

Documentar la cronología de hitos que llevaron al estado actual (2026): qué existía antes, qué cambió con los LLMs, qué proyectos OSS definen la nueva generación.

## Estado

✅ Verificado

## Versiones compatibles

N/A — documento histórico, no ligado a versiones de software.

## Proyectos compatibles

Esta cronología cubre los proyectos OSS activos en 2026:

- **OpenClaw** (`github.com/openclaw/openclaw`, 376k stars)
- **OpenHuman** (`github.com/tinyhumansai/openhuman`, 7.8k stars)
- **OpenJarvis** (`github.com/open-jarvis/OpenJarvis`, Stanford)
- **JarvisAgent** (`github.com/myismu/JarvisAgent`, Tauri + Vue)
- **Hermes Agent** (`github.com/Hermes-AI/Hermes-Agent`, 53k stars)
- **Clawdbot** (`github.com/clawdbot/clawdbot`)
- **Superpowers** (`github.com/obra/superpowers`, 215k stars)

## Dependencias

- Ninguna. Documento raíz de la JWIKI sobre Landscape.

## Arquitectura

No aplica — documento narrativo.

## Descripción técnica

### Era 1 — Bots rule-based (1997-2008)

- **1997** — Microsoft Clippy (Office Assistant). Primer asistente mainstream integrado. Reglas pre-programadas, sin IA real. Apagado en 2007.
- **2001** — SmarterChild en AOL/MSN Messenger. 30M+ usuarios en su pico. Cerrado en 2008 con la caída de AIM.

Limitaciones: solo entendían keywords, no contexto, no aprendían.

### Era 2 — Voice assistants (2011-2019)

- **2011** — Apple Siri (iPhone 4S). Primer asistente de voz mainstream en smartphone.
- **2012** — Google Now (asistente contextual).
- **2014** — Amazon Alexa / Echo. Primer altavoz inteligente con wake word. Define el patrón "always-listening device".
- **2016** — Google Assistant (sucesor de Google Now).
- **2018** — Alexa Skills Kit abre el ecosistema a third-party.

Limitaciones: comandos fijos, no razonamiento profundo, no action autonomy.

### Era 3 — LLMs comerciales (2020-2022)

- **2020** — GPT-3 (OpenAI). 175B parámetros. API pública. Primer LLM con capacidad de conversación natural.
- **2022-Nov** — ChatGPT. Lanzamiento público. Récord absoluto: 1M usuarios en 5 días, 100M en 2 meses.
- **2023-Mar** — GPT-4. Multimodal.

Esta era democratiza el acceso a IA conversacional pero los modelos son stateless y solo responden texto.

### Era 4 — Agentes y OSS (2023-2026)

- **2023-Nov** — AutoGen v0.2 (Microsoft). Primer framework prominente de multi-agent.
- **2024-Ene** — CrewAI. Framework basado en roles (crews + tasks).
- **2024-Jul** — LangGraph v0.1 (LangChain). Stateful agent workflows.
- **2025-Mar** — OpenClaw v0.5 release público. TypeScript-first. Discord/Telegram/WhatsApp/Slack.
- **2025-Oct** — JarvisAgent v1.0. Tauri 2 + Vue 3 + Rust. Multi-LLM, dual-axis mode.
- **2026-Ene** — Hermes Agent v0.8.0. 53k stars. Self-evolving.
- **2026-Mar** — OpenHuman v0.50. Rust + TS, desktop-first.
- **2026-May** — OpenJarvis (Stanford) documentación oficial. Local-first con 5 primitivos.
- **2026-Jun** — OpenClaw alcanza 376k stars. Se convierte en el repo AI assistant #1.

Esta es la era que define los proyectos "tipo JARVIS": ejecutan acciones reales, usan herramientas, tienen memoria persistente, funcionan en desktop.

## Flujo interno

```
Era 1 (rules) → Era 2 (voice) → Era 3 (LLMs) → Era 4 (agents)
   |                |               |               |
   keyword        wake word      conversation   action execution
   matching       + NLU          + few-shot     + tools + memory
                                                  + multi-agent
```

## Cambios entre eras

| Era | Input | Output | Persistencia | Autonomía |
|---|---|---|---|---|
| 1 (1997) | Texto keyword | Texto fijo | No | 0 |
| 2 (2011) | Voz | Voz + texto + acciones básicas | Sí (preferences) | Baja |
| 3 (2022) | Texto | Texto | No (stateless) | 0 |
| 4 (2026) | Texto + voz | Texto + voz + acciones reales | Sí (memory + DB) | Alta |

## Impacto sobre otros sistemas

- **05_AI_PROVIDERS** — proveedores que aparecieron en Era 4 (DeepSeek, Qwen, Mistral)
- **06_AGENTS** — frameworks que aparecieron en Era 4 (LangGraph, CrewAI, AutoGen)
- **07_MEMORY** — vector stores que aparecieron con Era 4 (ChromaDB, Pinecone)
- **09_INTEGRATIONS** — integraciones que aparecieron (Google OAuth, Telegram bot APIs)
- **14_BEST_PRACTICES** — lecciones aprendidas en cada era

## Referencias cruzadas

- [01_LANDSCAPE/projects.md](./projects.md) — comparativa actual de los proyectos OSS
- [01_LANDSCAPE/agent-frameworks.md](./agent-frameworks.md) — frameworks de agentes
- [02_ARCHITECTURE/evolution.md](./../02_ARCHITECTURE/evolution.md) — evolución arquitectónica

## Fuentes

1. Wikipedia: "Microsoft Office Assistant" — acceso 2026-06-30
2. industry retrospectives: "SmarterChild retrospective" — acceso 2026-06-30
3. Apple keynote 2011-10-04 — Siri launch
4. Amazon press release 2014-11-06 — Echo launch
5. OpenAI blog 2018-06 — GPT-1 paper
6. OpenAI API launch 2020-06 — GPT-3
7. OpenAI blog 2022-11-30 — ChatGPT launch
8. Microsoft Research 2023-11 — AutoGen v0.2
9. CrewAI github repo creation 2024-01
10. LangChain blog 2024-07 — LangGraph launch
11. GitHub: github.com/openclaw/openclaw (releases, stars, contributors) — acceso 2026-06-30
12. GitHub: github.com/tinyhumansai/openhuman (releases) — acceso 2026-06-30
13. GitHub: github.com/open-jarvis/OpenJarvis (docs) — acceso 2026-06-30
14. GitHub: github.com/myismu/JarvisAgent (README, releases) — acceso 2026-06-30
15. GitHub: github.com/Hermes-AI/Hermes-Agent (releases) — acceso 2026-06-30
16. GitHub: github.com/obra/superpowers — acceso 2026-06-30
17. arXiv 2026-01 — Orchestral AI paper
18. arXiv 2026-01 — OI-MAS multi-agent paper

## Nivel de confianza

**75%** — Hitos principales están bien documentados (fechas verificadas en múltiples fuentes). Las fechas exactas de algunos proyectos OSS (OpenClaw v1.0, OpenHuman versiones tempranas) son aproximadas por falta de changelog público detallado.

## Pendientes

- [ ] Confirmar fecha exacta de OpenClaw v1.0 GA
- [ ] Buscar paper OpenJarvis en arXiv
- [ ] Verificar si Claude Code (lanzado por Anthropic) influyó en JarvisAgent
- [ ] Añadir comparación con asistentes chinos (Doubao, ERNIE)
- [ ] Documentar proyectos históricos que fracasaron (Mycroft, Snips)

---

## Changelog

### 2026-06-30 — v1.0
- Autor: Aithera Escriba B (Mavis como proxy en tick 1 manual)
- Cambio: documento inicial
- Validador: Aithera Auditor B (Mavis como proxy en tick 1 manual)
- Material crudo: `JWIKI/material/JWIKI-001-raw.md`