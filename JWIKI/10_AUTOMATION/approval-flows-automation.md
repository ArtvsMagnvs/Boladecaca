# Approval Flows — Para automatizaciones

## Resumen

**Approval flows** son gates de aprobación que Aithera V0.9+ introduce para acciones sensibles (enviar email, borrar, ejecutar shell). Patrón P4 del Plan Maestro 2026 ("Checkpointing + approval gates formales").

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Por qué approval flows

- ⚠️ **Riesgo**: Aithera puede hacer acciones irreversibles (enviar email, borrar archivo, ejecutar shell).
- ✅ **Safety**: user debe confirmar antes de ejecutar.
- ✅ **Audit**: cada approval queda registrada.
- ✅ **Gradual autonomy**: empezar con approval, subir a auto cuando confianza.

## Approval gate architecture

```
Rule triggered
  ↓
Compute action + context
  ↓
Approval Gate
  ├─ Notificación al user (Hub, Telegram, Email)
  ├─ User revisa
  ├─ User: approve / deny / edit
  └─ Decision recorded
  ↓
Execute or skip
```

## Sensitive actions list

| Action | Approval required | Aithera V0.9+ |
|---|---|---|
| `email.send` | ✅ always | regla o auto-reply |
| `email.archive` | ❌ reversible | opcional |
| `email.delete` | ✅ always | nunca auto |
| `calendar.delete_event` | ✅ always | nunca auto |
| `shell.execute` | ✅ always | solo manual |
| `file.write` | ❌ reversible | opcional |
| `file.delete` | ✅ always | nunca auto |
| `agent.run` | depende | configurable |

## Approval request model

```python
class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    id: Mapped[int]
    rule_id: Mapped[int | None]
    action_type: Mapped[str]  # "email.send", etc.
    action_args: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str]  # "pending" | "approved" | "denied" | "edited"
    user_decision: Mapped[str | None]
    user_edits: Mapped[dict | None] = mapped_column(JSON)
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]
    decided_at: Mapped[datetime | None]
```

## UI patterns

### Hub card

```tsx
function ApprovalCard({ request }) {
    return (
        <Card>
            <Title>{request.action_type}: {request.action_args.subject}</Title>
            <Body>{request.action_args.body}</Body>
            <Buttons>
                <Button onClick={() => approve(request.id)}>✓ Aprobar</Button>
                <Button onClick={() => deny(request.id)}>✗ Denegar</Button>
                <Button onClick={() => openEdit(request.id)}>✎ Editar</Button>
            </Buttons>
            <Countdown expiresAt={request.expires_at} />
        </Card>
    );
}
```

### Telegram approval

```python
async def request_approval_telegram(request, bot):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✓ Aprobar", callback_data=f"approve:{request.id}"),
            InlineKeyboardButton("✗ Denegar", callback_data=f"deny:{request.id}")
        ]
    ])
    await bot.send_message(
        chat_id=settings.TELEGRAM_CHAT_ID,
        text=f"🤖 Aithera quiere:\n\n{format_action(request)}",
        reply_markup=keyboard
    )
```

## Approval timeout

Si user no responde en N minutos → auto-deny (safe default).

```python
DEFAULT_TIMEOUT_MINUTES = 30

async def wait_for_approval(request, timeout=DEFAULT_TIMEOUT_MINUTES):
    try:
        decision = await asyncio.wait_for(
            request_queue.wait_for_decision(request.id),
            timeout=timeout * 60
        )
        return decision
    except asyncio.TimeoutError:
        return {"status": "denied", "reason": "timeout"}
```

## Auto-approve rules

Para acciones no sensibles (leer, archivar, label), auto-approve sin gate.

Para **regla que ya tiene historial exitoso** (5+ ejecuciones aprobadas), user puede configurar "auto-approve".

## Audit trail

Cada approval queda en log:

```
2026-07-09 14:30:15 | rule weekly-digest | action email.send | APPROVED by user
2026-07-09 14:31:22 | rule auto-archive | action email.archive | AUTO-APPROVED
2026-07-09 14:32:10 | rule weekly-digest | action email.send | DENIED by user: "fuera de hora"
```

## Para Aithera

- ⏳ V0.9: approval flow + Hub UI.
- ⏳ V0.85+: Telegram approval integration.
- ⏳ V1.0+: ML para sugerir "auto-approve" cuando high confidence.

## Referencias cruzadas

- [JWIKI-118 approval-flows.md](../06_AGENTS/approval-flows.md)
- [JWIKI-166 auto-reply-patterns.md](../09_INTEGRATIONS/auto-reply-patterns.md)

## Fuentes

1. Plan Maestro 2026 §11 (V0.9 Automation)
2. https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop.html

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified