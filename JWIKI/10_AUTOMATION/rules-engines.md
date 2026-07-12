# Rules Engines — JSON-based

## Resumen

**Rules engine** es el patrón que Aithera V0.9+ usa para definir automatizaciones declarativamente. Reglas en JSON/YAML, ejecutadas por el engine.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## JSON Rule structure

```json
{
    "id": "weekly-digest",
    "name": "Weekly digest email",
    "trigger": {
        "type": "cron",
        "expression": "0 9 * * 1"
    },
    "condition": {
        "type": "and",
        "rules": [
            {"field": "user.preferences.email_digest", "op": "==", "value": true},
            {"field": "context.is_weekend", "op": "==", "value": false}
        ]
    },
    "action": {
        "type": "email.send",
        "args": {
            "to": "{{user.email}}",
            "subject": "Tu digest semanal",
            "template": "weekly_digest",
            "data": {"period": "last_7_days"}
        }
    },
    "approval_required": false,
    "enabled": true
}
```

## Operators

| Operator | Uso |
|---|---|
| `==` | igual |
| `!=` | distinto |
| `>` `<` `>=` `<=` | comparación |
| `in` | contains |
| `not_in` | not contains |
| `contains` | string contains |
| `regex` | regex match |
| `and` `or` `not` | boolean |

## Trigger types

```python
# Time-based
{"type": "cron", "expression": "0 9 * * 1"}

# Interval-based
{"type": "interval", "minutes": 30}

# Event-based (e.g., on email received)
{"type": "event", "topic": "email.received", "filter": "from:boss@..."}

# Webhook-based
{"type": "webhook", "path": "/api/webhook/github", "method": "POST"}

# Manual
{"type": "manual", "command": "/run-rule weekly-digest"}
```

## Action types

```python
# Email
{"type": "email.send", "args": {...}}
{"type": "email.archive", "args": {"message_id": "..."}}
{"type": "email.label", "args": {"message_id": "...", "label": "..."}}

# Calendar
{"type": "calendar.create_event", "args": {...}}
{"type": "calendar.delete_event", "args": {"event_id": "..."}}

# Chat (Aithera)
{"type": "chat.query", "args": {"prompt": "...", "to_user": "..."}}

# Agent
{"type": "agent.run", "args": {"agent_id": 1, "input": "..."}}

# Webhook (outgoing)
{"type": "webhook.send", "args": {"url": "...", "method": "POST", "body": {...}}}

# Custom action
{"type": "custom", "module": "my_module", "function": "my_func", "args": {...}}
```

## Execution model

```python
class RulesEngine:
    async def evaluate(self, rule: dict, context: dict) -> bool:
        condition = rule["condition"]
        return self._eval_condition(condition, context)
    
    async def execute(self, rule: dict, context: dict) -> dict:
        # 1. Evaluate condition
        if not await self.evaluate(rule, context):
            return {"status": "skipped", "reason": "condition_false"}
        
        # 2. Resolve template vars
        action = self._resolve_template(rule["action"], context)
        
        # 3. Approval gate
        if rule["approval_required"]:
            approved = await self.approval_gate.request(rule, action, context)
            if not approved:
                return {"status": "denied", "reason": "user_denied"}
        
        # 4. Execute
        result = await self.action_executor.execute(action)
        
        # 5. Log
        await self.log(rule, action, result)
        
        return {"status": "success", "result": result}
```

## Storage

Rules stored en BD:

```python
class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id: Mapped[int]
    name: Mapped[str]
    description: Mapped[str]
    trigger: Mapped[dict] = mapped_column(JSON)
    condition: Mapped[dict | None] = mapped_column(JSON)
    action: Mapped[dict] = mapped_column(JSON)
    approval_required: Mapped[bool] = False
    enabled: Mapped[bool] = True
    created_at: Mapped[datetime]
    last_run_at: Mapped[datetime | None]
    last_result: Mapped[str | None]
```

## Para Aithera

- ⏳ V0.9: rules engine completo.
- ⏳ V0.85+: visual editor (drag-and-drop en frontend).
- ⏳ V1.0+: marketplace de reglas predefinidas.

## Referencias cruzadas

- [JWIKI-170 apscheduler.md](./apscheduler.md)
- [JWIKI-176 approval-flows-automation.md](./approval-flows-automation.md)
- [JWIKI-178 automation-rules-examples.md](./automation-rules-examples.md)

## Fuentes

1. https://jsonlogic.com/
2. https://jsonata.org/

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified