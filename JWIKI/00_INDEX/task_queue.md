# JWIKI Task Queue (266 docs)

> Cola activa de tareas. Se procesa por orden cronológico con sistema de turnos.
> **Turno A** (cada 15 min en :00, :15, :30, :45) procesa IDs pares.
> **Turno B** (también cada 15 min) procesa IDs impares.
> Los turnos corren en paralelo, con 30 min de margen entre el mismo turno.

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

### Turno B (IDs impares, próximo: JWIKI-001)

### JWIKI-001 — Historia cronológica 1990s-2026
- **Path destino**: `01_LANDSCAPE/history.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta (Fase 1)
- **Notas**: cronología desde Clippy 1997 → Siri 2011 → Alexa 2014 → ChatGPT 2022 → agentes OSS 2026. Hitos clave, papers, releases, fechas.

### JWIKI-003 — OpenClaw (376k stars)
- **Path destino**: `01_LANDSCAPE/openclaw.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: el más popular. Stack (TypeScript), Discord/Telegram/WhatsApp/Slack, MCP-based, 376k stars. Features, arquitectura, limitaciones.

### JWIKI-005 — OpenJarvis (Stanford local-first)
- **Path destino**: `01_LANDSCAPE/openjarvis.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Stanford, local-first, 5 primitivos (model, reasoning, agent, tools/memory, routing). Routing dinámico basado en complejidad. Energía como métrica.

### JWIKI-007 — Hermes Agent (Nous Research)
- **Path destino**: `01_LANDSCAPE/hermes-agent.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: Nous Research, self-evolving, Python+Node.js, 53k stars. Diferencias con OpenClaw.

### JWIKI-009 — Superpowers (Skill framework)
- **Path destino**: `01_LANDSCAPE/superpowers.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-inv2
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: framework para skills (similar a OTKB). 215k stars, Shell. Compatible con Claude Code, Codex.

### Turno A (IDs pares, próximo: JWIKI-002)

### JWIKI-002 — Comparativa proyectos OSS principales
- **Path destino**: `01_LANDSCAPE/projects.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: JWIKI-001 (para tener cronología)
- **Prioridad**: alta (Fase 1)
- **Notas**: tabla comparativa OpenClaw/OpenHuman/OpenJarvis/JarvisAgent/Hermes/Clawdbot/Superpowers. Stars, licencia, stack, features, último commit.

### JWIKI-004 — OpenHuman desktop-first Rust+TS
- **Path destino**: `01_LANDSCAPE/openhuman.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: 7.8k stars, Rust+TS, v0.53.43 (mayo 2026). Personal context layer, conexiones Gmail/Notion/GitHub/Slack/Calendar/Drive/Linear/Jira.

### JWIKI-006 — JarvisAgent Tauri Vue 3
- **Path destino**: `01_LANDSCAPE/jarvisagent.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: ninguna
- **Prioridad**: media
- **Notas**: Tauri 2.0 + Vue 3 + Rust. 20+ LLMs. Snapshot engine, sub-agent delegation, plan approval.

### JWIKI-008 — Clawdbot MCP-based
- **Path destino**: `01_LANDSCAPE/clawdbot.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: ninguna
- **Prioridad**: media
- **Notas**: basado en MCP protocol. Menos stars pero interesante por el enfoque.

### JWIKI-010 — Comparativa frameworks de agentes
- **Path destino**: `01_LANDSCAPE/agent-frameworks.md`
- **Estado**: pending
- **Asignado**: aithera-wiki-investigador
- **Dependencias**: ninguna
- **Prioridad**: alta
- **Notas**: tabla LangGraph vs CrewAI vs AutoGen vs Google ADK vs OpenAI Agents SDK vs Semantic Kernel vs LlamaIndex vs Smolagents vs Strands.

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

- **Total**: 266 docs
- **Done**: 0
- **Verified**: 0
- **Rejected**: 0
- **Abandoned**: 0
- **Avance**: 0/266 = 0.00%

**ETA** (asumiendo ~8 docs/hora con 2 turnos): ~33 horas netas de investigación.

---

## Cómo añadir un punto nuevo

1. Identifica el dominio correcto (01-16).
2. Verifica que no exista en `wiki-map.md`.
3. Asigna el próximo ID disponible (siguiente al último).
4. Añádelo aquí en "Cola activa" con el formato estándar.

## Cómo cambiar estado

- `pending` → `in_progress`: el agente lo ha tomado.
- `in_progress` → `done`: borrador listo, pendiente de Auditor.
- `done` → `verified`: Auditor aprobó.
- `done` → `rejected`: crear nuevo punto con sufijo `-RW1`.

---

*Mantenedor: Mavis (orquestador).*