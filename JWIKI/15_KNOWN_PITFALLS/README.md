# Known Pitfalls — Overview

## Resumen

**Pitfalls conocidos** de Aithera V0.2-V0.8+. Bugs reales documentados en CLAUDE.md §16 y durante el desarrollo.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Pitfalls por categoría

### Bugs Aithera V0.2-V0.7.3 (CLAUDE.md §16)

- ✅ **God-endpoint `email_assistant.py`** (2038 líneas) — dividido en 7 routers en V0.7.2.
- ✅ **Bug `import json as _json` vs `json.`** en `log_activity` — fixed V0.7.2.
- ✅ **API keys en plaintext en BD** — cifrado DPAPI en V0.8.
- ✅ **CORS abierto `allow_origins=['*']`** — restringido V0.8.
- ✅ **Módulos paralelos legacy `backend/modules/`** — eliminados Sprint 1.
- ✅ **Streaming closure bug** — fixed V0.2.
- ✅ **Docs duplicados de fase** — archivados Sprint 4.

### Pitfalls técnicos genéricos

- ❌ **ChromaDB 1.5GB download** (sentence-transformers).
- ❌ **MiniMax API changes** (max_completion_tokens, model updates).
- ❌ **Pydantic v1 vs v2 syntax** (orm_mode deprecated).
- ❌ **React 18 strict mode double-render** (effects).
- ❌ **HashRouter Electron file://** (BrowserRouter no funciona).
- ❌ **Alembic schema divergence** (modificar modelo sin migration).

## Para Aithera

- ✅ V0.7.3: mayoría fixed.
- ⏳ V0.85+: revisar + cerrar restantes.

## Referencias cruzadas

- CLAUDE.md §16 (deuda técnica crítica)
- [JWIKI-241 god-endpoint-pattern.md](./god-endpoint-pattern.md)
- [JWIKI-242 modules-parallel-legacy.md](./modules-parallel-legacy.md)

## Fuentes

1. CLAUDE.md §16

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified