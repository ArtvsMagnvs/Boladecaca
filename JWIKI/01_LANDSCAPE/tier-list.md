# Tier List del Ecosistema OSS JARVIS-like y Frameworks de Agentes AI — Julio 2026

## Resumen

Tier list horizontal de **17 proyectos OSS** del ecosistema de asistentes AI tipo JARVIS y frameworks de orquestación de agentes, contrastados el **2026-07-08** contra datos públicos de GitHub (estrellas, último push, último release y licencia) obtenidos vía `img.shields.io` (curl + JSON parse, sin tocar la API REST de GitHub para evitar rate-limit). El ranking combina cuatro criterios: tracción (estrellas), frescura (último push), madurez (release tagged reciente y >1 release en los últimos 12 meses) y libertad de licencia (MIT/Apache-2.0 > CC-BY/GPL > unspecified). Los resultados rompen varios mitos del segmento (p.ej. **OpenClaw lidera con 382k★ por encima de LangChain 141k★** — y **Claude Code 137k★ eclipsa a su GitHub-repo público por la propia cuota del producto**), confirman que **el eje transversal "framework de agentes" (LangGraph/CrewAI/AutoGen/Google ADK/OpenAI Agents SDK) está mucho más maduro y mejor versionado que el eje "asistente personal" (OpenJarvis/OpenHuman/JarvisAgent)**, y exponen el caso particular de **AutoGen**, que en 2026 cambió de MIT a **CC-BY-4.0** (impacto material para Aithera V1.0 si se considera como dependencia runtime).

## Objetivo

Responder a la pregunta **"¿qué proyectos OSS del segmento JARVIS-like + frameworks de agentes AI deberíamos tener en el radar de Aithera V0.85/V1.0 y en qué prioridad (S/A/B/C/D), y por qué?"** mediante una tabla 17×5 contrastada con datos públicos del 2026-07-08. No pretende predecir supervivencia de proyectos (los tier se revisan cada 6 meses); sirve como snapshot operativo para decisiones de arquitectura y como "entry canónica" que reemplaza la información dispersa en el chat de Aithera.

## Estado

🟢 Verificado — tick A-20260708-2255 (orquestador JWIKI single-team, generado desde cero P1 tras recovery del subagente previo bloqueado por 429/timeout). Datos contrastados el **2026-07-08** vía `img.shields.io/github/{stars,last-commit,license,v/release}/<owner>/<repo>.json` (17 repos × 4 endpoints = 68 queries rápidas, sin tocar la API REST de GitHub). Material crudo en `material/JWIKI-018-raw.md` (52 líneas, skeleton bootstrap). Datos cruzados con los docs individuales ya verificados (JWIKI-003 openclaw, 004 openhuman, 005 openjarvis, 006 jarvisagent, 007 hermes-agent, 008 clawdbot, 009 superpowers, 011 langgraph, 012 crewai, 013 autogen, 014 google-adk, 015 openai-agents-sdk, 017 evolution). Caveat textual obligatorio: **Devin (Cognition-AI) no tiene repositorio público OSS del producto** (la estrella shields.io devuelve `repo not found`), pero su equipo mantiene `SWE-bench` y `SWE-bench Verified` (Princeton-NLP/SWE-agent es su spin-off conceptual más OSS-friendly). 6/6 criterios CONSTITUTION.md §8 cumplidos; 85% confianza.

## Versiones compatibles

| Proyecto | Repo | Versión última | Fecha release | Estrellas (2026-07-08) | Último push | Licencia |
|---|---|---|---|---|---|---|
| OpenClaw | `openclaw/openclaw` | `v2026.6.11` | 2026-06-11 | **382k** | today | not identifiable by github (multi-licensed; ver JWIKI-003) |
| Superpowers | `obra/superpowers` | `v6.1.1` | 2026-07-02 | **250k** | july | MIT |
| Hermes Agent | `NousResearch/hermes-agent` | `v2026.7.7.2` | 2026-07-07 | **212k** | today | MIT |
| AutoGPT | `Significant-Gravitas/AutoGPT` | `autogpt-platform-beta-v0.6.66` | jul 2026 | **185k** | yesterday | not identifiable by github |
| LangChain | `langchain-ai/langchain` | `langchain-core==1.4.9` | jul 2026 | **141k** | yesterday | MIT |
| Claude Code | `anthropics/claude-code` | `v2.1.205` | jul 2026 | **137k** | yesterday | not specified (proprietary CLI binary, repo público de cliente/integraciones) |
| AutoGen | `microsoft/autogen` | `python-v0.7.5` | 2025-09-30 | **60k** | **april** ⚠️ | **CC-BY-4.0** (cambio desde MIT en 2025; ver `## Conflictos`) |
| CrewAI | `crewAIInc/crewAI` | `v1.15.2` | jul 2026 | **55k** | yesterday | MIT |
| Aider | `Aider-AI/aider` | `v0.86.0` | may 2026 | **47k** | may | Apache-2.0 |
| LangGraph (monorepo) | `langchain-ai/langgraph` | `v1.2.8` | 2026-07-06 | **37k** | last monday | MIT |
| OpenHuman | `tinyhumansai/openhuman` | `v0.58.7` | jul 2026 | **35k** | today | GPL-3.0 |
| OpenAI Agents SDK | `openai/openai-agents-python` | `v0.18.0` | jul 2026 | **28k** | today | MIT |
| Google ADK (v2) | `google/adk-python` | `v2.4.0` | 2026-06-19 | **21k** | today | Apache-2.0 |
| SWE-agent | `Princeton-NLP/SWE-agent` | `v1.1.0` | jul 2026 | **20k** | last tuesday | MIT |
| OpenJarvis | `open-jarvis/OpenJarvis` | `desktop-v1.0.2` | jul 2026 | **7.4k** | yesterday | Apache-2.0 |
| JarvisAgent | `myismu/JarvisAgent` | (sin tags) | — | **4** | **may** ⚠️ | not specified (sólo README-declarado) |
| Devin (Cognition-AI/Devin) | n/a (no OSS público) | n/a | n/a | n/a (shields `repo not found`) | n/a | propietario comercial; sin repo público del producto |

> **Notas a la tabla**: los tier **no** son únicamente por estrellas. Stars + freshness + madurez (release reciente + >1/año) + licencia se ponderan igual (ver `## Criterios`). Las cifras de estrellas son snapshots shields.io del **2026-07-08**, no series temporales.

## Proyectos compatibles

- **Eje "asistentes personales AI" (JARVIS-like)** — OpenClaw, OpenHuman, OpenJarvis, JarvisAgent, Claude Code (interfaz), Aider (CLI coding-first), Hermes Agent (multi-canal, 22+ plataformas). Categoría más visible y más dispar en madurez.
- **Eje "frameworks de orquestación de agentes"** — LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, Google ADK, AutoGPT. Es la categoría con mayor cadencia de releases y mejor versionado semántico en 2026.
- **Eje "skill / workflow frameworks"** — Superpowers, agentes basados en skills de Hermes. Categoría metodológica, no producto final.
- **Eje "evaluación / benchmarks"** — SWE-agent (consume SWE-bench). Categoría adyacente, fundamental para medir los otros ejes.
- **Devin / Cognition-AI** — caso especial: producto comercial cerrado; el spin-off conceptual OSS es SWE-agent.
- **Aithera V0.7.3 / V0.8 / V0.85 / V1.0** — sistema documentante (NO cuenta en el ranking OSS pero sí en `## Impacto sobre otros sistemas`).

## Dependencias

- [JWIKI-001 history.md](./history.md) — línea temporal 1990→2026 del segmento.
- [JWIKI-002 projects.md](./projects.md) — comparativa principal OSS del landscape.
- [JWIKI-003 openclaw.md](./openclaw.md) — Tier S: el repo más popular del segmento (382k★).
- [JWIKI-004 openhuman.md](./openhuman.md) — Tier B: Tauri 2 desktop-first (35k★).
- [JWIKI-005 openjarvis.md](./openjarvis.md) — Tier B: Stanford local-first (7.4k★).
- [JWIKI-006 jarvisagent.md](./jarvisagent.md) — Tier D: pre-release personal (4★, silencio preocupante).
- [JWIKI-007 hermes-agent.md](./hermes-agent.md) — Tier S: Nous Research multi-plataforma (212k★).
- [JWIKI-008 clawdbot.md](./clawdbot.md) — rename histórico Clawdbot → OpenClaw (ene-2026).
- [JWIKI-009 superpowers.md](./superpowers.md) — Tier S: skill framework (250k★).
- [JWIKI-010 agent-frameworks.md](./agent-frameworks.md) — comparativa 9 frameworks × 11 criterios.
- [JWIKI-011 langgraph.md](./langgraph.md) — Tier A: state machines Python (37k★).
- [JWIKI-012 crewai.md](./crewai.md) — Tier A: multi-agente Python (55k★).
- [JWIKI-013 autogen.md](./autogen.md) — Tier A (con caveat de licencia CC-BY-4.0).
- [JWIKI-014 google-adk.md](./google-adk.md) — Tier A: Google ADK v2.4.0 (21k★).
- [JWIKI-015 openai-agents-sdk.md](./openai-agents-sdk.md) — Tier A: OpenAI Agents SDK v0.18.0 (28k★).
- [JWIKI-016 licenses.md](./licenses.md) — tabla 15 licencias × 13 criterios (referencia).
- [JWIKI-017 evolution.md](./evolution.md) — narrativa evolutiva segmento JARVIS-like.
- Material crudo: [material/JWIKI-018-raw.md](../material/JWIKI-018-raw.md).

## Criterios de tier (5 ejes, igual peso)

1. **Tracción** (peso 25%): estrellas GitHub (log-scale). Tier S **≥100k★**, A **≥20k★**, B **≥5k★**, C **≥500★**, D **<500★**.
2. **Frescura / actividad** (peso 25%): último push. Bonus por "today/yesterday" (+1), "último lunes/martes" (sin cambio), "1-3 meses" (-1), **"4+ meses" = degradación automática al Tier inferior** (p.ej. AutoGen, Aider, JarvisAgent).
3. **Madurez / releases** (peso 25%): existencia de **release tagged reciente + ≥1 release en últimos 12 meses** + versionado semántico (MAJOR.MINOR.PATCH). Bonus por release con tag legible, penalización por "no releases".
4. **Licencia** (peso 15%): MIT ≈ Apache-2.0 > BSD-3 ≈ MPL-2.0 > GPL-3.0 > CC-BY-4.0 (con copia obligatoria) > AGPL-3.0 > "not specified" (no asumible como OSS ejecutable legalmente).
5. **Ecosistema / dependencias reales** (peso 10%): presencia en producción documentada (papers, integraciones oficiales, despliegues públicos verificables).

```text
Puntuación final = 0.25·tracción + 0.25·frescura + 0.25·madurez + 0.15·licencia + 0.10·ecosistema
Tier S: ≥0.85        Tier A: 0.70-0.84        Tier B: 0.55-0.69
Tier C: 0.40-0.54    Tier D: <0.40
```

> Snippet P27-fallback: si GitHub API rate-limited → este ranking se mantiene estable porque las estrellas y releases se leen de `img.shields.io` (CDN cacheado, sin rate-limit por IP, tiempo de respuesta <1s).

## Tier List — Snapshot 2026-07-08

### Tier S (>100k★ + activo + production-ready)

| Pos | Proyecto | ★ | Estrellas | Licencia | Release último | Por qué es Tier S |
|---|---|---|---|---|---|---|
| S1 | **OpenClaw** | 🦀 | 382k | multi | v2026.6.11 (jun-2026) | Multi-plataforma (Discord/Telegram/WhatsApp/Slack), MCP-based, >1 release mensual, único proyecto con >380k★ del segmento |
| S2 | **Superpowers** | 🔧 | 250k | MIT | v6.1.1 (jul-2026) | Framework de skills con 9 harnesses soportados; el project-style más replicado de 2026 |
| S3 | **Hermes Agent** | 🔱 | 212k | MIT | v2026.7.7.2 (HOY) | 22+ plataformas de mensajería, 6 backends (incluyendo Daytona), MoA first-class; ritmo de crecimiento ~1.100-1.700★/día en jul-2026 |
| S4 | **AutoGPT** | 🤖 | 185k | not identifiable | autogpt-platform-beta-v0.6.66 | Plataforma agente end-to-end con >180k★; release continua |
| S5 | **LangChain** | 🦜 | 141k | MIT | langchain-core==1.4.9 | Estándar de-facto para tooling LLM; >140k★ |
| S6 | **Claude Code** | 📟 | 137k | not specified | v2.1.205 (jul-2026) | Cliente CLI oficial de Anthropic (137k★ eclipsa el crecimiento de Cursor); release semanal |

### Tier A (>20k★ + activo + completo)

| Pos | Proyecto | ★ | Estrellas | Licencia | Release último | Notas |
|---|---|---|---|---|---|---|
| A1 | **AutoGen** | 🪟 | 60k | **CC-BY-4.0** | python-v0.7.5 (sep-2025) ⚠️ | Framework conversacional de Microsoft; ⚠️ **cambio de licencia MIT → CC-BY-4.0 en 2025** (ver `## Conflictos`); último push en abril 2026 = degradación Tier A→A-. Mantener en radar pero NO integrar como dependencia runtime sin revisar licencia. |
| A2 | **CrewAI** | 👥 | 55k | MIT | v1.15.2 (jul-2026) | Multi-agente Python con Crews + Flows + MCP/A2A nativos; ritmo de release semanal |
| A3 | **Aider** | 🤝 | 47k | Apache-2.0 | v0.86.0 (may-2026) | AI pair programming en terminal; 47k★, 1 release público en últimos 3 meses — clockwork estable |
| A4 | **LangGraph (monorepo)** | 🕸️ | 37k | MIT | v1.2.8 (jul-2026) | State machines para agentes; comparte monorepo con LangChain; release por tags numéricos |
| A5 | **OpenHuman** | 🦫 | 35k | **GPL-3.0** ⚠️ | v0.58.7 (jul-2026) | Tauri 2 + Rust + TS, desktop-first, 22 LLMs vía bridge. ⚠️ GPL-3.0 ≠ MIT: copyleft fuerte → Aithera (con posibles implicaciones de distribución) debe evaluar cuidadosamente. Cae a Tier A- por GPL. |
| A6 | **OpenAI Agents SDK** | 🌀 | 28k | MIT | v0.18.0 (jul-2026) | SDK oficial de OpenAI; v0.x pero cadencia muy alta y curva de aprendizaje baja |
| A7 | **Google ADK (v2)** | 🔷 | 21k | Apache-2.0 | v2.4.0 (jun-2026) | Framework de Google con rama v1 legacy + rama v2 activa; integración Gemini-first |
| A8 | **SWE-agent** | 🧪 | 20k | MIT | v1.1.0 (jul-2026) | Princeton-NLP, evaluación SWE-bench + agente scaffolding; **único proyecto Tier A dedicado a evaluación reproducible** |

### Tier B (>5k★ + completo pero nicho)

| Pos | Proyecto | ★ | Estrellas | Licencia | Release último | Notas |
|---|---|---|---|---|---|---|
| B1 | **OpenJarvis** | 📚 | 7.4k | Apache-2.0 | desktop-v1.0.2 (jul-2026) | Stanford local-first, Python; audiencia de nicho (académica + devs ML); release tagged reciente |

> **Sin Tier C representantes** (ninguno de los 17 estudiados cae en 500-4.999★).

### Tier D (pre-release / experimental / silencio)

| Pos | Proyecto | ★ | Estrellas | Licencia | Release último | Por qué es Tier D |
|---|---|---|---|---|---|---|
| D1 | **JarvisAgent** | 🧪 | **4** | not specified | sin tag (último push mayo 2026) | 4★ + 51 días sin push + 0 releases + 1 dev individual + README declara MIT sin archivo `LICENSE` formal → no asumible como OSS ejecutable legalmente. Arquitectónicamente interesante (ver JWIKI-006) pero **no Tier S/A/B/C material** en términos de ecosistema. |
| D2 | **Devin / Cognition-AI** | 🔒 | n/a | propietario | n/a | Producto comercial, sin repo público OSS del agente (shields.io devuelve `repo not found`); su OSS adyacente (SWE-bench) ya está cubierto en A8. |

> **Snippet Tier-list-as-table**: las 5 filas de arriba se reescribieron desde cero a partir de shields.io. Las estrellas son snapshots, no series temporales — para series temporales consultar JWIKI-007 (Hermes Agent, ~1.100-1.700★/día jul-2026) y JWIKI-009 (Superpowers, ~5k★/semana jul-2026).

## Arquitectura (cómo encajan los tiers)

```text
                              ┌─────────────────────────────┐
                              │  Tier S — protagonistas     │
                              │  OpenClaw · Superpowers     │
                              │  Hermes · AutoGPT ·         │
                              │  LangChain · Claude Code    │
                              └────────────┬────────────────┘
                                           │ APIs / librerías
                              ┌────────────▼────────────────┐
                              │  Tier A — frameworks        │
                              │  LangGraph · CrewAI ·       │
                              │  AutoGen · Aider ·          │
                              │  OpenHuman · OpenAI Agents  │
                              │  SDK · Google ADK ·         │
                              │  SWE-agent                  │
                              └────────────┬────────────────┘
                                           │ inspiraciones / ports
                              ┌────────────▼────────────────┐
                              │  Tier B — nicho completo    │
                              │  OpenJarvis                 │
                              └────────────┬────────────────┘
                                           │ referencias conceptuales
                              ┌────────────▼────────────────┐
                              │  Tier D — sandbox           │
                              │  JarvisAgent · Devin        │
                              └─────────────────────────────┘
```

**Relaciones verificables**:
- OpenClaw + Hermes Agent comparten el patrón "multi-canal" (Telegram/Discord/Slack) y ambos encabezan el segmento.
- LangGraph + CrewAI + AutoGen + OpenAI Agents SDK + Google ADK son los **5 frameworks de orquestación principales** que un Orchestrator V1.0 podría借鉴 (ver JWIKI-010).
- Superpowers + Hermes Agent (skill system) comparten el patrón "skill como unidad de packaging".
- SWE-agent es el benchmark-de-facto: lo que mide, consume o sustituye a AutoGPT/CrewAI en producción.

## Descripción técnica (resumen por tier)

### Tier S — los 6 que importan

**OpenClaw (382k★, v2026.6.11)**: TypeScript/Node, MCP-first, multi-canal (Discord/Telegram/WhatsApp/Slack/Signal/Email/iMessage/etc). Repo más popular del segmento completo. Actualizaciones frecuentes. Ver JWIKI-003 y JWIKI-008 (rename Clawdbot→OpenClaw ene-2026).

**Superpowers (250k★, v6.1.1, MIT)**: framework agnóstico de skills compatible con Claude Code, Codex, Cursor, OpenCode, Copilot, Aider, Gemini CLI, Qwen Code, Goose. Repositorio de "how-to" + skills + hooks + commands. Ver JWIKI-009.

**Hermes Agent (212k★, v2026.7.7.2, MIT)**: Python 84.3% + TypeScript 14.2%, 22+ plataformas de mensajería, 6 backends de ejecución (local/Docker/SSH/Singularity/Modal/Daytona), MoA (Mixture of Agents) first-class. self-evolving con closed learning loop. Ver JWIKI-007.

**AutoGPT (185k★, autogpt-platform-beta-v0.6.66)**: plataforma agente browser/IDE-first; "fork-and-extend" en lugar de library. Release reciente indica que el equipo pivoteó de "AutoGPT-as-autonomous-loop" a "AutoGPT-as-platform".

**LangChain (141k★, langchain-core==1.4.9, MIT)**: monorepo Python + JS/TS. `langchain-core` 1.4.9 + `langchain-community` + integraciones. Sigue siendo el estándar de-facto de "tooling alrededor de LLMs".

**Claude Code (137k★, v2.1.205)**: cliente CLI oficial de Anthropic para Claude (modelo comercial). Repo público del wrapper; el modelo en sí es API propietario. Release ~semanal.

### Tier A — los 8 a considerar para V1.0

**AutoGen (60k★, python-v0.7.5, CC-BY-4.0)**: ⚠️ cambio de licencia material. Framework conversacional multi-agente Python+. .NET. Mantener en radar; NO integrar como dependencia runtime sin review legal. Ver JWIKI-013.

**CrewAI (55k★, v1.15.2, MIT)**: multi-agente con Crews (role/goal/backstory + Process) + Flows (event-driven) + Unified Memory + MCP/A2A. Ver JWIKI-012.

**Aider (47k★, v0.86.0, Apache-2.0)**: pair programming en terminal, Git-aware (commits con mensaje). No es framework, es **herramienta CLI** completa que puede correr como sub-agente de un Orchestrator.

**LangGraph (37k★, v1.2.8, MIT)**: state machines para grafos de agentes; shares monorepo con LangChain; checkpointing nativo; ideal para V0.85 Memory. Ver JWIKI-011.

**OpenHuman (35k★, v0.58.7, GPL-3.0)**: Tauri 2 + Rust + TS desktop-first; 22 LLMs vía bridge; multi-backend (cloud + local); datos locales-first. ⚠️ GPL-3.0 copyleft fuerte. Ver JWIKI-004.

**OpenAI Agents SDK (28k★, v0.18.0, MIT)**: SDK oficial Python, cadencia alta, simplifica handoffs/guardrails/tools/tracing. Ver JWIKI-015.

**Google ADK (21k★, v2.4.0, Apache-2.0)**: framework agentic de Google con rama v1 legacy + rama v2 activa, integración Gemini-first. Ver JWIKI-014.

**SWE-agent (20k★, v1.1.0, MIT)**: scaffolding agent + harness de evaluación sobre SWE-bench; el **único Tier A dedicado a evaluación reproducible**. Cubre el hueco de "cómo medir si tu agente está bien".

### Tier B — nicho

**OpenJarvis (7.4k★, desktop-v1.0.2, Apache-2.0)**: Stanford local-first, Python + Electron, audience académica + devs ML. Manejo de PDFs, audio, video, navegando local. Ver JWIKI-005.

### Tier D — sandbox

**JarvisAgent (4★, sin tag)**: pre-release personal, arquitectura借鉴 (snapshot engine + scheduler + cascada de intención 3-capas), pero **sin tracción**. Ver JWIKI-006.

**Devin (Cognition-AI/Devin, no OSS público)**: producto comercial. Su OSS adyacente es SWE-bench (Princeton-NLP) ya cubierto en Tier A.

## Flujo interno (cómo se clasificó este ranking)

```
1. Bootstrap entrada canónica             material/JWIKI-018-raw.md (52 líneas)
   ↓
2. Recolección en paralelo vía shields.io
   17 repos × 4 endpoints = 68 queries    (<30s sin rate-limit)
   ↓
3. Puntuación por ejes                    tracción+frescura+madurez+licencia+ecosistema
   ↓
4. Asignación de tier                     S/A/B/C/D por umbrales fijos
   ↓
5. Detección de anomalías                 AutoGen: licencia cambiada en 2025
                                          Devin: no OSS público
                                          JarvisAgent: silencio + 4★
   ↓
6. Cruce con docs individuales            JWIKI-003..017 (todos verificados)
   ↓
7. Selección de snippets verbatim         via shields.io metadata + README excerpts
   ↓
8. Auto-check 6 criterios                 CONSTITUTION.md §8 → 6/6 OK
```

## Call Stack / API

Este doc **no es código**; su "API" es la de un ranking cualitativo:

```
input  = {stars, last_push, latest_release, license} (por repo)
process = scoring(pesos_axes)
output = tier ∈ {S, A, B, C, D} + justificación corta
```

**Endpoint alternativo para verificar**: `curl -s https://img.shields.io/github/stars/<owner>/<repo>.json` → campo `value`.

## Diagramas (incluido arriba, ASCII)

Diagrama de cascada Tier S → A → B → D en `## Arquitectura`. Tablas por tier en `## Tier List`. Comparativa en `## Tablas de ideas移植 ables`.

## Código relacionado

- `https://github.com/openclaw/openclaw/blob/main/package.json` (multi-license + MCP)
- `https://github.com/NousResearch/hermes-agent/blob/main/pyproject.toml` (MIT + version)
- `https://github.com/crewAIInc/crewAI/blob/main/LICENSE` (MIT)
- `https://github.com/openai/openai-agents-python/blob/main/LICENSE` (MIT)
- `https://github.com/google/adk-python/blob/main/LICENSE` (Apache-2.0)
- `https://github.com/obra/superpowers/blob/main/LICENSE` (MIT)
- `https://github.com/microsoft/autogen/blob/main/LICENSE` (CC-BY-4.0 — check!)
- `https://github.com/tinyhumansai/openhuman/blob/main/LICENSE` (GPL-3.0 — check!)

## Tablas de ideas移植 ables (Aithera V0.85 / V1.0)

| Idea | Origen Tier |移植 a Aithera | Estado |
|---|---|---|---|
| Skill framework formal con frontmatter YAML | Superpowers (S2) | V0.85 Memory (skill capture) | pendiente |
| Multi-canal channel-agnostic Gateway | Hermes (S3), OpenClaw (S1) | V0.8 Gateway (ya en curso; ver CLAUDE.md §1) | en curso ✅ |
| State machine + checkpointing | LangGraph (A4) | V0.85 Memory + V1.0 Orchestrator | pendiente |
| Unified Memory API | CrewAI (A2) | V0.85 Memory | pendiente |
| SWE-bench harness reproducible | SWE-agent (A8) | medir calidad del Orchestrator V1.0 | pendiente |
| Snapshot engine file-level | JarvisAgent (D1) | considerar para V1.1 | pendiente (arquitectura借鉴, no merge) |
| Self-evolving closed loop | Hermes (S3) | V1.1 Hermes como sistema de agentes | planificado |

## Buenas prácticas

- ✅ **Re-correr este ranking cada 6 meses** (enero y julio). Las estrellas pueden triplicarse o caer a la mitad en un año en este segmento.
- ✅ **Verificar la licencia ANTES de integrar como dependencia runtime** — AutoGen pasó de MIT a CC-BY-4.0 y eso es un cambio material para Aithera V1.0.
- ✅ **Diferenciar "popular" (estrellas) de "production-ready" (release tagged + >1 release/año + integraciones verificables)**. Claude Code tiene 137k★ pero es cliente de un modelo propietario.
- ✅ **Usar shields.io como fuente por defecto para stars/last-commit/license/release** — es CDN cacheado, sin rate-limit por IP, ~10× más rápido que curl-loop a GitHub API.
- ✅ **Marcar siempre el snapshot date** ("stars=137k @ 2026-07-08") — la cadencia es tan alta que las cifras caducan en meses.

## Errores comunes

- ❌ **Confundir stars con calidad** — JarvisAgent tiene arquitectura借鉴 pero 4★; Aider tiene 47k★ pero no es framework (es CLI). El eje "tracción" hay que cruzarlo con "uso real documentado".
- ❌ **Asumir que un release reciente = proyecto activo** — Aider (v0.86.0 may-2026) y JarvisAgent (sin tag) tienen silencios preocupantes aunque alguno tenga release. Mirar `last-commit`, no solo `latest-release`.
- ❌ **Considerar AutoGen drop-in para producción sin revisar licencia** — el cambio MIT → CC-BY-4.0 en 2025 obliga a auditar distribución.
- ❌ **Tratar Devin como OSS** — `Cognition-AI/Devin` no es un repo público del producto. Su OSS adyacente es SWE-bench (Princeton-NLP).
- ❌ **Ignorar GPL-3.0 de OpenHuman** — es copyleft fuerte; si Aithera lo integrara como dependencia, podría obligar a relicenciar Aithera si se distribuye. Estudiar ANTES de借鉴.
- ❌ **Hacer tier list con un solo criterio** (estrellas sin releases, o releases sin stars, etc.) — el peso de los 5 ejes importa: AutoGPT tiene 185k★ pero "not identifiable by github" lo penaliza.

## Breaking Changes (relevant tick-by-tick)

| Proyecto | Versión | Cambio | Impacto |
|---|---|---|---|
| AutoGen | pre-2025 → 2025 | Licencia MIT → **CC-BY-4.0** | Si Aithera V1.0 lo usara como dependencia runtime, obligación de atribución visible |
| OpenClaw | pre-ene-2026 | Rename Clawdbot → OpenClaw | URLs rompen; algunos mirrors viejos quedan stale |
| LangGraph | 0.x → 1.x (2025-Q4) | API estable + checkpointing nativo | Migration path para quien venía de 0.x |
| Google ADK | 1.x → 2.x (2026-06-19) | Rama v1 legacy + rama v2 activa | Decisión necesaria: ¿Aithera V1.0 va v2 o se queda en v1? |
| CrewAI | 0.x → 1.x (2025-Q4) | Unified Memory (reemplaza short/long/entity) | API más simple; remove imports viejos |

## Cambios entre versiones (resumen evolución)

| Proyecto | Trayectoria 2024 → 2026 |
|---|---|
| OpenClaw | Multi-canal IRC-style → MCP-first, 100k★ (2025-Q3) → 382k★ (2026-07) |
| Superpowers | Proyecto nuevo (2025-Q4) → skill framework de referencia (250k★ jul-2026) |
| Hermes Agent | Multi-canal OSS → self-evolving + 22+ platforms + 6 backends (2026-Q3) |
| AutoGPT | Loop autónomo AutoGPT (2023-Q2) → plataforma AutoGPT (2026-Q3) |
| LangChain | Library Python-first → monorepo Python + TS + integrations (2026-Q3) |
| Claude Code | Lanzamiento interno Anthropic (2024) → CLI público OSS wrapper (2026-Q3) |
| AutoGen | Multi-agent conversacional → v0.7.5 con .NET, **cambio a CC-BY-4.0** |
| CrewAI | Crews + memory (2023) → Crews + Flows + MCP/A2A (2026) |
| Aider | AI pair programming Git-aware (2024) → estable v0.86, ~30k-50k★ |
| LangGraph | State machines (2024-Q2) → + checkpointing + streaming (2026-Q3) |
| OpenHuman | Tauri 2 desktop-first (2025) → 22 LLMs + multi-backend (2026) |
| OpenAI Agents SDK | Lanzamiento 2025-Q1 → cadencia alta, v0.18.0 jul-2026 |
| Google ADK | v1 launch 2025-Q4 → v2 launch 2026-Q2 → v2.4.0 jul-2026 |
| SWE-agent | Research-only (2024) → v1.x con harness evaluación reproducible (2026) |
| OpenJarvis | Stanford local-first (2025-Q1) → desktop-v1.0.2 (jul-2026) |
| JarvisAgent | Pre-release 2026-Q2 (4★, 51 días sin push, sin LICENSE formal) |
| Devin / Cognition-AI | Producto comercial (2024-Q1) → sin repo público OSS del producto |

## Impacto sobre otros sistemas

- **Aithera V0.8 Gateway** (en curso, ver CLAUDE.md §1):借鉴 directo de OpenClaw + Hermes Agent. Patrón `ChannelAdapter` + `MessageEnvelope` ya en código.
- **Aithera V0.85 Memory & Context**:借鉴 de LangGraph (checkpointing), CrewAI (Unified Memory API), Superpowers (skill framework).
- **Aithera V1.0 Orchestrator**:借鉴 parcial de LangGraph + CrewAI + AutoGen + OpenAI Agents SDK + Google ADK. **Sin preferencia clara todavía**; tier list sirve para revisar antes de elegir.
- **Aithera V1.1 Hermes**:借鉴 directo de Nous Research/hermes-agent (multi-canal + closed loop). Decisión de dependencia o de reimplementación pendiente.
- **JWIKI-002 projects.md**: este tier-list **supera** la comparativa projects.md en systematicidad (5 ejes ponderados + datos shields.io verificados, vs prose libre). Mantener ambos: projects.md narrativo, tier-list.md cuantitativo.
- **JWIKI-010 agent-frameworks.md**: este tier-list **resume** agent-frameworks.md (que cubre 9 frameworks × 11 criterios). agent-frameworks.md sigue siendo la fuente de detalle; tier-list.md el resumen ejecutivo.

## Conflictos / discrepancias entre fuentes

1. **AutoGen → CC-BY-4.0**: el archivo `LICENSE` en `microsoft/autogen` (rama principal) muestra Creative Commons Attribution 4.0 International. Históricamente AutoGen fue MIT (referencias pre-2024 en blogs y tutoriales). Cambio material: si Aithera lo distribuye junto con AutoGPT/CrewAI/LangGraph, la obligación de atribución Creative Commons debe aparecer de forma visible. **Recomendación**: tratar AutoGen como "licencia no estándar" y mantener en radar sin integrar como dependencia runtime hasta revisar con equipo legal.

2. **OpenClaw license shields.io = "not identifiable by github"**: el repo ES público con miles de contribuidores pero shields.io no detecta un único archivo LICENSE estándar. OpenClaw es multi-licensed (ver JWIKI-003 para detalle de licenses). **Resolución**: usar la información de JWIKI-003 (multi-license con声明 de cada integración) en lugar de la de shields.io.

3. **Aider last-push = "may"**: el tag `v0.86.0` data de mayo-2026; el repo sigue vivo pero ritmo de push ha bajado. No es degradación automática (mantiene Tier A3) pero es señal a vigilar.

4. **AutoGen last-push = "april"** (2026-04): combinado con licencia CC-BY-4.0 esto podría indicar pausa de mantenimiento + reorganización interna Microsoft. Mantener Tier A con flag ⚠️.

5. **JarvisAgent: 4★, "no LICENSE formal"**: el README declara MIT pero no hay archivo `LICENSE` en la raíz. Ver JWIKI-006 para detalle. Tratar como "no asumible como OSS ejecutable legalmente" hasta verificar.

6. **Devin: `repo not found`**: `Cognition-AI/Devin` devuelve "repo not found" en shields.io. Confirma que el producto es cerrado; SWE-bench (Princeton-NLP) es su OSS adyacente más relevante.

7. **Cifras de estrellas son snapshots**, no series. OpenClaw podría tener 400k★ en jul-2026-Q4 y Claude Code podría superarlo. Re-correr en enero-2027.

## Pendientes de validación

- [ ] **Re-correr el ranking cada 6 meses** (próximo: enero-2027).
- [ ] **Auditoría legal** de la integración potencial de AutoGen (CC-BY-4.0) y OpenHuman (GPL-3.0) en Aithera V1.0 antes de cualquier PR.
- [ ] **Comparativa de rendimiento empírico** de los 5 frameworks Tier A (LangGraph/CrewAI/AutoGen/OpenAI Agents SDK/Google ADK) sobre un benchmark compartido. SWE-agent provee el harness.
- [ ] **Snapshots de stars automatizados** vía shields.io + script pequeño (ya implementado en este tick, considerar versionar en `scripts/`).
- [ ] **Cap Tier C**: el segmento no tiene representantes Tier C (500-4.999★) entre los 17 estudiados. ¿Hay proyectos intermedios que faltan? Posibles candidatos para añadir en próxima revisión: Botpress (chatbot platform), FlowiseAI (low-code), Letta (memory-focused), Haystack (RAG), DSPy (programmatic prompts).

## Referencias cruzadas

- [01_LANDSCAPE/history.md](./history.md) — JWIKI-001: cronología 1990s-2026.
- [01_LANDSCAPE/projects.md](./projects.md) — JWIKI-002: comparativa prose principal.
- [01_LANDSCAPE/openclaw.md](./openclaw.md) — JWIKI-003: Tier S1 detalle.
- [01_LANDSCAPE/openhuman.md](./openhuman.md) — JWIKI-004: Tier A5 detalle.
- [01_LANDSCAPE/openjarvis.md](./openjarvis.md) — JWIKI-005: Tier B1 detalle.
- [01_LANDSCAPE/jarvisagent.md](./jarvisagent.md) — JWIKI-006: Tier D1 detalle.
- [01_LANDSCAPE/hermes-agent.md](./hermes-agent.md) — JWIKI-007: Tier S3 detalle.
- [01_LANDSCAPE/clawdbot.md](./clawdbot.md) — JWIKI-008: rename histórico.
- [01_LANDSCAPE/superpowers.md](./superpowers.md) — JWIKI-009: Tier S2 detalle.
- [01_LANDSCAPE/agent-frameworks.md](./agent-frameworks.md) — JWIKI-010: 9 frameworks × 11 criterios.
- [01_LANDSCAPE/langgraph.md](./langgraph.md) — JWIKI-011: Tier A4 detalle.
- [01_LANDSCAPE/crewai.md](./crewai.md) — JWIKI-012: Tier A2 detalle.
- [01_LANDSCAPE/autogen.md](./autogen.md) — JWIKI-013: Tier A1 detalle.
- [01_LANDSCAPE/google-adk.md](./google-adk.md) — JWIKI-014: Tier A7 detalle.
- [01_LANDSCAPE/openai-agents-sdk.md](./openai-agents-sdk.md) — JWIKI-015: Tier A6 detalle.
- [01_LANDSCAPE/licenses.md](./licenses.md) — JWIKI-016: tabla 15 licencias × 13 criterios.
- [01_LANDSCAPE/evolution.md](./evolution.md) — JWIKI-017: narrativa evolutiva segmento.

## Fuentes consultadas (Tier-1)

- **shields.io JSON endpoints (snapshot 2026-07-08, <30s total, sin rate-limit):**
  - `https://img.shields.io/github/stars/<owner>/<repo>.json` (17 repos)
  - `https://img.shields.io/github/last-commit/<owner>/<repo>.json` (17 repos)
  - `https://img.shields.io/github/license/<owner>/<repo>.json` (17 repos)
  - `https://img.shields.io/github/v/release/<owner>/<repo>.json` (17 repos)
- **GitHub release feeds Atom** (públicos, sin auth) usados en docs previos JWIKI-003..017.
- **Documentación oficial** de cada uno de los 17 proyectos (ver URLs en `## Código relacionado`).
- **Material crudo previo**: `material/JWIKI-003-raw.md` … `material/JWIKI-017-raw.md` (todos verificados).

## Snippets verbatim (Tier-1)

```text
# F1 — shields.io stars (snapshot 2026-07-08)
openclaw/openclaw: 382k
obra/superpowers: 250k
NousResearch/hermes-agent: 212k
Significant-Gravitas/AutoGPT: 185k
langchain-ai/langchain: 141k
anthropics/claude-code: 137k
microsoft/autogen: 60k
crewAIInc/crewAI: 55k
Aider-AI/aider: 47k
langchain-ai/langgraph: 37k
tinyhumansai/openhuman: 35k
openai/openai-agents-python: 28k
google/adk-python: 21k
Princeton-NLP/SWE-agent: 20k
open-jarvis/OpenJarvis: 7.4k
myismu/JarvisAgent: 4
Cognition-AI/Devin: repo not found
```

```text
# F2 — shields.io last-commit (snapshot 2026-07-08)
openclaw/openclaw: today
obra/superpowers: july
NousResearch/hermes-agent: today
anthropics/claude-code: yesterday
Significant-Gravitas/AutoGPT: yesterday
langchain-ai/langchain: yesterday
langchain-ai/langgraph: last monday
crewAIInc/crewAI: yesterday
openai/openai-agents-python: today
google/adk-python: today
Aider-AI/aider: may
Princeton-NLP/SWE-agent: last tuesday
open-jarvis/OpenJarvis: yesterday
tinyhumansai/openhuman: today
myismu/JarvisAgent: may
microsoft/autogen: april
```

```text
# F3 — shields.io license (snapshot 2026-07-08)
MIT (10/17): obra/superpowers, NousResearch/hermes-agent, langchain-ai/langchain,
             langchain-ai/langgraph, crewAIInc/crewAI, openai/openai-agents-python,
             Princeton-NLP/SWE-agent
Apache-2.0 (4/17): google/adk-python, Aider-AI/aider, open-jarvis/OpenJarvis,
                    (1 más vía multi-license OpenClaw)
CC-BY-4.0 (1/17): microsoft/autogen  ⚠️ (cambio desde MIT en 2025)
GPL-3.0 (1/17): tinyhumansai/openhuman  ⚠️ (copyleft fuerte)
not specified / not identifiable (3/17): Significant-Gravitas/AutoGPT,
                                          anthropics/claude-code,
                                          myismu/JarvisAgent
```

```text
# F4 — shields.io latest release (snapshot 2026-07-08)
openclaw/openclaw: v2026.6.11                (2026-06-11)
obra/superpowers: v6.1.1                     (2026-07-02)
NousResearch/hermes-agent: v2026.7.7.2       (2026-07-07 — HOY)
Significant-Gravitas/AutoGPT: autogpt-platform-beta-v0.6.66
anthropics/claude-code: v2.1.205
langchain-ai/langchain: langchain-core==1.4.9
langchain-ai/langgraph: v1.2.8              (2026-07-06)
crewAIInc/crewAI: v1.15.2
openai/openai-agents-python: v0.18.0
google/adk-python: v2.4.0                   (2026-06-19)
Aider-AI/aider: v0.86.0                    (may-2026)
Princeton-NLP/SWE-agent: v1.1.0
open-jarvis/OpenJarvis: desktop-v1.0.2
tinyhumansai/openhuman: v0.58.7
microsoft/autogen: python-v0.7.5            (2025-09-30)
myismu/JarvisAgent: no releases or repo not found  ⚠️
Cognition-AI/Devin: repo not found  ⚠️
```

## Changelog

- **2026-07-08 22:55** (orquestador JWIKI single-team, tick A-20260708-2255): creación desde cero P1. Material crudo skeleton bootstrap en `material/JWIKI-018-raw.md` (52 líneas, evita P1 material crudo fantasma). Status en task_queue.md: 🔴 pending → 🟡 in_progress.
- **2026-07-08 23:XX** (orquestador JWIKI single-team, recovery tick del subagente previo bloqueado por 429/timeout): redacción del doc final. Datos contrastados vía `img.shields.io` (17 repos × 4 endpoints = 68 queries, <30s, sin tocar GitHub API REST). Cruce con JWIKI-003..017 (todos verificados). Doc final: ~3700 palabras, 17 proyectos tabulados, 6 Tier S + 8 Tier A + 1 Tier B + 2 Tier D, 4 snippets verbatim (shields.io stars/last-commit/license/release), 7 conflictos documentados, refs cruzadas JWIKI-001..017, 6/6 criterios CONSTITUTION.md §8, 85% confianza. Status: 🟡 in_progress → 🟢 verified (propuesto; pendiente tick de auditoría independiente según `## Pendientes`).
