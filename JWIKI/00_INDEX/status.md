# STATUS — Estado actual de la JWIKI

> Snapshot del estado de la knowledge base. Se actualiza al cerrar cada fase o tick importante.
## Última actualización: 2026-07-08 21:XX (JWIKI-016 Licencias comparativa generado y verificado, 6302 palabras — single-team tick A-20260708-21XX, production-tick desde cero P1; contraste GitHub API live 2026-07-08 11 proyectos + raw GitHub LICENSE files + SPDX license-list-data + choosealicense.com como Tier-1 independientes; 23 secciones TEMPLATE.md, 16 fenced code blocks, 12 snippets verbatim de LICENSE files reales, tabla 15 licencias × 13 criterios, tabla 11 proyectos OSS con 5 conflictos resueltos, 62 fuentes URL+fecha, 88% confianza)

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Dominios totales | 17 |
| Dominios con esqueleto | 17 |
| **Total docs PLANIFICADOS** | **267** |
| **Documentos verificados** | **14** (JWIKI-001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012 ✅, 013, 014 verificado 2026-07-08 20:38, 015 verificado 2026-07-08 20:55, **016 verificado 2026-07-08 21:XX**) |
| En auditoría | 0 |
| Avance total | 14/267 = **5.24%** |
| Wiki-map | ✅ Activo (267 IDs, 14 verificados a 2026-07-08 21:XX) |
| Task queue | ✅ Activo (single-team desde 2026-06-30 19:15, sin turno A/B) |
| Equipo wiki | ✅ 6 agentes (3 turno A + 3 turno B) |
| Equipo Aithera | ✅ 8 agentes especialistas |
| Crons | ✅ 4 configurados y activos |

## Estado por fase (de ROADMAP.md)

| Fase | Descripción | Estado | Avance |
|---|---|---|---|
| 0 | Bootstrap | 🟢 Completa | 100% |
| 1 | Landscape + AI Providers | 🔴 Pendiente | 0% |
| 2 | Backend + Frontend | 🔴 Pendiente | 0% |
| 3 | Agentes + Memory | 🔴 Pendiente | 0% |
| 4 | Voice + Integrations | 🔴 Pendiente | 0% |
| 5 | Automation + Security | 🔴 Pendiente | 0% |
| 6 | Tooling + Deployment | 🔴 Pendiente | 0% |
| 7 | Best Practices + Known Pitfalls | 🔴 Pendiente | 0% |
| 8 | SOPs + Mantenimiento | 🔴 Pendiente | 0% |

## Inventario por dominio

| Dominio | Total docs PLANIFICADOS | Done | Avance |
|---|---|---|---|
| 00_INDEX/ | 8 | 8 | **100%** ✅ |
| 01_LANDSCAPE/ | 18 | 7 | **38.89%** |
| 02_ARCHITECTURE/ | 12 | 0 | 0% |
| 03_BACKEND/ | 22 | 0 | 0% |
| 04_FRONTEND/ | 22 | 0 | 0% |
| 05_AI_PROVIDERS/ | 26 | 0 | 0% |
| 06_AGENTS/ | 18 | 0 | 0% |
| 07_MEMORY/ | 16 | 0 | 0% |
| 08_VOICE/ | 16 | 0 | 0% |
| 09_INTEGRATIONS/ | 18 | 0 | 0% |
| 10_AUTOMATION/ | 10 | 0 | 0% |
| 11_SECURITY/ | 12 | 0 | 0% |
| 12_TOOLING/ | 12 | 0 | 0% |
| 13_DEPLOYMENT/ | 14 | 0 | 0% |
| 14_BEST_PRACTICES/ | 12 | 0 | 0% |
| 15_KNOWN_PITFALLS/ | 14 | 0 | 0% |
| 16_SOPS/ | 24 | 0 | 0% |
| **TOTAL** | **266** | **0** | **0.00%** |

## Sistema wiki-map (activo desde tick 0)

- ✅ `JWIKI/00_INDEX/wiki-map.md` creado y activo desde el bootstrap.
- ✅ 266 IDs planificados (JWIKI-001 a JWIKI-266) con asignación de turno A/B.
- ✅ Será mantenido por Mavis cada 5-10 ticks (similar a OTKB).
- ✅ Cada agente `aithera-wiki-*` debe leerlo antes de empezar trabajo.

## Crons configurados (4 — **24/7**)

- ✅ `jwiki-tick-a` — cada 15 min (turno A, IDs pares) **24/7**
- ✅ `jwiki-tick-b` — cada 15 min (turno B, IDs impares) **24/7**
- ✅ `skill-evolve` — cada 3 días a las 10:00 (mejora skills) **24/7**
- ✅ `skill-discover` — cada lunes a las 09:00 (descubrir nuevas skills) **24/7**

## Equipo creado (14 agentes)

**Wiki team (6)**:
- `aithera-wiki-investigador` (turno A)
- `aithera-wiki-escriba` (turno A)
- `aithera-wiki-auditor` (turno A)
- `aithera-wiki-inv2` (turno B)
- `aithera-wiki-scr2` (turno B)
- `aithera-wiki-aud2` (turno B)

**Aithera team (8)**:
- `aithera-backend`, `aithera-frontend`, `aithera-ia`, `aithera-agentes`
- `aithera-memoria`, `aithera-voz`, `aithera-integ`, `aithera-devops`

## Próximos puntos en cola (task_queue.md)

Ver `task_queue.md` (vacío, se llenará cuando arranque Fase 1).

## Hitos recientes

- **Tick 0 (2026-06-30 00:25)**: Bootstrap completo. Estructura 17 dominios creada, constitución + roadmap + workflow + wiki-map + equipo `aithera-wiki-*` en proceso.
- **Tick A-20260708-21XX (2026-07-08 21:XX)**: JWIKI-016 Licencias comparativa generado desde cero (P1). 11 proyectos OSS verificados GitHub API live 2026-07-08 (OpenClaw MIT 382k★ con API NOASSERTION por regex copyright, OpenHuman GPL-3.0 34k★, OpenJarvis Apache 2.0 7k★, Hermes MIT 211k★, Superpowers MIT 249k★, AutoGen dual MIT+CC-BY-4.0 60k★, LangGraph MIT 36k★, CrewAI MIT 55k★, Google ADK Apache 2.0 20k★, OpenAI Agents SDK MIT 27k★, JarvisAgent MIT declarado en README con LICENSE file null). 5 conflictos entre fuentes resueltos (OpenClaw NOASSERTION vs MIT file, AutoGen dual MIT/CC-BY-4.0, JarvisAgent LICENSE file null, AutoGen pushed_at stale abril 2026, GitHub API NOASSERTION vs Other). 12 snippets verbatim de LICENSE files reales con path:line. Tabla 15 licencias OSS × 13 criterios (MIT, Apache-2.0, BSD-2/3, ISC, Unlicense, CC0-1.0, GPL-2.0, GPL-3.0, LGPL-2.1, LGPL-3.0, AGPL-3.0, MPL-2.0, EPL-2.0, BSL-1.1). 5 riesgos legales comunes (GPL contamination, AGPL en SaaS, BSD vs Apache patent grant, GPL-2.0 vs 3.0, MIT sin LICENSE file). Casos prácticos Aithera: core→MIT/Apache-2.0, datasets→CC0-1.0, skills→MPL-2.0, trading→BSL-1.1. 6302 palabras, 23 secciones TEMPLATE, 16 fenced code blocks, 62 fuentes Tier-1 con URL+fecha, 88% confianza, 6/6 criterios CONSTITUTION §8. Avance 14/267 = 5.24%.
- **Tick A-20260708-2008 (2026-07-08 20:08)**: JWIKI-006 JarvisAgent verificado. Doc enriquecido de 2080 → 5632 palabras (+170 %). 11 snippets, 32 hechos, comparativa OSS contrastada live. Avance 10/267 = 3.75%.
- **Tick A-20260708-2020 (2026-07-08 20:20)**: JWIKI-012 CrewAI overview generado desde cero (P1). GitHub API live confirmó **55.157★** (task_queue decía ~30k, +84% stale), **v1.15.2** publicada ese día, MIT, Python 99.7%, monorepo UV con 6 paquetes `lib/`, **Unified Memory** v1.x (reemplaza short/long/entity de 0.x), **MCP+A2A nativos** (refuta claim de JWIKI-013). 3492 palabras, 26 secciones, 14 snippets, 10 refs path:line, tabla comparativa 5 frameworks, 55 hechos. 88% confianza. Avance 11/267 = 4.12%.
- **Tick A-20260708-2032 (2026-07-08 20:38)**: **JWIKI-014 Google ADK overview RECOVERY+COMPLETION**. Subagente previo dejó research al 70% sin persistir. Branch `main` @ v2.4.0 contrastado vía raw source 2026-07-08 (GitHub API rate-limited; contraste vía shields.io + raw). Hallazgos clave: (1) `__version__="2.4.0"` confirmado en `version.py:16`, no MIT (mito frecuente) sino **Apache 2.0** verificado triple (badge + pyproject classifier + license file); (2) 5 SDKs oficiales (`adk-python/-js/-go/-java/-kotlin`); (3) **Workflow Runtime 2.0** con `Workflow(BaseNode) + DynamicNodeScheduler + ReplayManager + ReplaySequenceBarrier` (replay determinístico); (4) **interop deliberada** — `extensions` extras incluye `langgraph>=0.2.60`, `crewai[tools]`, `litellm>=1.84`, `anthropic>=0.78` (Claude Opus 4.7), `openai>=2.20`, `llama-index`, `toolbox-adk`; (5) **A2A nativo** (`a2a-sdk>=0.3.4`) refuta JWIKI-013 "solo CrewAI"; (6) **MCP nativo** (`mcp>=1.24`); (7) `mode='chat'/'task'/'single_turn'` es novedad 2.0 para delegación; (8) `DEFAULT_MODEL='gemini-3.5-flash'` y `DEFAULT_LIVE_MODEL='gemini-live-2.5-flash-native-audio'`. 5307 palabras, 22 secciones TEMPLATE, 53 hechos verificados, 35 path:line refs, 7 snippets con `path:line`, tabla comparativa 6 frameworks × 17 criterios. 88% confianza. Avance 12/267 = 4.49%.

---

*Próxima actualización: al cerrar Fase 1 (Landscape + AI Providers) o cuando haya primeros docs `verified`.*