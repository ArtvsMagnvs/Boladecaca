# Monolith vs Microservices — Decisión arquitectónica para Aithera

## Resumen

**Monolith** vs **Microservices** es la decisión arquitectónica clásica. Aithera V0.7.3 es un **monolith modular** (FastAPI monolítico + Electron monolítico), NO microservices. Para V1.0+ podría evaluarse split parcial.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Comparativa

| Aspecto | Monolith | Microservices |
|---|---|---|
| **Complejidad inicial** | Baja ✅ | Alta ❌ |
| **Despliegue** | 1 deploy ✅ | N deploys ❌ |
| **Escalabilidad** | Vertical (scale up) | Horizontal (scale out) ✅ |
| **Resiliencia** | ❌ un crash = todo cae | ✅ un crash = servicio afectado |
| **Transacciones ACID** | ✅ fáciles | ❌ complejas (saga) |
| **Testing** | ✅ E2E simple | ❌ complejo |
| **Team scaling** | ❌ bottleneck | ✅ equipos independientes |
| **Tech diversity** | ❌ 1 stack | ✅ polyglot |
| **Network overhead** | ❌ in-process | ❌ red inter-service |
| **Debugging** | ✅ stack trace simple | ❌ distributed tracing |

## Cuando elegir Monolith

- ✅ **Equipo pequeño** (< 10 devs).
- ✅ **Producto nuevo** (validar mercado primero).
- ✅ **Dominio simple** (no microservices necesarios).
- ✅ **Startup / personal project** (como Aithera).

## Cuando elegir Microservices

- ✅ **Equipo grande** (> 50 devs).
- ✅ **Producto maduro** con dominios claros.
- ✅ **Necesidad de escalar** partes específicas independientemente.
- ✅ **Resiliencia crítica** (99.99%+ SLA).

## Aithera — monolith modular

Aithera V0.7.3 sigue el patrón **monolith modular**:

- **Backend FastAPI monolítico**: `backend/app/main.py` con `lifespan` que arranca TODO (AI Manager, Memory, Agents, Tools, Gateway, Telegram, Voice).
- **Frontend Electron monolítico**: `frontend/src/App.tsx` con HashRouter + Zustand.
- **Persistencia compartida**: PostgreSQL (con fallback SQLite) + ChromaDB.
- **Componentes débilmente acoplados**: routers separados (email, calendar, agents, etc.) que comparten DB pero no red.

### Para V1.0+

Aithera podría considerar split:
- **Microservicio de AI Provider** (separar del API principal).
- **Microservicio de Email Assistant** (separar por carga).
- **Microservicio de Memory** (separar ChromaDB para escalar independiente).

**Pero NO antes de V1.0**. La complejidad extra de microservices no compensa con <100 usuarios.

## Modular monolith — el sweet spot

**Modular monolith** es el patrón recomendado para Aithera:
- 1 deploy (sencillo).
- Módulos bien separados internamente (`app/api/endpoints/email_*.py`).
- Preparado para split futuro si es necesario.

Es lo que Aithera ya hace (V0.7.2 split del god-endpoint email en 7 routers).

## Para Aithera V0.85/V1.0

- Mantener monolith modular.
- Considerar **workers asíncronos** (Celery, RQ) para tareas pesadas (memory indexing, email processing).
- NO split a microservices prematuramente.

## Referencias cruzadas

- [JWIKI-046 client-server.md](./client-server.md) — arquitectura cliente-servidor
- [JWIKI-049 async-patterns.md](./async-patterns.md) — async patterns
- [JWIKI-058 fastapi.md](../03_BACKEND/fastapi.md) — FastAPI

## Fuentes

1. https://martinfowler.com/bliki/MonolithFirst.html — Martin Fowler, Monolith First
2. https://samnewman.io/patterns/architectural/monolith-vs-microservices/ — Sam Newman

## Nivel de confianza

**90%** — Decisión arquitectónica clásica bien documentada.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified