# UX — Error Handling

## Resumen

**Error handling** UX-friendly: mensajes claros, accionables, no asustar al user.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Principios

1. **Mensaje claro**: qué pasó.
2. **Acción**: qué puede hacer el user.
3. **No culpar**: "Aithera no pudo" no "tú hiciste mal".
4. **Soporte**: link a docs / contact.

## Anti-patterns

```tsx
// ❌ MAL
toast.error("Error 500: Internal Server Error")
toast.error("ValidationError: 'to' field invalid")

// ✅ BIEN
toast.error("No pude enviar el email. ¿Revisamos la dirección?")
toast.error("La dirección de email no es válida.")
```

## Aithera error handling

```python
class AitheraError(Exception):
    """Base error para Aithera."""
    user_message: str
    technical_details: str
    suggestions: list[str] = []

class EmailAuthExpired(AitheraError):
    user_message = "Tu sesión de Gmail ha expirado. ¿Renovamos los permisos?"
    suggestions = ["Ir a Ajustes > Gmail > Reconectar"]

# Global handler (CLAUDE.md §1)
@app.exception_handler(AitheraError)
async def handle_aithera_error(request, exc):
    logger.exception(exc.technical_details)
    return JSONResponse(
        status_code=400,
        content={
            "error_code": exc.__class__.__name__,
            "user_message": exc.user_message,
            "suggestions": exc.suggestions
        }
    )
```

## Para Aithera

- ✅ V0.7.3: global exception handler (CLAUDE.md §1).
- ⏳ V0.85+: mensajes user-friendly + i18n.

## Referencias cruzadas

- [JWIKI-076 exception-handling.md](../03_BACKEND/exception-handling.md)
- CLAUDE.md §1

## Fuentes

1. https://www.nngroup.com/articles/error-message-design/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified