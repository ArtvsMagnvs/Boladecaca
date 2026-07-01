# CHANGELOG JWIKI

> Historial de cambios significativos. Para cambios menores ver git log.

## v1.0 — 2026-06-30 (Fase 0 Bootstrap)

### Añadido
- Estructura de 16 directorios de dominio (`00_INDEX` + `01-16`).
- `README.md` raíz con visión, principios, navegación y taxonomía.
- `CONSTITUTION.md` con 10 principios, fuentes prioritarias y plantilla.
- `ROADMAP.md` con 8 fases de investigación y meta de 15-30 días.
- `CONTRIBUTING.md` con reglas de contribución.
- `00_INDEX/README.md` con arquitectura de la JWIKI.
- `00_INDEX/architecture.md` con diagrama de la knowledge base.
- `00_INDEX/dependencies.md` con dependencias entre dominios.
- `00_INDEX/status.md` con estado inicial (Fase 0 completa).
- `00_INDEX/TEMPLATE.md` con plantilla obligatoria de documento.
- `00_INDEX/WORKFLOW.md` con loop autónomo del equipo.
- `00_INDEX/task_queue.md` con cola activa (266 IDs planificados).
- `00_INDEX/wiki-map.md` con mapa vivo (266 docs).
- README.md esqueleto en cada uno de los 16 dominios.

### Pendiente
- Investigación real (Fase 1+).
- Documentos validados con los 6 criterios.

---

## v1.3 — 2026-07-01 (JWIKI-005 auditado + JWIKI-008 en auditoría)

### Añadido
- **JWIKI-005** (`01_LANDSCAPE/openjarvis.md`) — OpenJarvis Stanford local-first. **VERIFIED** ✅ (auditor 2026-07-01 11:51, revisión independiente).
  - 26 fuentes contrastadas (GitHub API, arXiv x2, blog Stanford, blog Hazy Research, web oficial, blog Ollama, README, CHANGELOG, código fuente directo).
  - 5 primitivas reales confirmadas (Intelligence/Engine/Agents/Tools & Memory/Learning) — corrige 7 errores del briefing original.
  - Routing dual (HeuristicRouter + LearnedRouterPolicy), ComplexityQueryAnalyzer con 5-tier.
  - EnergyMonitor ABC con 4 vendors (NVIDIA/AMD/Apple/CPU_RAPL).
  - 5 snippets de código copy-paste ready con path:line.
  - 12 referencias cruzadas a otros docs JWIKI.
  - Tabla comparativa vs OpenClaw/OpenHuman/Hermes/Aithera V0.7.
  - **CONTRADICCION CONOCIDA**: `projects.md` declara `v0.5.x` pero el repo real es `v1.0.2` — marcada para corregir en JWIKI-002 (projects.md).
  - Nivel de confianza 85%.
- **JWIKI-008** (`01_LANDSCAPE/clawdbot.md`) — en auditoría (auditor 2026-07-01 11:49, session `mvs_f69926e8`).

### Métricas
- **5/266 docs verificados (1.88%)**

### Añadido
- **JWIKI-003** (`01_LANDSCAPE/openclaw.md`) — OpenClaw 376k stars. **VERIFIED** ✅.
  - Historia de renames (Clawdbot → Moltbot → OpenClaw).
  - Arquitectura completa (Channels → Gateway → Agent Runtime → Sandbox).
  - 11+ channels, MCP integration, ClawHub marketplace (1,508 activos / 31k histórico).
  - Controversias de seguridad documentadas (ClawHavoc 1,184 malicious, scope squatting).
  - 10 fuentes + arXiv paper.
  - Nivel confianza 80%.
- **JWIKI-004** (`01_LANDSCAPE/openhuman.md`) — OpenHuman desktop-first Rust+TS. **VERIFIED** ✅.
  - Datos oficiales de GitHub API (33,923 stars, GPL-3.0, Tauri 2.0).
  - 100+ OAuth connectors via Composio, sincronización cada 20 min.
  - Mascot con ElevenLabs TTS + Google Meet integration.
  - Vault paralelo Obsidian-compat.
  - 9 fuentes citadas.
  - Nivel confianza 90%.
- Material crudo automático en `JWIKI/material/JWIKI-003-raw.md` (63 hechos, 22KB) y `JWIKI-004-raw.md` (86 hechos, 24KB).
- Sistema de turnos operativo 24/7 (eliminado active-hours).
- Pipeline automático: crons disparan cada 15 min, Investigadores producen raw, Mavis cierra el flujo (Escriba+Auditor).
- Fix de spawn detectado en tick B 14:15 (path completo a mavis.cmd + lista args sin shell).
- Reportes individuales por tick en `JWIKI/ticks/`.

### Métricas
- **4/266 docs verificados (1.50%)**
- 3 commits en master
- 12 skills activas (entran en ciclo skill-evolve/skill-discover)

---

*Mantenedor: Aithera Escriba (`aithera-wiki-escriba`).*