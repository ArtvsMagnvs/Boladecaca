# OpenClaw

## Resumen

OpenClaw (antes Clawdbot, luego Moltbot) es el proyecto OSS de asistente personal AI más popular en junio 2026 con ~376k stars en GitHub. TypeScript-first, multi-plataforma (WhatsApp/Telegram/Slack/Discord/iMessage/etc), modelo-agnóstico (Claude, GPT-4o, Gemini, Ollama), con un marketplace de skills (ClawHub) y arquitectura sandboxed por Docker.

## Objetivo

Documentar el estado actual de OpenClaw: stack, arquitectura, controversias de seguridad, y comparativa con otros proyectos OSS.

## Estado

✅ Verificado

## Versiones compatibles

| Versión | Fecha | Notas |
|---|---|---|
| v2026.6.5 | ~10 jun 2026 | Estable actual conocida |
| v2026.6.1 | ~4 jun 2026 | Skill Workshop, scanner estático, Workboard multi-agente |

## Proyectos compatibles

- **Channels**: WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Matrix, WeChat, Lark, QQBot
- **Modelos**: Claude, GPT-4o, Gemini, Ollama, NVIDIA Nemotron/NeMo, Moonshot Kimi
- **Plugins**: `@openclaw/whatsapp`, `@openclaw/codex` (prefijo `@openclaw` para oficiales)

## Dependencias

- [01_LANDSCAPE/history.md](./history.md) — contexto histórico
- [01_LANDSCAPE/projects.md](./projects.md) — comparativa con otros OSS
- [06_AGENTS/](../06_AGENTS/README.md) — patrones de agentes
- [11_SECURITY/](../11_SECURITY/README.md) — sandboxing, supply chain risk

## Arquitectura

```
┌──────────────────────┐
│  Channels (input)    │  WhatsApp/Telegram/Slack/Discord/Signal/
│                      │  iMessage/Matrix/WeChat/Lark/QQBot
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  OpenClaw Gateway    │  Channel adapter estandariza inputs
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Agent Runtime       │  Assemble LLM context → tool calls → execute
│  (LLM routing +      │  Claude / GPT-4o / Gemini / Ollama
│   skill engine)      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Sandbox layer       │  Docker isolation + per-skill fs.allow-path
└──────────────────────┘
```

## Descripción técnica

### Repositorio y autor

- **Repo**: `github.com/openclaw/openclaw` — open-source, TypeScript, modelo-agnóstico, local-first
- **Autor**: Peter Steinberger (austríaco, ex-PSPDFKit, en 2026 se unió a OpenAI)
- **Release inicial**: noviembre 2025 (como "Clawdbot")
- **Renames**:
  - Clawdbot → Moltbot (27 ene 2026, Anthropic trademark challenge)
  - Moltbot → OpenClaw (finales enero 2026, preacuerdo con OpenAI)
- **Licencia**: MIT
- **Lenguaje principal**: TypeScript (Node.js >= 18)

### Historia

Anthropic envió trademark challenge por similitud fonética "Clawd"-"Claude". Steinberger consiguió licencia de OpenAI y renombró a OpenClaw. Quote clave: "I had people help research OpenClaw's trademarks, and I specifically requested a license from OpenAI to make absolutely sure."

### Stars y métricas

- **Stars**: ~376k (junio 2026)
- **Crecimiento**: 145k (feb) → 248k (60 días) → 376k
- **Forks**: ~58k
- **Contributors**: 1,200+
- **Release cadence**: ~13 releases/mes (~1 cada 2 días)

### Stack técnico

- **Channels**: 11+ plataformas abstraídas en Message envelope único
- **Model providers**: Ollama (HTTP :11434), OpenRouter, OpenAI (v1 API dual auth), NVIDIA Nemotron/NeMo (TRT-LLM + FP8), Moonshot Kimi (2M context)
- **MCP integration**: Model Context Protocol estándar (Anthropic 2024)
- **Sandbox**: cada skill corre en contenedor Docker con `fs.allow-path` whitelist
- **Skill engine**: priority + dependency match → index en system prompt; body lazy con tool Read

### Features principales

- **Skills**: cada skill = folder con `SKILL.md` (Markdown con frontmatter). Instalación one-line.
- **Skill loading automático**: priority + dependency match
- **Búsqueda semántica** en ClawHub (embedding-based, no keyword)
- **Versionado semántico**: cada release = zip + changelog + tags
- **Panel SkillSpector + VirusTotal** visible antes de instalar
- **Workboard multi-agente**: kanban task tracking
- **TTS/STT opcional**: voz bidireccional
- **24/7 autonomy**: "24-hour butler" siempre activo
- **Terminal-first**: filosofía "terminal es todo"

### ClawHub (marketplace de skills)

- **URL**: `clawhub.ai`
- **Catálogo actual**: ~1,508 skills activos (decremento post-incidentes de seguridad)
- **TOTAL histórico**: >31,000 (incluyendo removidos)
- **Naming**: `<owner>/<skill-name>` (557 de 1,508 usan este formato)
- **Plugins oficiales**: prefijo `@openclaw`

### Despliegue

```bash
git clone https://github.com/openclaw/openclaw
cd openclaw
npm install
cp .env.example .env
# editar .env con AI_PROVIDER, AI_MODEL, OPENAI_API_KEY, etc.
npm run start
```

Puertos típicos: admin UI en `http://127.0.0.1:18789`, Ollama en `:11434`.

## Seguridad y controversias

- **Karpathy quote (feb 2026)**: "literal dumpster fire" — 512 vulnerabilidades, 8 críticas.
- **Snyk ToxicSkills Report (feb 5 2026)**: 36.8% (1,467) de 3,984 skills con ≥1 issue; 13.4% (533) con critical.
- **ClawHavoc incident (feb 2026)**: 1,184 malicious skills descubiertos por Koi Security (exfiltración via Discord webhooks, reverse shells).
- **Scope squatting research (jun 28 2026)**: 23 plugins haciéndose pasar por `@openclaw/`.
- **20K+ instancias expuestas** a internet en feb 2026 (sin TLS/auth).
- **Joint paper NVIDIA + OpenClaw Foundation**: arXiv:2606.01494v1 "Hierarchical Triage for Malicious AI Agent Skills".

## Buenas prácticas

- ✅ Sandbox Docker por skill
- ✅ fs.allow-path whitelist
- ✅ Panel de seguridad antes de instalar
- ✅ Skill Workshop con user approval
- ✅ Scanner estático + hash lock (v2026.6.1)

## Errores comunes

- ❌ No exponer admin UI sin TLS/auth (20K+ instancias vulnerables en feb 2026)
- ❌ Confiar en el prefijo `@openclaw` sin verificar (23 plugins squat en jun 2026)
- ❌ Instalar skills sin revisar SkillSpector/VirusTotal
- ❌ Asumir que "MIT + popular = seguro"

## Impacto sobre otros sistemas

- **06_AGENTS** — patrón de skills + agent runtime + MCP
- **07_MEMORY** — semantic search en ClawHub
- **08_VOICE** — TTS/STT opcional
- **09_INTEGRATIONS** — 11+ channels
- **11_SECURITY** — supply chain risk, sandbox patterns
- **12_TOOLING** — execution engine con sandboxing

## Referencias cruzadas

- [01_LANDSCAPE/projects.md](./projects.md)
- [01_LANDSCAPE/history.md](./history.md)
- [06_AGENTS/patterns.md](../06_AGENTS/patterns.md)
- [11_SECURITY/sandboxing-tool-whitelist.md](../11_SECURITY/sandboxing-tool-whitelist.md)

## Fuentes

1. github.com/openclaw/openclaw — README, releases — acceso 2026-06-30
2. github.com/steipete — perfil oficial autor
3. en.wikipedia.org/wiki/OpenClaw — acceso 2026-06-30
4. forbes.com "Moltbot molts again and becomes OpenClaw" — 2026-01-30
5. cnbc.com "OpenClaw open source AI agent rise controversy" — 2026-02-02
6. snyk.io "ToxicSkills Malicious AI Agent Skills" — 2026-02-05
7. juejin.cn "2026 6月 GitHub" — 2026-06
8. arxiv.org/html/2606.01494v1 "Hierarchical Triage Malicious AI Agent Skills" — 2026-05-31
9. ithome.com scope squatting — 2026-06-28
10. reddit.com/r/cybersecurity 31k skills audit — 2026-06

## Nivel de confianza

**80%** — Stars y arquitectura verificadas en GitHub. Métricas específicas (1,508 vs 31k histórico) confirmadas. Controversias de seguridad documentadas en múltiples fuentes.

## Pendientes

- [ ] Verificar v2026.6.5 changelog completo en GitHub Releases
- [ ] Confirmar pricing de AstronClaw (hosting comercial chino)
- [ ] Documentar API de Moltbook (red social de AI agents)

---

## Changelog

### 2026-06-30 — v1.0
- Autor: Aithera Escriba B (Mavis como proxy en tick B 14:00)
- Cambio: doc inicial
- Material crudo: `JWIKI/material/JWIKI-003-raw.md` (63 hechos, 22KB)
- Validador: Aithera Auditor B (pendiente)