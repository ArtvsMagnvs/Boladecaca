# Exception Handling — Global handler en Aithera

## Resumen

Aithera V0.7.3 tiene un **global exception handler** que captura TODAS las excepciones no manejadas y devuelve JSON estructurado con log del error. Ver CLAUDE.md §1 (main.py:113).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Global handler

```python
# backend/app/main.py
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("aithera")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log con contexto completo
    logger.exception(
        f"Unhandled error in {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An internal error occurred. Check server logs.",
            "request_id": request.headers.get("X-Request-ID", "unknown"),
        }
    )
```

## Handlers específicos

```python
from fastapi.exceptions import RequestValidationError, HTTPException

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": exc.errors(),  # Pydantic format
        }
    )

@app.exception_handler(HTTPException)
async def http_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        }
    )
```

## Logging context

Aithera loguea con **structured logging** (campos parseables):

```python
import structlog

logger = structlog.get_logger()

logger.error(
    "email_send_failed",
    user_id=user.id,
    email_id=email.id,
    smtp_error=str(e),
    smtp_code=e.smtp_code,
)
```

## Error format estándar

```json
{
    "error": "string_code",     // machine-readable
    "message": "human text",   // user-readable
    "detail": [...],            // opcional, structured data
    "request_id": "uuid"        // para correlación con logs
}
```

## Best practices

- ✅ **Log ANTES de devolver** al cliente.
- ✅ **Stack trace completo** en logs del servidor.
- ✅ **Mensaje genérico** al cliente (no leak info).
- ✅ **Request ID** para correlación cliente-servidor.
- ❌ **No retornar stack trace** al cliente (security).
- ❌ **No swallow exceptions** silenciosamente.

## Para Aithera

- ✅ V0.7.3: global exception handler activo.
- ✅ Log a archivo + stdout.
- ⏳ V0.85: Sentry/GlitchTip integration (futuro).

## Referencias cruzadas

- [JWIKI-058 fastapi.md](./fastapi.md)
- [JWIKI-075 async-lifespan.md](./async-lifespan.md)

## Fuentes

1. https://fastapi.tiangolo.com/tutorial/handling-errors/
2. CLAUDE.md §1

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified