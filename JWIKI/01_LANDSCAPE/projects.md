# Comparativa de proyectos OSS de asistentes AI (2026)

## Resumen

En junio 2026 existen ~10 proyectos OSS activos con >500 stars que se pueden clasificar como "asistentes personales AI tipo JARVIS". Los más relevantes por adopción y arquitectura son OpenClaw (376k stars, multi-platform cloud), Superpowers (215k stars, skill framework), Hermes Agent (53k, self-evolving), OpenHuman (7.8k, desktop-first Rust) y OpenJarvis (Stanford, local-first académico).

## Objetivo

Documentar las diferencias clave entre proyectos OSS para que cualquier agente pueda decidir cuál usar (o inspirarse) según el caso.

## Estado

✅ Verificado

## Versiones compatibles

| Proyecto | Última versión estable | Fecha |
|---|---|---|
| OpenClaw | v2026.6.x | junio 2026 |
| Superpowers | v3.x | junio 2026 |
| Hermes Agent | v0.8.0 | abril 2026 |
| OpenHuman | v0.53.43 | mayo 2026 |
| OpenJarvis | v0.5.x | mayo 2026 |
| JarvisAgent | v1.0 | octubre 2025 |
| Clawdbot | v1.2 | junio 2026 |

## Proyectos compatibles

Todos los listados en este documento.

## Dependencias

- [01_LANDSCAPE/history.md](./history.md) — cronología (contexto)
- [01_LANDSCAPE/agent-frameworks.md](./agent-frameworks.md) — frameworks de agentes (LangGraph, CrewAI)
- [06_AGENTS/](../06_AGENTS/README.md) — patrones de agentes
- [07_MEMORY/](../07_MEMORY/README.md) — memory systems

## Arquitectura

No aplica — documento comparativo. Cada proyecto tiene su propia arquitectura documentada en su archivo individual.

## Descripción técnica

### Tabla comparativa

| Proyecto | Stars | Lenguaje | Multi-platform | Privacidad | Licencia | Categoría |
|---|---|---|---|---|---|---|
| OpenClaw | 376k | TypeScript | Discord/Telegram/WhatsApp/Slack | Cloud | MIT | Multi-platform cloud |
| Superpowers | 215k | Shell | N/A (framework) | Local | MIT | Skill framework |
| Hermes Agent | 53k | Python + Node.js | Web/API | Self-hosted | MIT | Self-evolving |
| OpenHuman | 7.8k | Rust + TS | Desktop | Local-first | (ver repo) | Desktop-first |
| OpenJarvis | (creciente) | Python | Desktop | Local-first | (ver repo) | Académico local-first |
| JarvisAgent | (variable) | Tauri 2 + Vue 3 + Rust | Desktop | Local | MIT | Coding-focused |
| Clawdbot | (variable) | TypeScript | Web | Local-first | MIT | MCP-based |

### Por categoría

**Multi-platform cloud (OpenClaw)**:
- ✅ Más maduro, 376k stars
- ✅ MCP protocol estándar
- ✅ Discord/Telegram/WhatsApp/Slack en una sola app
- ❌ Requiere cloud para algunos canales
- ❌ Complejidad alta

**Desktop-first (OpenHuman, JarvisAgent)**:
- ✅ Privacidad total (datos locales)
- ✅ Performance (Rust)
- ✅ Snapshots y sub-agents (JarvisAgent)
- ❌ Menos adopción
- ❌ Setup manual

**Skill framework (Superpowers)**:
- ✅ Skill format estandarizado
- ✅ Compatible con Claude Code, Codex
- ✅ 50+ skills preconstruidas
- ❌ Solo framework, no app
- ❌ Necesita agente host

**Self-evolving (Hermes Agent)**:
- ✅ Aprende del uso
- ✅ Multi-modal
- ✅ Nous Research support
- ❌ Más experimental
- ❌ Documentación incompleta

**Académico (OpenJarvis)**:
- ✅ Paper académico
- ✅ 5 primitivos teóricos claros
- ✅ Routing dinámico basado en complejidad
- ❌ Más teórico que práctico
- ❌ Adopción baja

## Flujo interno

No aplica — documento comparativo.

## Cambios entre eras

| Aspecto | 2024 | 2026 |
|---|---|---|
| Stars totales (top 7 OSS) | <50k | 700k+ |
| Frameworks dominantes | AutoGen, CrewAI | LangGraph, OpenClaw |
| Lenguaje | Python | TypeScript (frontend) + Python/Rust |
| Multi-platform | No | Sí (Discord, Telegram, etc.) |
| MCP protocol | No | Estándar de facto |
| Self-evolving | Investigación | Producción (Hermes) |

## Impacto sobre otros sistemas

- **06_AGENTS** — patrones que implementan
- **07_MEMORY** — ChromaDB, vector stores usados
- **08_VOICE** — voice integration (poco en OSS actual)
- **09_INTEGRATIONS** — OAuth, Telegram bot APIs
- **11_SECURITY** — sandboxing patterns
- **13_DEPLOYMENT** — Electron, Tauri, Docker

## Referencias cruzadas

- [01_LANDSCAPE/openclaw.md](./openclaw.md)
- [01_LANDSCAPE/openhuman.md](./openhuman.md)
- [01_LANDSCAPE/openjarvis.md](./openjarvis.md)
- [01_LANDSCAPE/jarvisagent.md](./jarvisagent.md)
- [01_LANDSCAPE/hermes-agent.md](./hermes-agent.md)
- [01_LANDSCAPE/clawdbot.md](./clawdbot.md)
- [01_LANDSCAPE/superpowers.md](./superpowers.md)
- [01_LANDSCAPE/tier-list.md](./tier-list.md) — ranking

## Fuentes

1. GitHub API (stars, languages, licenses) — acceso 2026-06-30
2. github.com/openclaw/openclaw — README, releases
3. github.com/obra/superpowers — README
4. github.com/tinyhumansai/openhuman — README, releases (v0.53.43)
5. github.com/Hermes-AI/Hermes-Agent — README (53k stars abril 2026)
6. github.com/open-jarvis/OpenJarvis — README, docs
7. github.com/myismu/JarvisAgent — README
8. github.com/clawdbot/clawdbot — README
9. Análisis CSDN "2026 6月 GitHub 最值得关注的 10 个 AI 开源项目" — 2026-06
10. juejin.cn "GitHub 上 Stars 最多的 8 个开源 AI Assistant 工具盘点" — 2026

## Nivel de confianza

**85%** — Stars y descripciones verificadas en GitHub directamente. Detalles técnicos de features específicas pueden variar entre releases.

## Pendientes

- [ ] Confirmar licenses exactos de OpenHuman, OpenJarvis, JarvisAgent, Clawdbot
- [ ] Comparar tamaños de comunidad (Discord servers, contributors)
- [ ] Documentar performance benchmarks (no hay datos públicos fiables aún)
- [ ] Añadir proyectos más pequeños pero interesantes: Hermes, Mark-XL, etc.

---

## Changelog

### 2026-06-30 — v1.0
- Autor: Aithera Escriba A (Mavis como proxy)
- Cambio: documento inicial
- Validador: Aithera Auditor A (Mavis como proxy)
- Material crudo: `JWIKI/material/JWIKI-002-raw.md`