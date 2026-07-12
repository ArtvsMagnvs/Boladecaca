# Approval Flows — Human-in-the-loop

## Resumen

**Approval flows** permiten al user revisar/approve/reject acciones sensibles del agent (enviar email, ejecutar shell, borrar archivo). Patrón P4 del Plan Maestro 2026.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Patrón

```
Agent wants to do X
  ↓
Approval Gate
  ↓
User reviews
  ├─ ✓ Approve → execute
  ├─ ✎ Edit → modify + execute
  └─ ✗ Deny → skip
```

## Implementación

```python
class ApprovalGate:
    async def request(self, action, args, user_id, timeout=1800) -> bool:
        request = ApprovalRequest(
            user_id=user_id,
            action=action,
            args=args,
            expires_at=datetime.utcnow() + timedelta(seconds=timeout)
        )
        await db.add(request)
        
        # Notificar user (Hub card, Telegram, etc.)
        await notify_user(request)
        
        # Esperar decisión
        decision = await self._wait_decision(request.id, timeout)
        
        if decision == "approve":
            return True
        elif decision == "edit":
            args = decision.edited_args
            return True  # con args modificados
        else:  # deny
            return False
    
    async def _wait_decision(self, request_id, timeout):
        # Polling o websocket
        ...
```

## Sensitive actions

| Action | Approval required |
|---|---|
| `email.send` | ✅ always |
| `email.delete` | ✅ always |
| `calendar.delete_event` | ✅ always |
| `shell.execute` | ✅ always |
| `file.delete` | ✅ always |
| `email.archive` | ❌ reversible |
| `calendar.create_event` | ❌ reversible |

## Aithera V0.7.3+ (auto-reply)

Aithera email auto-reply ya implementa autonomy gradual:
- ✅ "propose" (default) → user debe aprobar.
- ✅ "auto" (5+ hits con feedback positivo) → ejecuta sin pedir.

Ver [JWIKI-166 auto-reply-patterns.md](../09_INTEGRATIONS/auto-reply-patterns.md).

## V0.9+ Automation approval flow

Ver [JWIKI-176 approval-flows-automation.md](../10_AUTOMATION/approval-flows-automation.md).

## UI patterns

### Hub card

```tsx
<Card>
    <Title>{action}: {args.subject}</Title>
    <Body>{args.body}</Body>
    <Buttons>
        <Button onClick={() => approve(request.id)}>✓ Approve</Button>
        <Button onClick={() => deny(request.id)}>✗ Deny</Button>
        <Button onClick={() => openEdit(request.id)}>✎ Edit</Button>
    </Buttons>
    <Countdown expiresAt={request.expires_at} />
</Card>
```

### Telegram inline

```python
keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✓", callback_data=f"approve:{request.id}"),
        InlineKeyboardButton("✗", callback_data=f"deny:{request.id}")
    ]
])
await bot.send_message(chat_id, "...", reply_markup=keyboard)
```

## Para Aithera V1.0

V1.0 Orchestrator con approval gate unificado para todos los agents.

## Referencias cruzadas

- [JWIKI-166 auto-reply-patterns.md](../09_INTEGRATIONS/auto-reply-patterns.md)
- [JWIKI-176 approval-flows-automation.md](../10_AUTOMATION/approval-flows-automation.md)
- [JWIKI-118 approval-flows.md](./este doc)

## Fuentes

1. https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop.html
2. Plan Maestro 2026 §11

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified