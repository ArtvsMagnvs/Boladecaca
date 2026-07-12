# ADRs — Architecture Decision Records

## Resumen

**ADRs** (Architecture Decision Records) documentan decisiones arquitectónicas clave. Aithera usa ADR pattern para V0.8+.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Formato

```markdown
# ADR-001: Use FastAPI for backend

## Status
Accepted (2026-07-01)

## Context
Need async Python web framework. Alternatives: Flask, Django, Tornado, Sanic.

## Decision
Use FastAPI.

## Consequences
- ✅ Async + OpenAPI + Pydantic v2 built-in.
- ❌ Less mature than Django.
- ❌ Smaller ecosystem than Flask.

## Alternatives considered
- Flask: not async-native.
- Django: too opinionated.
- Tornado: deprecated.
```

## ADR-001 a ADR-008 (Aithera)

- ADR-001: Use FastAPI.
- ADR-002: SQLAlchemy 2.0 (vs SQLModel, Tortoise).
- ADR-003: ChromaDB para memory (vs Pinecone, Qdrant).
- ADR-004: Pydantic v2 (vs dataclasses, attrs).
- ADR-005: Electron (vs Tauri, Qt).
- ADR-006: HashRouter (vs BrowserRouter).
- ADR-007: DPAPI Windows (vs Keychain/libsecret).
- ADR-008: APScheduler V0.9 (vs Celery).

## Para Aithera

- ⏳ V0.85+: docs/adr/ folder con ADRs.

## Fuentes

1. https://adr.github.io/
2. https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified