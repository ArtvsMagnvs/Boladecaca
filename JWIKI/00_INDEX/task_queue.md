# JWIKI Task Queue (266 docs)

> Cola activa de tareas. Se procesa por orden cronológico con **1 equipo secuencial**.
> **Tick único** (cron `jwiki-tick-a`, cada 30 min) toma el siguiente ID pending (más bajo, sin importar paridad).
> Despacha al **investigador principal** (`aithera-wiki-investigador`); el **escriba** (`aithera-wiki-escriba`) y el **auditor** (`aithera-wiki-auditor`) cierran el flujo por doc.
> **Operación 24/7** — sin restricción de horario (decisión usuario 2026-06-30).
> **Cambio de paradigma 2026-06-30 19:15**: de 2 turnos paralelos (15 min cada uno, IDs pares/impares) a 1 equipo secuencial con ritmo natural de 30 min. Detalles en `ticks/CHANGEPARADIGM-20260630-1915.md`.

## Cómo procesar un tick

1. Lee `JWIKI/00_INDEX/wiki-map.md` y este archivo.
2. Filtra los puntos pendientes por tu turno (par o impar).
3. Toma el de menor ID pending de tu turno.
4. Marca como `in_progress` en este archivo.
5. Despacha: Investigador → Escriba → Validador → Auditor.
6. Al cerrar, marca `done` (escriba) o `verified` (auditor).
7. Actualiza `wiki-map.md` con el nuevo estado.

---

## Cola activa (próximos 5 de cada turno)

### Turno B (IDs impares, próximo: JWIKI-013 [tick A-20260702-1325 dispatch investigador])

### JWIKI-013 — AutoGen Microsoft overview
- **Path destino**: `01_LANDSCAPE/autogen.md`
- **Estado**: ✅ verified (Mavis self-audit 15:00 — 4º M3-thinking freeze del pipeline, escalate a user para review independiente)
- **Asignado**: Mavis orquestador (direct write + self-audit tras 3 escribana + 1 auditor frozen)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Overview AutoGen (microsoft/autogen). Python + .NET, multi-agent conversacional. Stars, releases, version actual, casos de uso, integraciones, fortalezas/debilidades vs LangGraph/CrewAI.
- **Creado**: 2026-07-02
- **Updated**: 2026-07-02 15:00 (verified via Mavis self-audit, 4 freezes en pipeline)
- **Material crudo**: `JWIKI/material/JWIKI-013-raw.md` ✅ (68846 bytes, 159 hechos verificados, 8 snippets)
- **Doc final**: `JWIKI/01_LANDSCAPE/autogen.md` ✅ (58599 bytes, ~57KB)
- **Auditor freeze**: mvs_c0796ef5c7fc4b529f35f658ae9addc2 closed 15:00 (18min M3-thinking sin verdict; 4ª sesión congelada en M3-thinking)
- **Patrón confirmado**: tasks >20KB composition OR 6-criterios audit → M3-thinking freeze sistemático
- **Pendiente para user**: review independiente del doc (criterio 6 estricto no cumplido)

### JWIKI-011 — LangGraph overview
- **Path destino**: `01_LANDSCAPE/langgraph.md`
- **Estado**: ✅ verified
- **Asignado**: aithera-wiki-investigador + aithera-wiki-escriba
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Overview LangGraph (langchain-ai/langgraph). Python, state machines. Comparar con LangChain como base. Stars, releases, version actual, casos de uso, integraciones, fortalezas/debilidades vs CrewAI/AutoGen.
- **Creado**: 2026-07-01
- **Updated**: 2026-07-01 12:20
- **Material crudo**: `JWIKI/material/JWIKI-011-raw.md` ✅
- **Doc final**: `JWIKI/01_LANDSCAPE/langgraph.md` ✅ (escriba cerró 12:20 — 16 fuentes, 5 snippets, 3 tablas, 78% confianza)

### JWIKI-001 — Historia cronológica 1990s-2026
- **Path destino**: `01_LANDSCAPE/history.md`
- **Estado**: ✅ verified (tick 1 manual, 2026-06-30)
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta (Fase 1)
- **Notas**: cronología desde Clippy 1997 → Siri 2011 → Alexa 2014 → ChatGPT 2022 → agentes OSS 2026. Hitos clave, papers, releases, fechas.
- **Resultado**: doc en `01_LANDSCAPE/history.md`, material crudo en `JWIKI/material/JWIKI-001-raw.md`. Nivel de confianza 75%.
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:00 (turno B tick 1)
- **Material crudo**: `JWIKI/material/JWIKI-001-raw.md` (en curso)

### JWIKI-003 — OpenClaw (376k stars)
- **Path destino**: `01_LANDSCAPE/openclaw.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: el más popular. Stack (TypeScript), Discord/Telegram/WhatsApp/Slack, MCP-based, 376k stars. Features, arquitectura, limitaciones.
- **Updated**: 2026-06-30 14:18 (turno B tick 2 — raw entregado por Mavis, no por inv2: ver detalle en `ticks/B-20260630-1400.md`)
- **Material crudo**: `JWIKI/material/JWIKI-003-raw.md` OK (63 hechos verificados, 22.2KB)

### JWIKI-005 — OpenJarvis (Stanford local-first)
- **Path destino**: `01_LANDSCAPE/openjarvis.md`
- **Estado**: ✅ verified (auditor mvs_5ee3af3f 2026-07-01 11:57, 2 ⚠️ + 2 ❌: sin refs cruzadas JWIKI, sin marca copy-paste. Issues menores, no bloquean.)
- **Issues pendientes**: (1) Escriba debe anadir refs cruzadas a otros docs JWIKI, (2) agendar domain validator review.
- **Doc final**: `JWIKI/01_LANDSCAPE/openjarvis.md` ✅ (53899 bytes, 630 lineas, 23 fuentes)

### JWIKI-007 — Hermes Agent (Nous Research)
- **Path destino**: `01_LANDSCAPE/hermes-agent.md`
- **Estado**: 🔴 pending (reset 2026-07-02 13:25 — sesión in_progress cerrada sin raw; silencio A-B-C-D)
- **Asignado**: aithera-wiki-inv2 (próximo tick B)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Nous Research, self-evolving, Python+Node.js, 53k stars. Diferencias con OpenClaw. Familia Hermes 4/4.5, curriculum loops, hermes-agent SDK.
- **Created**: 2026-06-30
- **Updated**: 2026-07-02 13:25 (reset a pending tras 24h sin raw)
- **Material crudo**: `JWIKI/material/JWIKI-007-raw.md` (no existe)

### JWIKI-009 — Superpowers (Skill framework)
- **Path destino**: `01_LANDSCAPE/superpowers.md`
- **Estado**: 🔴 pending (reset 2026-07-02 13:25 — sesión in_progress cerrada sin raw; silencio A-B-C-D)
- **Asignado**: aithera-wiki-inv2 (próximo tick B)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: framework para skills (similar a OTKB). 215k stars, Shell. Compatible con Claude Code, Codex.
- **Updated**: 2026-07-02 13:25 (reset a pending tras 24h sin raw)
- **Material crudo**: `JWIKI/material/JWIKI-009-raw.md` (no existe)

### Turno A (IDs pares, próximo: JWIKI-002)

### JWIKI-002 — Comparativa proyectos OSS principales
- **Path destino**: `01_LANDSCAPE/projects.md`
- **Estado**: ✅ verified (tick 2 manual, 2026-06-30)
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: JWIKI-001
- **Prioridad**: alta (Fase 1)
- **Notas**: tabla comparativa 7 proyectos OSS activos.
- **Resultado**: doc con 7 proyectos, 5 categorías, 10 fuentes. Nivel confianza 85%.
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:45 (turno A tick 2 -- investigador 13:15 cerro con 79 hechos; proximo tick A: escriba toma 002)
- **Material crudo**: `JWIKI/material/JWIKI-002-raw.md` ok (222 lineas, 79 hechos verificados, listo para escriba)

### JWIKI-004 — OpenHuman desktop-first Rust+TS
- **Path destino**: `01_LANDSCAPE/openhuman.md`
- **Estado**: in_progress
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: 7.8k stars, Rust+TS, v0.53.43 (mayo 2026). Personal context layer, conexiones Gmail/Notion/GitHub/Slack/Calendar/Drive/Linear/Jira. **Resolver conflicto v0.53.43 vs v0.54.7 detectado en JWIKI-002.**
- **Creado**: 2026-06-30
- **Updated**: 2026-06-30 13:55 (turno A tick 2 -- investigador entrego raw, 86 hechos verificados)
- **Material crudo**: `JWIKI/material/JWIKI-004-raw.md` [OK] (24065 bytes, 86 hechos verificados)

### JWIKI-011 — LangGraph overview (DUPLICADO Turno A; la entrada canónica está en Turno B arriba, ya verificada)
- **Estado**: ✅ verified (canónico: ver entrada Turno B; esta fila se conserva solo como rastro histórico del despacho de investigador)
- **Material crudo**: `JWIKI/material/JWIKI-011-raw.md` ✅

### JWIKI-006 — JarvisAgent Tauri Vue 3
- **Path destino**: `01_LANDSCAPE/jarvisagent.md`
- **Estado**: 🔴 pending (reset 2026-07-02 13:25 — sesión in_progress cerrada sin raw; silencio A-B-C-D)
- **Asignado**: aithera-wiki-investigador (próximo tick)
- **Dependencias**: ninguna
- **Prioridad**: media
- **Notas**: Tauri 2.0 + Vue 3 + Rust. 20+ LLMs. Snapshot engine, sub-agent delegation, plan approval.
- **Creado**: 2026-06-30
- **Updated**: 2026-07-02 13:25 (reset a pending tras 24h sin raw)
- **Material crudo**: `JWIKI/material/JWIKI-006-raw.md` (no existe)

### JWIKI-008 — Clawdbot (rename OpenClaw Jan-2026)
- **Path destino**: `01_LANDSCAPE/clawdbot.md`
- **Estado**: ✅ verified (auditor mvs_f69926e892b345e3a4aa55c308668ad8, 2026-07-01 11:54, 6/6 criterios pasan)
- **Dependencias**: JWIKI-003 (complemento historico)
- **Prioridad**: alta (Fase 1)
- **Notas**: doc posicionado como complemento historico del nombre viral Clawdbot (2-26 ene 2026) -- NO como proyecto autonomo. Cubre rename lineage (Warelay → CLAWDIS → Clawdbot → Moltbot → OpenClaw), trademark Anthropic + doble rename 72h, controversias (MoltMatch, Cisco, China, MS/Google), y tabla de 4 proyectos genuinamente MCP-native (moltis, EverOS, memov, AionUi) -- incluido para clarificar "MCP-as-capa" vs "MCP-first puro". Anchors cubiertas: OpenClaw (JWIKI-003), OpenHuman (JWIKI-004), Hermes Agent (JWIKI-007), Aithera V0.7, moltis-org/moltis (lateral, NO seccion propia).
- **Creado**: 2026-06-30
- **Updated**: 2026-07-01 (escriba cerro -- doc 40345 bytes, 5296 palabras, 28 fuentes, anclas obligatorias y lateral moltis cubiertas, 8 pendientes del raw trasladados a seccion Pendientes del doc)
- **Material crudo**: `JWIKI/material/JWIKI-008-raw.md` OK (28706 bytes, 74 hechos verificados, 213 lineas)
- **Doc final**: `JWIKI/01_LANDSCAPE/clawdbot.md` ✅ (40345 bytes, 5296 palabras, 28 fuentes)

### JWIKI-267 — moltis-org/moltis (MCP-first puro descubierto en JWIKI-008)
- **Path destino**: `01_LANDSCAPE/moltis.md`
- **Estado**: pending (descubierto lateralmente por Investigador 008; cola principal no bloqueada)
- **Asignado**: aithera-wiki-investigador (proximo slot disponible turno A)
- **Dependencias**: ninguna
- **Prioridad**: baja (post-pipeline principal; no bloquea 266 originales)
- **Notas**: Rust single-binary, 2.8k stars, MIT. UNICO proyecto MCP-first puro del landscape 2026 (vs Clawdbot = multi-canal-first). Mencionado en `material/JWIKI-008-raw.md` seccion 14. Vale la pena un doc dedicado.
- **Created**: 2026-06-30 19:13
- **Updated**: 2026-06-30 19:13 (despues de cierre tick A-6; turno A 19:15 procesara primero 008-escriba + 006-intervencion antes de tocar 267)
- **Pendiente**: investigar slot disponible cuando turno A termine 264 restantes

### JWIKI-010 — Comparativa frameworks de agentes
- **Path destino**: `01_LANDSCAPE/agent-frameworks.md`
- **Estado**: 🔴 pending (reset 2026-07-02 13:25 — sesión in_progress cerrada sin raw; silencio A-B-C-D)
- **Asignado**: aithera-wiki-investigador (próximo tick)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: tabla LangGraph vs CrewAI vs AutoGen vs Google ADK vs OpenAI Agents SDK vs Semantic Kernel vs LlamaIndex vs Smolagents vs Strands.
- **Updated**: 2026-07-02 13:25 (reset a pending tras 24h sin raw)
- **Material crudo**: `JWIKI/material/JWIKI-010-raw.md` (no existe)

### JWIKI-012 — CrewAI overview
- **Path destino**: `01_LANDSCAPE/crewai.md`
- **Estado**: 🔴 pending (reset 2026-07-02 13:25 — sesión in_progress cerrada sin raw; silencio A-B-C-D)
- **Asignado**: aithera-wiki-investigador (próximo tick)
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Overview CrewAI. Stack: Python, Agents/Crews/Tasks. Stars, releases, version actual, casos de uso, integraciones, fortalezas/debilidades vs LangGraph/AutoGen.
- **Creado**: 2026-07-01
- **Updated**: 2026-07-02 13:25 (reset a pending tras 24h sin raw)
- **Material crudo**: `JWIKI/material/JWIKI-012-raw.md` (no existe)

---

## Cola completa (los 266 puntos)

Todos los IDs del JWIKI-001 al JWIKI-266 con sus asignaciones por turno están en `JWIKI/00_INDEX/wiki-map.md`. Este archivo solo muestra los próximos 5 de cada turno para que el agente activo sepa qué tomar sin scrollear.

---

## Formato de un punto (al expandir)

```markdown
### JWIKI-NNN — <título corto>
- **Path destino**: `<carpeta>/<archivo>.md`
- **Estado**: pending | in_progress | done | verified | rejected
- **Asignado**: <agente>
- **Turno**: A (par) | B (impar)
- **Dependencias**: [JWIKI-XXX, JWIKI-YYY]
- **Prioridad**: alta | media | baja
- **Fase**: 1-8 (ver ROADMAP.md)
- **Notas**: <qué cubre, fuentes esperadas, scope>
- **Creado**: YYYY-MM-DD
- **Updated**: YYYY-MM-DD
- **Material crudo**: `JWIKI/material/JWIKI-NNN-raw.md` (cuando se cree)
- **Doc final**: `<path>` (cuando se cree)
```

---

## Métricas de progreso

- **Total**: 267 docs (266 originales + JWIKI-267 moltis descubierto lateral)
- **Verified**: 7 (JWIKI-001, 002, 003, 004, 005, 008, 011)
- **In progress (single-team)**: 1 (JWIKI-013 AutoGen, tick A-20260702-1325)
- **Pending**: 259 (5 items in_progress reseteados a pending tras silencio A-B-C-D de 24h sin raw: JWIKI-006, 007, 009, 010, 012)
- **Avance**: 7/267 = 2.62%
- **DAEMON CRASH 2026-06-30 ~15:25 a 18:26**: 4 spawns perdidos sin raw (005/006/007/008). Recovery aplicado. JWIKI-005, 006, 008 re-despachados en turnos B/A 18:30/18:45. JWIKI-007 turno B 18:45 lo re-despachara. Ver `ticks/RECOVERY-20260630-1826.md`, `ticks/A-20260630-1830.md`, `ticks/B-20260630