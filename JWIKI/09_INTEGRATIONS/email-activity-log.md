# Email Activity Log — Aithera V0.7+

## Resumen

**Email activity log** es el audit log de Aithera V0.7+ que registra cada acción que Aithera toma sobre emails (leer, archivar, marcar spam, auto-reply). Tabla `email_activity_log` en BD.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Modelo de datos

```python
class EmailActivityLog(Base):
    __tablename__ = "email_activity_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    email_id: Mapped[int | None]
    action: Mapped[str]  # "read" | "archive" | "label" | "reply" | "spam" | "forward"
    rule_id: Mapped[int | None]  # si fue por auto-reply rule
    actor: Mapped[str]  # "user" | "aithera" | "rule:{rule_id}"
    metadata: Mapped[dict] = mapped_column(JSON)  # detalles
    success: Mapped[bool] = True
    error_message: Mapped[str | None] = None
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

## Bug histórico (V0.7.2)

CLAUDE.md §1 menciona: "FIX del bug latente `import json as _json` vs `json.` que impedía persistir el activity log".

El bug era que `log_activity` fallaba en silencio, y el activity log **nunca había persistido nada**. **Fixed en V0.7.2**.

```python
# Antes (bug):
def log_activity(...):
    _json.dumps(...)  # <- import local

# Después (fix):
def log_activity(...):
    json.dumps(...)  # <- usa json global importado
```

## API endpoints

```python
# GET /api/email/activity
# Query: ?user_id=&action=&since=&limit=
# Response: { activities: [...], total, has_more }

# GET /api/email/activity/summary
# Aggregated: { total_read, total_replied, total_archived, by_day }
```

## Use cases

- ✅ **Audit**: ¿qué hizo Aithera mientras yo no estaba?
- ✅ **Debug**: ¿por qué Aithera archivó este email?
- ✅ **Dashboard**: dashboard de actividad en el Hub.
- ✅ **Digest**: digest diario con actividad de Aithera (V0.7.3).

## Digest diario

CLAUDE.md §1: `GET /api/email/digest` + tarjeta en el Hub:

```python
@router.get("/api/email/digest")
async def email_digest(user_id: int, since: datetime = None):
    activities = await db.get_activities(user_id, since=since or yesterday())
    
    return {
        "total_processed": len(activities),
        "auto_replied": sum(1 for a in activities if a.action == "reply" and a.actor != "user"),
        "archived": sum(1 for a in activities if a.action == "archive"),
        "flagged_spam": sum(1 for a in activities if a.action == "spam"),
        "highlights": [...]  # top 5 most interesting
    }
```

## Privacy

⚠️ El activity log contiene **metadata sensible** (quién, qué, cuándo). Cifrar con DPAPI en V0.8+.

## Retention

Aithera V0.85+ debería implementar **oblivion** (ver [JWIKI-137 oblivion.md](../07_MEMORY/oblivion.md)):
- Borrar entries > 90 días automáticamente.
- User puede pedir "borrar todo" (GDPR).

## Para Aithera

- ✅ V0.7.2: bug fixed, activity log funciona.
- ✅ V0.7.3: digest diario.
- ⏳ V0.85+: oblivion pattern, encryption DPAPI.

## Referencias cruzadas

- [JWIKI-166 auto-reply-patterns.md](./auto-reply-patterns.md)
- [JWIKI-137 oblivion.md](../07_MEMORY/oblivion.md)
- CLAUDE.md §1 (V0.7.2 fix)

## Fuentes

1. CLAUDE.md §1
2. https://en.wikipedia.org/wiki/Audit_trail

## Nivel de confianza

**100%** — implementado en CLAUDE.md §1.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified