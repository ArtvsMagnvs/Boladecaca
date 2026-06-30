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

## v1.1 — 2026-06-30 (primeros 2 ticks verificados)

### Añadido
- **JWIKI-001** (`01_LANDSCAPE/history.md`) — Historia cronológica 1990s-2026. **VERIFIED** ✅.
- **JWIKI-002** (`01_LANDSCAPE/projects.md`) — Comparativa proyectos OSS principales. **VERIFIED** ✅.
  - Tabla con 7 proyectos OSS activos (OpenClaw 376k, Superpowers 215k, Hermes 53k, OpenHuman, OpenJarvis, JarvisAgent, Clawdbot).
  - 5 categorías: multi-platform cloud, desktop-first, skill framework, self-evolving, académico.
  - 10 fuentes citadas.
  - Nivel de confianza 85%.
- Material crudo en `JWIKI/material/JWIKI-001-raw.md` y `JWIKI-002-raw.md`.
- Sistema de turnos operativo (Turno A: IDs pares, Turno B: IDs impares).
- 14 agentes `aithera-*` con agent.md completo (6 wiki + 8 especialistas).
- 4 crons configurados (jwiki-tick-a/b, skill-evolve, skill-discover).
- 12 skills custom creadas (4 globales + 8 por agente).
- 2 commits en master (root-commit a7f9f49, tick 1 9a60e5b).

### Estado de skills (entran en ciclo skill-evolve/skill-discover)

- `aithera-v0-7-architecture` (global)
- `aithera-coding-standards` (global)
- `jwiki-tick-workflow` (global)
- `mavis-orchestrator-loop` (global)
- `web-research` (aithera-wiki-investigador)
- `doc-synthesis` (aithera-wiki-escriba)
- `audit-criteria` (aithera-wiki-auditor)
- `fastapi-patterns` (aithera-backend)
- `react-18-streaming` (aithera-frontend)
- `provider-integration` (aithera-ia)
- `agent-manager` (aithera-agentes)
- `chromadb-patterns` (aithera-memoria)

---

*Mantenedor: Aithera Escriba (`aithera-wiki-escriba`).*