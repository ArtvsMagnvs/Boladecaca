# Backlog priorizado y plan de sprints

> Unidad de trabajo = "sprint" = un prompt/sesión de Claude Code. Cada sprint
> termina con producto usable + commit (principio 1 y 7).

---

## Backlog priorizado (P0 = ya, P3 = puede esperar)

| ID | Tarea | Prioridad | Fase | Depende de |
|---|---|---|---|---|
| B1 | Commit de los ~204 archivos pendientes + tag v0.7.1 | **P0** | V0.7.2 | — |
| B2 | Ampliar pytest: smoke + contratos email (~30 rutas) | **P0** | V0.7.2 | B1 |
| B3 | Auditoría y eliminación de `modules/email_assistant/` legacy | **P0** | V0.7.2 | B1 |
| B4 | Split god-endpoint en 5 routers + `email_service.py` | P1 | V0.7.2 | B2 |
| B5 | Triaje del inbox (7 categorías, 2 etapas) | P1 | V0.7.3 | B4 |
| B6 | Autonomía gradual por regla (propose→auto) | P1 | V0.7.3 | B4 |
| B7 | Digest diario (endpoint + panel Hub) | P1 | V0.7.3 | B5 |
| B8 | Archivar docs de fase duplicados + actualizar CLAUDE.md + tag v0.7.3 | P1 | V0.7.3 | B5-B7 |
| B9 | Gateway + MessageEnvelope + adapters | P2 | V0.8 | B8 |
| B10 | Security hardening (CORS, PIN, cifrado keys, rate limit) | P2 | V0.8 | B8 |
| B11 | Telegram bot (adapter + comandos) | P2 | V0.8 | B9, B10 |
| B12 | Web client servido por FastAPI + PWA | P2 | V0.8 | B9, B10 |
| B13 | Ingesta background email/calendar → ChromaDB | P2 | V0.8.5 | B8 |
| B14 | Summary trees + contexto en chat | P2 | V0.8.5 | B13 |
| B15 | APScheduler + AutomationRule/Execution + UI | P3 | V0.9 | B8 |
| B16 | Approval gates genéricos + checkpointing | P3 | V0.9 | B15 |
| B17 | daily_briefing + system_monitor | P3 | V0.9 | B15, B7 |
| B18 | Orchestrator (intent routing + planner + traces) | P3 | V1.0 | B16 |
| B19 | MCP server + cliente | P3 | V1.1 | B18 |
| B20 | Auto-start backend desde Electron | P3 | flotante | B1 |
| B21 | Chat general: separar/ocultar razonamiento de modelos reasoning (MiniMax `<think>`) | P2 | flotante | — |

## Sprint 1 (el próximo prompt) — "Red de seguridad"

**3 tareas: B1 + B2 + B3.** Ni una más.

Por qué estas tres y no empezar directo con el split: hay ~204 archivos sin
commitear (todo el trabajo V0.7.1) y el único seguro contra romper OAuth en el
refactor son los tests de contrato. Sesión 0 del doc 02. Es trabajo poco vistoso
que compra velocidad para todo lo demás.

Contenido exacto del sprint:
1. Commit de todo lo pendiente + tag `v0.7.1` (mensaje: `feat: Aithera V0.7.1 — Email Assistant Fase 4b completa`).
2. Ampliar `backend/tests/`: smoke de arranque, imports de routers, contratos de los ~30 endpoints de email con Gmail mockeado (ruta + método + shape de respuesta).
3. Auditoría de `backend/modules/email_assistant/` con veredicto por archivo y eliminación (o extracción de lo rescatable a `app/services/`).

Definición de hecho: `pytest` verde, `git log` con historia, una sola implementación
de email en el repo, CLAUDE.md §16.2 actualizado.

## Sprint 2 — "Split" (B4)

El refactor del god-endpoint completo, con los contratos como red. Commit por router.

## Sprint 3-4 — "Triaje + autonomía + digest" (B5, B6, B7)

Sprint 3: clasificador de triaje + migración Alembic + inbox categorizado en UI.
Sprint 4: autonomía gradual + digest + panel Hub + B8 (cierre de fase, tag v0.7.3).

## Cadencia recomendada

- 1 sprint = 1 prompt bien acotado con criterio de cierre explícito.
- Nunca mezclar refactor con feature en el mismo sprint (lección del god-endpoint: nació de hacer todo a la vez "por urgencia").
- Al cerrar cada sprint: actualizar CLAUDE.md si tocó arquitectura (regla §19) y marcar la tarea aquí.

## Registro de progreso

| Sprint | Fecha | Tareas | Estado |
|---|---|---|---|
| 1 | 2026-07-02 | B1, B2, B3 | ✅ Completado (tag v0.7.1, 61 tests) |
| 2 | 2026-07-02 | B4 | ✅ Completado (tag v0.7.2, 7 routers, 62 tests, fix log_activity) |
| 3 | 2026-07-02 | B5 | ✅ Completado (triaje 7 categorías 2 etapas, 81 tests) |
| 4 | 2026-07-02 | B6, B7, B8 | ✅ Completado (tag v0.7.3 — **FASE EMAIL ASSISTANT CERRADA**, 97 tests) |

---
*Creado: 2026-07-02. Actualizar el registro al cerrar cada sprint.*
