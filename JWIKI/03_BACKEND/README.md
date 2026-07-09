# Frameworks Backend — Comparativa

## Resumen

Comparativa de frameworks backend Python (FastAPI, Flask, Django, Tornado, Sanic) y otros lenguajes (Express, Tauri Rust).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Frameworks Python

| Framework | Async | Performance | Ecosystem | Use case |
|---|---|---|---|---|
| **FastAPI** | ✅ nativo | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Aithera V0.7.3, APIs modernas |
| Flask | ❌ sync | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Legacy, simple |
| Django | ❌ sync (+ASGI) | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Full-stack web framework |
| Tornado | ✅ async | ⭐⭐⭐⭐ | ⭐⭐ | Long-lived connections |
| Sanic | ✅ async | ⭐⭐⭐⭐ | ⭐⭐ | Flask-like async |
| aiohttp | ✅ async | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Client + server |

## Frameworks no-Python

| Framework | Lenguaje | Performance | Use case |
|---|---|---|---|
| **Express** | Node.js | ⭐⭐⭐⭐ | Aithera NO lo usa |
| **Tauri backend** | Rust | ⭐⭐⭐⭐⭐ | Aithera V0.85+ posible |
| **Next.js API routes** | TS/React | ⭐⭐⭐⭐ | Web apps |
| **Bun** | TS | ⭐⭐⭐⭐⭐ | Modern JS |

## FastAPI — el elegido para Aithera

**Por qué FastAPI**:
- ✅ Async nativo (clave para SSE streaming).
- ✅ Type hints + Pydantic (validation automática).
- ✅ OpenAPI auto-generated.
- ✅ Performance top-tier.
- ✅ Ecosystem rico (SQLAlchemy, Alembic, etc.).
- ✅ Lifespan events (startup/shutdown async).

## Para Aithera

- ✅ V0.7.3: FastAPI + SQLAlchemy + Pydantic v2 + lifespan.
- ⏳ V0.85+: considerar Tauri backend para Rust perf crítico.

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-060 tauri-backend.md](./tauri-backend.md)
- [JWIKI-061 flask-vs-fastapi.md](./flask-vs-fastapi.md)

## Fuentes

1. https://fastapi.tiangolo.com/
2. https://www.techempower.com/benchmarks/

## Nivel de confianza

**90%** — FastAPI bien establecido.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified