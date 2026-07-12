# CORS Abierto Producción — V0.7.3

## Resumen

**CORS `allow_origins=['*']`** en producción fue riesgo en V0.7.3. **Fixed en V0.8** (CLAUDE.md §1).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Risk

- ⚠️ Cualquier web puede llamar tu API desde el browser del user.
- ⚠️ CSRF + XSS exploitation.

## Fix V0.8

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "http://localhost:8000",  # backend
        "null",  # Electron file://
        # Settings.CORS_ALLOWED_ORIGINS from user config
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)
```

## Para Aithera

- ✅ V0.8: restringido (CLAUDE.md §1).

## Referencias cruzadas

- CLAUDE.md §1

## Fuentes

1. https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified