# Auditoría del módulo legacy `backend/modules/email_assistant/` — B3, Sprint 1

> Fecha: 2026-07-02. Resultado: **eliminado completo**. Todo el contenido queda
> recuperable en git (commit `abf4493`, tag `v0.7.1`): `git show v0.7.1 -- backend/modules/`.

## Verificación previa

- **Cero referencias**: ningún archivo de `backend/app/`, `backend/scripts/`, ni `frontend/src/` importa `modules.email_assistant`. Código muerto confirmado.
- Era el "Email Executive Assistant V1" pre-V0.7, sustituido por `app/tools/email_tool.py` (44KB) + `app/api/endpoints/email_assistant.py` + `app/integrations/google_auth.py`.

## Veredicto por archivo

| Archivo | Líneas | Veredicto | Justificación |
|---|---|---|---|
| `__init__.py` | 19 | 🗑️ Muerto | Solo re-exports |
| `auth_manager.py` | 186 | 🗑️ Duplicado | `app/integrations/google_auth.py` lo cubre (OAuth + refresh + token en BD; el legacy usaba archivo local) |
| `gmail_tool.py` | 409 | 🗑️ Duplicado | `app/tools/email_tool.py` cubre todo (inbox, search, draft, send, MIME) |
| `calendar_tool.py` | 459 | 🗑️ Duplicado | `app/tools/calendar_tool.py` (29KB) lo supera (availability, proposals) |
| `memory.py` | 383 | 🗑️ Superado | Memoria JSON en archivo; superado por ChromaDB MemoryManager (V0.6) |
| `conversation_engine.py` | 380 | 📌 Referencia futura | Máquina de estados de conversación (ActionState, resolve_email_reference, approval flow). No se extrae ahora: el Orchestrator V1.0 la reinventará mejor con el patrón interrupt(). Consultar en git si sirve de inspiración |
| `email_intelligence.py` | 572 | 📌 Referencia futura | Heurísticas de prioridad (CRÍTICO→SPAM) y categorías. **Relevante para el triaje del Sprint 3** (V0.7.3): revisar sus keywords/regex como semilla de la etapa heurística antes de escribir el clasificador nuevo |

## Decisión

Se elimina el directorio entero en vez de mover los 2 archivos "referencia" a
`app/`: mover código muerto a la app crearía código sin uso (deuda nueva). Git
es el archivo. El Sprint 3 debe empezar con:

```bash
git show v0.7.1:backend/modules/email_assistant/email_intelligence.py
```

## Efecto

- Deuda §16.2 de CLAUDE.md saldada: una sola fuente de verdad para email.
- `-2.408` líneas de código muerto (+ README + SETUP).
