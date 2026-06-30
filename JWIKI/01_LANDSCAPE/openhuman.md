# OpenHuman

## Resumen

OpenHuman (de TinyHumans AI) es un agente personal AI desktop-first en Rust + TypeScript (Tauri 2.0). Su propuesta es "context in minutes, not weeks" — sincroniza automáticamente cada 20 min desde 100+ OAuth connectors (Gmail, Notion, GitHub, Slack, Calendar, Drive, Linear, Jira) y construye una memoria local jerárquica en SQLite con vault paralelo compatible con Obsidian. Mascot que habla (ElevenLabs TTS con lip-sync) y se une a Google Meet como participante real.

## Objetivo

Documentar el estado actual de OpenHuman: stack técnico, arquitectura, comparativa con otros agentes desktop-first.

## Estado

✅ Verificado

## Versiones compatibles

- **v0.53.43** — mayo 2026 (estable actual)
- **v0.50** — marzo 2026

## Proyectos compatibles

- **Categorías relacionadas**: JarvisAgent (Tauri+Vue), OpenJarvis (Python local-first)
- **Conectores OAuth**: Gmail, Notion, GitHub, Slack, Calendar, Drive, Linear, Jira, y 90+ más
- **Vault**: Obsidian-compatible

## Dependencias

- [01_LANDSCAPE/history.md](./history.md)
- [01_LANDSCAPE/projects.md](./projects.md)
- [01_LANDSCAPE/openclaw.md](./openclaw.md) — comparativa MIT vs GPL-3.0
- [07_MEMORY/](../07_MEMORY/README.md) — memoria semántica
- [08_VOICE/](../08_VOICE/README.md) — ElevenLabs TTS
- [09_INTEGRATIONS/](../09_INTEGRATIONS/README.md) — OAuth connectors

## Arquitectura

```
┌─────────────────────────────────┐
│  Frontend (React + TypeScript)  │  Tauri 2.0 shell
└──────────┬──────────────────────┘
           ▼
┌─────────────────────────────────┐
│  Rust backend (60% del código)  │  ~80 sub-módulos
│  openhuman-core, rpc/, agent/,  │
│  memory/, integrations/        │
└──────────┬──────────────────────┘
           ▼
┌─────────────────────────────────┐
│  Persistencia local (SQLite)    │  hierarchical summary trees
│  Vault paralelo (.md Obsidian)  │  Karpathy-style wiki
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  100+ OAuth connectors          │  via Composio
│  Sincronización cada 20 min      │
└─────────────────────────────────┘
```

## Descripción técnica

### Repositorio

- **Repo**: `github.com/tinyhumansai/openhuman` (canonico, activo)
- **Organización**: `tinyhumansai` (TinyHumans, Tiny Humans AI)
- **Fundador**: Steven Enamakel (`@senamakel` en GitHub y X)
- **Motivación**: "tried to set up an open-source AI agent for his dad earlier this year. Three hours of API keys, YAML..."

### Métricas oficiales (GitHub API)

- **Stars**: 33,923 (junio 2026)
- **Forks**: 3,293
- **Watchers**: 177
- **Open issues**: 204
- **Tamaño**: ~127 MB
- **Creado**: 2026-02-18
- **Último push**: 2026-06-30 (hoy)

### Licencia

- **SPDX**: **GPL-3.0** (NO MIT, copyleft fuerte)
- **Implicación**: cualquier fork/modificación distribuida debe mantener el código abierto bajo GPL-3.0
- **Diferencia con OpenClaw (MIT)** y **Hermes Agent (MIT)**: más restrictivo

### Stack tecnológico

- **Rust**: 60.5% (32.6 MB) — backend
- **TypeScript**: 36.6% (19.8 MB) — frontend
- **Otros**: JavaScript, Shell, CSS, HTML, Swift, PowerShell, Python, Dockerfile
- **Shell de escritorio**: **Tauri 2.0** (pnpm 10.10.0, Rust 1.93.0)
- **Frontend framework**: React + TypeScript
- **Estructura Rust**: ~80 sub-módulos (openhuman-core, rpc/, agent/, memory/, etc.)
- **Persistencia**: SQLite local + vault .md Obsidian-compat

### Features principales

- **Sincronización automática cada 20 min** desde 100+ OAuth connectors
- **Memoria local jerárquica** (summary trees en SQLite)
- **Vault Obsidian-compat**: chunks también como archivos .md editables
- **Mascot animado** con ElevenLabs TTS + lip-sync
- **Mascot en Google Meet** como participante real
- **Capa Composio** para integraciones OAuth gestionadas

### Comparativa con otros

| Aspecto | OpenHuman | OpenClaw | Hermes Agent | JarvisAgent |
|---|---|---|---|---|
| Stars | 33,923 | 376k | 53k | (var) |
| Lenguaje | Rust+TS | TypeScript | Python+Node | Tauri+Vue+Rust |
| Desktop-first | ✅ Sí | ❌ No (cloud) | ❌ No | ✅ Sí |
| Multi-channel | ❌ (GMeet focused) | ✅ (11+) | ✅ Web/API | ❌ Desktop |
| Skill marketplace | ❌ No | ✅ ClawHub | ❌ No | ❌ No |
| Memoria local | ✅ SQLite | ⚠️ Variable | ⚠️ Variable | ⚠️ Variable |
| Licencia | GPL-3.0 | MIT | MIT | MIT |

## Buenas prácticas

- ✅ Persistencia 100% local (privacidad)
- ✅ Vault dual: SQLite + .md (editables)
- ✅ Composio para OAuth (reduce complejidad de mantener 100+ connectors)
- ✅ Tauri (vs Electron) → binario más pequeño, menos RAM

## Errores comunes

- ❌ Confundir con OpenClaw (nombres similares)
- ❌ Asumir MIT como OpenClaw → OpenHuman es GPL-3.0
- ❌ Esperar multi-platform como OpenClaw → OpenHuman es desktop-first (GMeet)
- ❌ Subestimar tamaño de vault: 100+ connectors × 20min sync = mucho contexto

## Impacto sobre otros sistemas

- **06_AGENTS** — desktop agent pattern
- **07_MEMORY** — hierarchical summary trees en SQLite
- **08_VOICE** — ElevenLabs TTS + lip-sync
- **09_INTEGRATIONS** — 100+ OAuth via Composio
- **13_DEPLOYMENT** — Tauri 2.0 alternativa a Electron

## Referencias cruzadas

- [01_LANDSCAPE/projects.md](./projects.md)
- [01_LANDSCAPE/openclaw.md](./openclaw.md)
- [01_LANDSCAPE/jarvisagent.md](./jarvisagent.md)
- [04_FRONTEND/desktop-tauri.md](../04_FRONTEND/desktop-tauri.md)
- [08_VOICE/elevenlabs.md](../08_VOICE/elevenlabs.md)
- [09_INTEGRATIONS/google-oauth-flow.md](../09_INTEGRATIONS/google-oauth-flow.md)

## Fuentes

1. api.github.com/repos/tinyhumansai/openhuman (oficial) — 2026-06-30
2. github.com/tinyhumansai/openhuman (README) — acceso 2026-06-30
3. github.com/senamakel (perfil fundador) — acceso 2026-06-30
4. x.com/senamakel (perfil fundador) — acceso 2026-06-30
5. linkedin.com/company/tinyhumansai — acceso 2026-06-30
6. alphasignalai.substack.com "How OpenHuman works" — acceso 2026-06-30
7. juejin.cn comparativa licenses — 2026
8. blog.csdn.net/luolaihua2018 "OpenHuman disection" — 2026
9. knightli.com "OpenHuman 速读" — 2026-05-15

## Nivel de confianza

**90%** — Datos del repo directamente desde GitHub API. README y descripción oficial. Métricas exactas.

## Pendientes

- [ ] Probar OpenHuman con cuenta real (requiere install + OAuth setup)
- [ ] Verificar pricing si hay versión comercial
- [ ] Documentar migración desde otros agentes
- [ ] Comparar rendimiento desktop vs OpenClaw

---

## Changelog

### 2026-06-30 — v1.0
- Autor: Aithera Escriba A (Mavis como proxy en tick A 13:45)
- Cambio: doc inicial
- Material crudo: `JWIKI/material/JWIKI-004-raw.md` (86 hechos, 24KB)
- Validador: Aithera Auditor A (pendiente)