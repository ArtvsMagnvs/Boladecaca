# God-Endpoint Pattern — Anti-pattern general

## Resumen

**God-endpoint** (single router con muchos recursos) es anti-pattern. Aithera lo evitó en V0.7.2 dividiendo email_assistant en 7 routers.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Detección

- ⚠️ Archivo > 500 líneas con múltiples `@router.get` para recursos distintos.
- ⚠️ Múltiples dominios mezclados (email + calendar + auth).
- ⚠️ Imposible de testear unitariamente.
- ⚠️ Conflictos de merge frecuentes.

## Refactor pattern

```
# ANTES
router = APIRouter(prefix="/api/email_assistant")

@router.get("/status")
@router.get("/auth/start")
@router.post("/auth/callback")
@router.get("/inbox")
@router.post("/send")
@router.post("/auto-reply/rules")
...  # 50+ endpoints

# DESPUÉS
auth_router = APIRouter(prefix="/api/email/auth")
@auth_router.get("/status")
@auth_router.post("/start")
@auth_router.post("/callback")

inbox_router = APIRouter(prefix="/api/email/inbox")
@inbox_router.get("/")
@inbox_router.get("/{id}")

compose_router = APIRouter(prefix="/api/email/compose")
@compose_router.post("/send")

# + service layer
class EmailService:
    async def get_message(self, id): ...
    async def send(self, to, subject, body): ...
```

## Para Aithera

- ✅ V0.7.2: email_assistant dividido.

## Referencias cruzadas

- [JWIKI-238 email-assistant-god-endpoint.md](./email-assistant-god-endpoint.md)

## Fuentes

1. https://martinfowler.com/bliki/GodObject.html

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified