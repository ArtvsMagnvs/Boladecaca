# Fase Email Assistant FINAL — V0.7.2 / V0.7.3

> Objetivo: dejar el Email Assistant **terminado**: refactorizado, testeado, con
> triaje completo del inbox y autonomía gradual por regla (patrón Inbox Zero).
> Prerrequisito: V0.7.1 funcionando. Referencia de deuda: CLAUDE.md §16.1 y §16.2.

---

## Estado de partida (real)

Hecho en V0.7 / V0.7.1: OAuth Google, inbox, search, draft, send con confirmación,
summary, reglas auto-reply (CRUD + test + send), detección de reuniones en dos etapas
(patrón AMD GAIA), `detect_calendar_conflicts` con cross-check de Google Calendar,
captura de urgentes sin regla, toast contextual, `EmailActivityLog`, tests unitarios
de meeting detection. Frontend `EmailAssistant.tsx` (51KB) funcional.

Pendiente (lo que impide llamarlo "terminado"):
- `email_assistant.py` = god-endpoint de **2038 líneas** (verificado 2026-07-02; CLAUDE.md decía 1889 — sigue creciendo).
- `backend/modules/email_assistant/` legacy duplicando dominio email.
- Sin triaje del inbox completo (categorías) ni digest.
- Autonomía de reglas binaria (regla existe → actúa); sin niveles de confianza.
- Sin tests del módulo completo (solo meeting detection en `backend/tests/test_email_assistant.py`).
- **~204 archivos modificados/sin trackear sin commitear** (verificado 2026-07-02: hay 5 commits — bootstrap V0.7 + ticks JWIKI — pero todo el trabajo V0.7.1 está pendiente de commit; CLAUDE.md §1 está desactualizado en esto).

---

## Sesión 0 — Red de seguridad (hacer ANTES de tocar nada)

**S0.1 — Commit del trabajo pendiente.** Commitear los ~204 archivos pendientes con
mensaje `feat: Aithera V0.7.1 — Email Assistant Fase 4b completa`. Tag `v0.7.1`.
Nota: al commitear desde el sandbox puede aparecer un `.git/index.lock` bloqueado —
hacerlo desde la máquina del usuario si ocurre. A partir de aquí, un commit por paso
terminado (principio 1: cada commit deja producto usable).

**S0.2 — Ampliar pytest.** Ya existe `backend/tests/test_email_assistant.py`
(meeting detection + conflicts). Añadir: smoke test de arranque (TestClient,
`GET /health`), test de import de los 11 routers, y **tests de contrato del API de
email**: para cada endpoint público de `email_assistant.py` (~30 rutas `@router`),
un test que fija ruta + método + shape de respuesta (con Gmail mockeado). Estos
tests son el seguro del refactor: si pasan antes y después del split, el frontend
no se entera.

**S0.3 — Auditoría del módulo legacy.** Leer `backend/modules/email_assistant/`
(auth_manager, gmail_tool, email_intelligence, conversation_engine, memory,
calendar_tool) y producir veredicto por archivo: `muerto` (borrar) / `útil`
(extraer a `app/tools/` o `app/services/`) / `duplicado` (borrar tras verificar que
`app/tools/email_tool.py` cubre lo mismo). Eliminar el directorio al terminar.
Resultado esperado: una sola fuente de verdad para email.

Criterio de cierre S0: repo con historia git, `pytest` verde, `modules/` resuelto.

## Sesión 1 — Split del god-endpoint (V0.7.2)

Dividir `app/api/endpoints/email_assistant.py` en 5 routers (plan ya definido en
CLAUDE.md §16.1), **sin cambiar ninguna ruta pública**:

| Router nuevo | Endpoints |
|---|---|
| `email_auth.py` | `/status`, `/auth/credentials`, `/auth/start`, `DELETE /auth` |
| `email_inbox.py` | `/inbox`, `/{id}`, `/search`, `/summary` |
| `email_compose.py` | `/draft`, `/send` |
| `email_auto_reply.py` | `/auto-reply/rules` CRUD, `/auto-reply/test`, `/auto-reply/send` |
| `email_meetings.py` | proposals, confirmaciones, reagendado, conflicts |

Reglas del refactor:
1. Mover código, no reescribirlo. Cero cambios de comportamiento en esta sesión.
2. Lógica compartida (helpers, parsing, clientes Gmail) → `app/services/email_service.py` (por fin `services/` deja de estar vacío).
3. Los 5 routers se montan bajo el mismo prefijo `/api/email` en `main.py`.
4. Tests de contrato S0.2 verdes antes y después. Probar OAuth con cuenta secundaria (riesgo §17).
5. Commit por router migrado.

Criterio de cierre: `email_assistant.py` eliminado, 15 routers montados, contratos verdes, OAuth probado.

## Sesión 2 — Triaje del inbox + digest (V0.7.3)

Patrón Inbox Zero: **la IA clasifica, el rule engine ejecuta, el usuario aprueba**.

**S2.1 — Clasificador de triaje.** `email_service.triage(email) -> categoria`
con categorías fijas: `urgente`, `responder`, `reunión`, `newsletter`, `factura`,
`spam-social`, `fyi`. Dos etapas como en meeting detection: heurística barata
(remitente, asunto, headers de lista) primero, LLM solo para los ambiguos.
Usar el proveedor activo; diseñar el prompt para funcionar también con modelo local.
Persistir categoría en BD (columna nueva vía migración Alembic — regla §16.7).

**S2.2 — Autonomía gradual por regla.** Añadir a `EmailAutoReplyRule` el campo
`autonomy: "propose" | "auto"` (default `propose`) + contador de aciertos
(`approved_count`, `edited_count`, `rejected_count` — se alimentan de la acción del
usuario sobre cada propuesta, vía `EmailActivityLog`). UI: botón "subir a automático"
visible solo cuando la regla lleva N propuestas aprobadas sin editar (sugerido N=5).
Ninguna regla nace en `auto`. El envío en `auto` sigue registrándose en el activity log.

**S2.3 — Digest diario.** Endpoint `GET /api/email/digest?date=` que devuelve:
conteo por categoría, urgentes pendientes, reuniones detectadas, respuestas
propuestas esperando aprobación. Panel en `EmailAssistant.tsx` + tarjeta en el Hub.
(En V0.9 el Automation Engine lo programará como briefing matinal — aquí solo el endpoint.)

**S2.4 — Tests.** Unit tests del triaje (fixtures de emails reales anonimizados),
del ciclo de autonomía (propose→auto) y del digest.

Criterio de cierre: inbox se muestra categorizado, reglas con autonomía gradual
funcionando, digest disponible en Hub, suite completa verde.

## Sesión 3 — Pulido y cierre de fase

- Revisar `EmailAssistant.tsx` (51KB): extraer sub-componentes si algún bloque supera ~300 líneas (InboxList, RulePanel, MeetingPanel, DigestPanel). Sin rediseño visual.
- Archivar docs duplicados (`Fase_2_..._V04.md`, `Fase_5_Telegram_V07.md`) en `archive/`.
- Actualizar CLAUDE.md §1, §3, §6, §16 (deuda 1, 2 y 3 saldadas) y bump a V0.7.3 en los 3 sitios (main.py, config.py, package.json).
- Commit + tag `v0.7.3`.

## Definición de "Email Assistant TERMINADO"

1. Ningún archivo del dominio email > 500 líneas.
2. Una sola implementación de email en el repo.
3. Inbox triado en 7 categorías con 2 etapas (barato → LLM).
4. Reglas con autonomía gradual y auditoría completa en activity log.
5. Digest consultable desde el Hub.
6. Suite pytest del módulo verde; OAuth verificado con cuenta secundaria.
7. Historia git limpia con tags v0.7.1 → v0.7.3.

## Estimación

| Sesión | Contenido | Tamaño |
|---|---|---|
| S0 | git + pytest baseline + auditoría legacy | 1 sesión |
| S1 | split god-endpoint | 1-2 sesiones |
| S2 | triaje + autonomía + digest | 2 sesiones |
| S3 | pulido + docs + release | 1 sesión |

---
*Creado: 2026-07-02.*
