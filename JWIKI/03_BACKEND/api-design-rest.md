# REST API Design — Convenciones en Aithera

## Resumen

**REST** (Representational State Transfer) es el patrón de diseño de APIs usado por Aithera V0.7.3. Convenciones REST + extensiones Aithera-specific.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## REST basics

- ✅ Recursos como URLs: `/api/projects`, `/api/projects/{id}`.
- ✅ HTTP verbs: GET, POST, PUT, PATCH, DELETE.
- ✅ Status codes: 200, 201, 204, 400, 401, 403, 404, 500.
- ✅ JSON request/response.

## Convenciones Aithera V0.7.3

| Verbo | Ruta | Significado |
|---|---|---|
| GET | `/api/{resource}` | Listar |
| GET | `/api/{resource}/{id}` | Obtener uno |
| POST | `/api/{resource}` | Crear |
| PUT | `/api/{resource}/{id}` | Reemplazar |
| PATCH | `/api/{resource}/{id}` | Actualizar parcial |
| DELETE | `/api/{resource}/{id}` | Eliminar |

## Status codes usados

| Code | Uso |
|---|---|
| 200 | OK (GET, PUT, PATCH) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (no API key) |
| 403 | Forbidden (invalid API key) |
| 404 | Not Found |
| 422 | Unprocessable Entity (Pydantic validation) |
| 429 | Too Many Requests (rate limit) |
| 500 | Internal Server Error |

## Prefijos Aithera

| Prefijo | Router |
|---|---|
| `/api/chat` | Chat (SSE streaming) |
| `/api/email/*` | Email Assistant (V0.7+) |
| `/api/calendar/*` | Calendar |
| `/api/projects` | Projects CRUD |
| `/api/tasks` | Tasks CRUD |
| `/api/agents/*` | Agent Manager |
| `/api/ai/*` | AI providers |
| `/api/memory/*` | Memory (ChromaDB) |
| `/api/voice/*` | Voice |
| `/api/tools/*` | Tools |
| `/api/config` | Config |
| `/api/telegram/*` | Telegram (V0.8+) |

## Auth header

Todas las requests requieren:
```
Authorization: Bearer <api_key>
```

## Content negotiation

Aithera acepta y devuelve `application/json`.

## Versioning

Aithera V0.7.3 NO usa URL versioning (`/v1/`). Solo OpenAPI version. Decisión: single-version API.

## Pagination

Aithera V0.7.3 NO implementa pagination estándar. Para listas grandes (chats), se carga todo.

**Mejora futura V0.85+**: cursor-based pagination.

## Error format

```json
{
    "error": "validation_error",
    "detail": [
        {"field": "email", "message": "Invalid email format"},
        {"field": "age", "message": "Must be >= 18"}
    ]
}
```

## HATEOAS — NO se usa

Aithera no implementa HATEOAS (hypermedia). Decisión: pragmatic REST, no strict.

## Idempotency

Para POST críticos (pagos, etc.), usar `Idempotency-Key` header. Aithera V0.7.3 NO lo implementa (no hay endpoints críticos de pago).

## Rate limiting

Aithera V0.7.3 NO tiene rate limiting built-in. Confía en API keys como gate.

**Mejora futura V1.0**: rate limiting por IP + API key.

## OpenAPI

FastAPI genera OpenAPI automáticamente en `/docs` y `/openapi.json`.

## Referencias cruzadas

- [JWIKI-072 api-design-rest.md](./este doc)
- [JWIKI-073 api-design-graphql.md](./api-design-graphql.md)
- [JWIKI-074 api-design-trpc.md](./api-design-trpc.md)
- [JWIKI-076 exception-handling.md](./exception-handling.md)

## Fuentes

1. https://restfulapi.net/
2. https://docs.microsoft.com/en-us/azure/architecture/best-practices/api-design
3. FastAPI OpenAPI docs

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified