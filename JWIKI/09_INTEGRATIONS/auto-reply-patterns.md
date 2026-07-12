# Auto-Reply Patterns — Aithera V0.7+

## Resumen

**Auto-reply** es el patrón de Aithera V0.7+ que permite al agente responder automáticamente a emails basado en reglas del user. CLAUDE.md §1: "Email Assistant refactor V0.7.1 → V0.7.3".

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Patrón Inbox Zero (origen)

Aithera借鉴 el patrón **Inbox Zero** (Merlin Mann):
- ✅ Reglas determinísticas (no LLM decide).
- ✅ LLM clasifica, motor de reglas ejecuta.
- ✅ Autonomía gradual por regla.
- ✅ Feedback loop del user.

## Modelo de datos

```python
# backend/app/db/database.py
class EmailAutoReplyRule(Base):
    __tablename__ = "email_auto_reply_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    name: Mapped[str]
    pattern: Mapped[str]  # sender, subject, body regex
    action: Mapped[str]   # "reply" | "archive" | "label" | "forward"
    template: Mapped[str]  # reply template (can use {{name}}, {{date}})
    autonomy: Mapped[str]  # "propose" (default) | "auto"
    ai_prompt: Mapped[str | None]  # prompt para el LLM si action="reply"
    hits: Mapped[int] = 0  # veces aplicada
    feedback_pos: Mapped[int] = 0  # feedback ✓
    feedback_neg: Mapped[int] = 0  # feedback ✗
    feedback_edit: Mapped[int] = 0  # feedback ✎
```

## Tipos de acción

| Action | Descripción |
|---|---|
| `reply` | enviar respuesta (con plantilla o ai_prompt) |
| `archive` | archivar sin responder |
| `label` | aplicar Gmail label |
| `forward` | reenviar a otra dirección |
| `mark_read` | marcar como leído |
| `spam` | marcar como spam |

## Autonomía gradual

Aithera V0.7.3 implementa **autonomía gradual** (CLAUDE.md §1):

```
0 hits → user debe aprobar cada acción
1+ hits → propone borrador (user acepta/edita/rechaza)
5+ hits con feedback positivo (≥saldo 5) → user puede subir a "auto"
"auto" → ejecuta sin confirmación
```

```python
async def apply_rule(rule, email):
    if rule.autonomy == "auto":
        # Ejecutar sin confirmación
        await execute_action(rule, email)
    else:
        # Proponer borrador (para 'reply')
        draft = await generate_draft(rule, email)
        await notify_user(f"¿Aprobar este borrador?\n\n{draft}")
```

## Aithera V0.7.3 features

- ✅ Rule engine determinístico.
- ✅ LLM clasifica emails (2 etapas: heurística → LLM).
- ✅ Autonomía gradual (propose → auto).
- ✅ Feedback loop (✓/✎/✗).
- ✅ Templates con variables (`{{name}}`, `{{date}}`).
- ✅ ai_prompt por regla (LLM redacta respuesta con estilo del user).

## CRUD endpoints

```python
# POST /api/email/auto-reply/rules
# GET /api/email/auto-reply/rules
# GET /api/email/auto-reply/rules/{id}
# PATCH /api/email/auto-reply/rules/{id}
# DELETE /api/email/auto-reply/rules/{id}
# POST /api/email/auto-reply/test { rule_id, email_id }
# POST /api/email/auto-reply/send { draft_id }  # confirmar borrador
```

## Para Aithera V0.85+

- ✅ Más fuentes de reglas (Slack, Notion, etc.).
- ✅ Reglas condicionales complejas (AND/OR).
- ✅ ML para sugerir nuevas reglas basado en historial.

## Referencias cruzadas

- [JWIKI-153 gmail-api.md](./gmail-api.md)
- [JWIKI-167 meeting-detection.md](./meeting-detection.md)
- [JWIKI-168 email-activity-log.md](./email-activity-log.md)
- CLAUDE.md §1 (V0.7.3 Email Assistant)

## Fuentes

1. https://www.43folders.com/intro-to-inbox-zero
2. CLAUDE.md §1

## Nivel de confianza

**100%** — implementado en CLAUDE.md §1.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified