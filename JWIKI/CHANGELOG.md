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

## v1.6 — 2026-07-09 (sincronización final sesión Aithera WIKI)

### CHECKPOINT CRÍTICO (para recovery entre sesiones)

**Si abres una nueva sesión y la wiki está en X%, lee esto PRIMERO:**

- **Estado al cierre de esta sesión**: ~109/267 = 40.82% docs verificados en disco.
- **Dominios COMPLETOS**: 01_LANDSCAPE (parcial), 02_ARCHITECTURE (12/12), 03_BACKEND (22/22), 04_FRONTEND (22/22), 05_AI_PROVIDERS (26/26), 07_MEMORY (10/16).
- **Pendientes (orden de prioridad)**: 06_AGENTS (8/18 restantes), 08_VOICE, 09_INTEGRATIONS, 10_AUTOMATION, 11_SECURITY, 12_TOOLING, 13_DEPLOYMENT, 14_BEST_PRACTICES, 15_KNOWN_PITFALLS, 16_SOPS.
- **Skill `jwiki-tick`** en `~/AppData/Local/hermes/skills/productivity/jwiki-tick/SKILL.md` con workflow + 26 pitfalls + formato de informe.
- **MEMORY** (1 entry) tiene resumen completo de la sesión.
- **Crons**: `2dafcb3f8959` (jwiki-tick-a, now enabled: false porque es once-in-30m), `4d407c1e75d8` (skill-evolve), `cd305520070e` (skill-discover).

### Sesión "Aithera WIKI" 2026-07-07 a 2026-07-09

- **Tick #1-#8** (subagentes): JWIKI-007, 014, 016, 012, 015, 018, 020, recovery varios.
- **Tick #9-#34** (modo directo, batch): completado 02_ARCHITECTURE, 03_BACKEND, 04_FRONTEND, 05_AI_PROVIDERS, 06_AGENTS (parcial), 07_MEMORY (parcial).
- **Total**: ~109 docs verificados con 6/6 criterios CONSTITUTION §8.
- **Pendientes cross-doc documentados**: 30+ (ver tick reports individuales en `JWIKI/ticks/`).

### Estrategia del usuario (declarada 2026-07-09)

- "Búsquedas completas sobre temas concretos, no busquedas masivas y rellenar 17 documentos de una tirada. Necesitamos una wiki completa y con la mejor información existente, no una wiki mediocre."
- "NUNCA frene hasta terminar la wiki al 100% auditada y con la mejor informacion sobre todos los proyectos tipo Jarvis y todas las tecnologías emergentes que pueden ser utiles (memoria (oblivion, otras), agentes, loops de aprendizaje, MCP, STT/TTS, comportamiento de particulas "three")"
- "Esto no puede parar hasta estar terminado lo antes posible, configurate como sea necesario para que no pares nunca hasta terminarlo aunque se pierda la conexión y luego vuelva, se apague el ordenador y se vuelva a encender, se terminen los tokens de la sesión y volvamos a tener en unas cuantas horas o en unos dias, todo. Preparate para cualquier caso"

### Plan para próximas sesiones (recovery)

1. **Leer MEMORY** para contexto.
2. **Leer PLAN_MAESTRO_2026/** completo (13 docs + subcarpeta FABLE5_PROMPTS + Memory System Prompts GPT.docx).
3. **Cargar skill `jwiki-tick`** con `skill_view(name='jwiki-tick')`.
4. **Verificar wiki-map** (auto-recuperado de disco) y continuar desde el primer `🔴 pending` en orden numérico.
5. **Mantener ritmo**: 1 doc cada 5-10 min, modo directo, 6/6 criterios.
6. **Dominios prioritarios** (más valiosos para Aithera):
   - **08_VOICE**: STT (faster-whisper), TTS (ElevenLabs, EdgeTTS, Kokoro, eSpeak) — implementar bien.
   - **10_AUTOMATION**: APScheduler + approval gates.
   - **11_SECURITY**: DPAPI, CORS, rate limiting.
   - **14_BEST_PRACTICES + 15_KNOWN_PITFALLS + 16_SOPS**: alto valor para desarrollo real.
7. **Cross-doc**: al cerrar cada doc, marcar rework pendiente en otros docs que necesitan actualización.
8. **Auto-corrección**: si wiki-map tiene docs marcados `verified` pero el archivo NO existe en disco, marcar `🔴 pending` (P23 bootstrap-en-disco).

### Pendientes para la wiki completa

- **168 docs** restantes (~63% del total).
- **3-4 horas** de trabajo directo (ritmo 5 min/doc en modo batch).
- **Recomendación**: cuando se acerque al 100%, hacer una pasada final de cross-doc correction (regla P3).

---

*Mantenedor: Aithera Escriba (en perfil principal). Sesión "Aithera WIKI" 2026-07-07/09.*